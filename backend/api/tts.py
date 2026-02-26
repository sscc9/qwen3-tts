import logging
import tempfile
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from typing import Optional
from slowapi import Limiter
from slowapi.util import get_remote_address

from core.config import settings
from core.database import get_db
from db.models import Job, JobStatus, User
from schemas.tts import CustomVoiceRequest, VoiceDesignRequest
from api.auth import get_current_user
from utils.validation import (
    validate_language,
    validate_speaker,
    validate_text_length,
    validate_generation_params,
    get_supported_languages,
    get_supported_speakers
)
from utils.audio import save_audio_file, validate_ref_audio

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tts", tags=["tts"])

limiter = Limiter(key_func=get_remote_address)


async def process_custom_voice_job(
    job_id: int,
    user_id: int,
    request_data: dict,
    backend_type: str,
    db_url: str
):
    from core.database import SessionLocal
    from core.tts_service import TTSServiceFactory
    from core.security import decrypt_api_key

    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        job.status = JobStatus.PROCESSING
        job.started_at = datetime.utcnow()
        db.commit()

        logger.info(f"Processing custom-voice job {job_id} with backend {backend_type}")

        user_api_key = None
        if backend_type == "aliyun":
            user = db.query(User).filter(User.id == user_id).first()
            if user and user.aliyun_api_key:
                user_api_key = decrypt_api_key(user.aliyun_api_key)

        backend = await TTSServiceFactory.get_backend(backend_type, user_api_key)

        audio_bytes, sample_rate = await backend.generate_custom_voice(request_data)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{user_id}_{job_id}_{timestamp}.wav"
        output_path = Path(settings.OUTPUT_DIR) / filename

        with open(output_path, 'wb') as f:
            f.write(audio_bytes)

        job.status = JobStatus.COMPLETED
        job.output_path = str(output_path)
        job.completed_at = datetime.utcnow()
        db.commit()

        logger.info(f"Job {job_id} completed successfully")

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            db.commit()

    finally:
        db.close()


async def process_voice_design_job(
    job_id: int,
    user_id: int,
    request_data: dict,
    backend_type: str,
    db_url: str,
    saved_voice_id: Optional[str] = None
):
    from core.database import SessionLocal
    from core.tts_service import TTSServiceFactory
    from core.security import decrypt_api_key

    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        job.status = JobStatus.PROCESSING
        job.started_at = datetime.utcnow()
        db.commit()

        logger.info(f"Processing voice-design job {job_id} with backend {backend_type}")

        user_api_key = None
        if backend_type == "aliyun":
            user = db.query(User).filter(User.id == user_id).first()
            if user and user.aliyun_api_key:
                user_api_key = decrypt_api_key(user.aliyun_api_key)

        backend = await TTSServiceFactory.get_backend(backend_type, user_api_key)

        if backend_type == "aliyun" and saved_voice_id:
            audio_bytes, sample_rate = await backend.generate_voice_design(request_data, saved_voice_id)
        else:
            audio_bytes, sample_rate = await backend.generate_voice_design(request_data)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{user_id}_{job_id}_{timestamp}.wav"
        output_path = Path(settings.OUTPUT_DIR) / filename

        with open(output_path, 'wb') as f:
            f.write(audio_bytes)

        job.status = JobStatus.COMPLETED
        job.output_path = str(output_path)
        job.completed_at = datetime.utcnow()
        db.commit()

        logger.info(f"Job {job_id} completed successfully")

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            db.commit()

    finally:
        db.close()


async def process_voice_clone_job(
    job_id: int,
    user_id: int,
    request_data: dict,
    ref_audio_path: str,
    backend_type: str,
    db_url: str,
    use_voice_design: bool = False
):
    from core.database import SessionLocal
    from core.tts_service import TTSServiceFactory
    from core.security import decrypt_api_key
    import numpy as np

    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        job.status = JobStatus.PROCESSING
        job.started_at = datetime.utcnow()
        db.commit()

        logger.info(f"Processing voice-clone job {job_id} with Aliyun backend")

        user_api_key = None
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.aliyun_api_key:
            user_api_key = decrypt_api_key(user.aliyun_api_key)

        backend = await TTSServiceFactory.get_backend("aliyun", user_api_key)

        with open(ref_audio_path, 'rb') as f:
            ref_audio_data = f.read()

        audio_bytes, sample_rate, voice_id = await backend.generate_voice_clone(request_data, ref_audio_data)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{user_id}_{job_id}_{timestamp}.wav"
        output_path = Path(settings.OUTPUT_DIR) / filename

        with open(output_path, 'wb') as f:
            f.write(audio_bytes)

        job.status = JobStatus.COMPLETED
        job.output_path = str(output_path)
        job.completed_at = datetime.utcnow()
        
        if voice_id:
            from sqlalchemy.orm.attributes import flag_modified
            # Update input_params to include the voice_id so frontend can retrieve it
            current_params = dict(job.input_params or {})
            current_params["voice_id"] = voice_id
            job.input_params = current_params
            flag_modified(job, "input_params")
            
        db.commit()

        logger.info(f"Job {job_id} completed successfully with voice_id {voice_id}")

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            db.commit()

    finally:
        if not use_voice_design and ref_audio_path and Path(ref_audio_path).exists():
            Path(ref_audio_path).unlink()
        db.close()


@router.post("/custom-voice")
async def create_custom_voice_job(
    request: Request,
    req_data: CustomVoiceRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from core.security import decrypt_api_key

    backend_type = "aliyun"

    if not current_user.aliyun_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aliyun API key not configured. Please set your API key in Settings."
        )

    try:
        validate_text_length(req_data.text)
        language = validate_language(req_data.language)
        speaker = validate_speaker(req_data.speaker, backend_type)

        params = validate_generation_params({
            'max_new_tokens': req_data.max_new_tokens,
            'temperature': req_data.temperature,
            'top_k': req_data.top_k,
            'top_p': req_data.top_p,
            'repetition_penalty': req_data.repetition_penalty
        })

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    job = Job(
        user_id=current_user.id,
        job_type="custom-voice",
        status=JobStatus.PENDING,
        backend_type=backend_type,
        input_data="",
        input_params={
            "text": req_data.text,
            "language": language,
            "speaker": speaker,
            "instruct": req_data.instruct or "",
            **params
        }
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    request_data = {
        "text": req_data.text,
        "language": language,
        "speaker": speaker,
        "instruct": req_data.instruct or "",
        **params
    }

    background_tasks.add_task(
        process_custom_voice_job,
        job.id,
        current_user.id,
        request_data,
        backend_type,
        str(settings.DATABASE_URL)
    )

    return {
        "job_id": job.id,
        "status": job.status,
        "message": "Job created successfully"
    }


@router.post("/voice-design")
async def create_voice_design_job(
    request: Request,
    req_data: VoiceDesignRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from core.security import decrypt_api_key
    from db.crud import get_voice_design, update_voice_design_usage

    backend_type = "aliyun"

    saved_voice_id = None

    if req_data.saved_design_id:
        saved_design = get_voice_design(db, req_data.saved_design_id, current_user.id)
        if not saved_design:
            raise HTTPException(status_code=404, detail="Saved voice design not found")

        req_data.instruct = saved_design.instruct
        saved_voice_id = saved_design.aliyun_voice_id

        update_voice_design_usage(db, req_data.saved_design_id, current_user.id)

    if not current_user.aliyun_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aliyun API key not configured. Please set your API key in Settings."
        )

    try:
        validate_text_length(req_data.text)
        language = validate_language(req_data.language)

        if not req_data.saved_design_id:
            if not req_data.instruct or not req_data.instruct.strip():
                raise ValueError("Instruct parameter is required when saved_design_id is not provided")

        params = validate_generation_params({
            'max_new_tokens': req_data.max_new_tokens,
            'temperature': req_data.temperature,
            'top_k': req_data.top_k,
            'top_p': req_data.top_p,
            'repetition_penalty': req_data.repetition_penalty
        })

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    job = Job(
        user_id=current_user.id,
        job_type="voice-design",
        status=JobStatus.PENDING,
        backend_type=backend_type,
        input_data="",
        input_params={
            "text": req_data.text,
            "language": language,
            "instruct": req_data.instruct,
            **params
        }
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    request_data = {
        "text": req_data.text,
        "language": language,
        "instruct": req_data.instruct,
        **params
    }

    background_tasks.add_task(
        process_voice_design_job,
        job.id,
        current_user.id,
        request_data,
        backend_type,
        str(settings.DATABASE_URL),
        saved_voice_id
    )

    return {
        "job_id": job.id,
        "status": job.status,
        "message": "Job created successfully"
    }


@router.post("/voice-clone")
async def create_voice_clone_job(
    request: Request,
    text: str = Form(...),
    language: str = Form(default="Auto"),
    ref_audio: Optional[UploadFile] = File(default=None),
    ref_text: Optional[str] = Form(default=None),
    use_cache: bool = Form(default=True),
    x_vector_only_mode: bool = Form(default=False),
    voice_design_id: Optional[int] = Form(default=None),
    max_new_tokens: Optional[int] = Form(default=2048),
    temperature: Optional[float] = Form(default=0.9),
    top_k: Optional[int] = Form(default=50),
    top_p: Optional[float] = Form(default=1.0),
    repetition_penalty: Optional[float] = Form(default=1.05),
    backend: Optional[str] = Form(default=None),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from core.security import decrypt_api_key
    from db.crud import get_voice_design
    import hashlib

    backend_type = "aliyun"

    if not current_user.aliyun_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aliyun API key not configured. Please set your API key in Settings."
        )

    ref_audio_data = None
    ref_audio_hash = None
    use_voice_design = False

    try:
        validate_text_length(text)
        language = validate_language(language)

        params = validate_generation_params({
            'max_new_tokens': max_new_tokens,
            'temperature': temperature,
            'top_k': top_k,
            'top_p': top_p,
            'repetition_penalty': repetition_penalty
        })

        if voice_design_id:
            design = get_voice_design(db, voice_design_id, current_user.id)
            if not design:
                raise ValueError("Voice design not found")

            if not design.aliyun_voice_id:
                raise ValueError("Voice design has not been successfully saved.")

            use_voice_design = True
            ref_audio_hash = f"voice_design_{voice_design_id}"
            if not ref_text:
                ref_text = design.ref_text

            logger.info(f"Using voice design {voice_design_id}")

        else:
            if not ref_audio:
                raise ValueError("Either ref_audio or voice_design_id must be provided")

            ref_audio_data = await ref_audio.read()

            if not validate_ref_audio(ref_audio_data, max_size_mb=settings.MAX_AUDIO_SIZE_MB):
                raise ValueError("Invalid reference audio: must be 1-30s duration and ≤10MB")
                
            ref_audio_hash = hashlib.md5(ref_audio_data).hexdigest()

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    job = Job(
        user_id=current_user.id,
        job_type="voice-clone",
        status=JobStatus.PENDING,
        backend_type=backend_type,
        input_data="",
        input_params={
            "text": text,
            "language": language,
            "ref_text": ref_text or "",
            "ref_audio_hash": ref_audio_hash,
            "use_cache": use_cache,
            "x_vector_only_mode": x_vector_only_mode,
            "voice_design_id": voice_design_id,
            **params
        }
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    if use_voice_design:
        design = get_voice_design(db, voice_design_id, current_user.id)
        tmp_audio_path = design.ref_audio_path
    else:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
            tmp_file.write(ref_audio_data)
            tmp_audio_path = tmp_file.name

    request_data = {
        "text": text,
        "language": language,
        "ref_text": ref_text or "",
        "use_cache": use_cache,
        "x_vector_only_mode": x_vector_only_mode,
        "voice_design_id": voice_design_id,
        **params
    }

    background_tasks.add_task(
        process_voice_clone_job,
        job.id,
        current_user.id,
        request_data,
        tmp_audio_path,
        backend_type,
        str(settings.DATABASE_URL),
        use_voice_design
    )

    cache_info = None

    return {
        "job_id": job.id,
        "status": job.status,
        "message": "Job created successfully",
        "cache_info": cache_info
    }


@router.get("/speakers")
async def list_speakers(request: Request, backend: Optional[str] = "local"):
    return get_supported_speakers(backend)


@router.get("/languages")
async def list_languages(request: Request):
    return get_supported_languages()
