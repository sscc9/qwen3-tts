import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from core.config import settings
from core.database import init_db
from db.database import SessionLocal
from core.cleanup import run_scheduled_cleanup
from api import auth, jobs, tts, users, voice_designs
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def get_user_identifier(request: Request) -> str:
    from jose import jwt
    from core.config import settings

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = payload.get("sub")
            if user_id:
                return f"user:{user_id}"
        except Exception:
            pass

    return get_remote_address(request)

limiter = Limiter(key_func=get_user_identifier)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Qwen3-TTS Backend Service...")
    logger.info(f"Cache directory: {settings.CACHE_DIR}")
    logger.info(f"Output directory: {settings.OUTPUT_DIR}")

    try:
        settings.validate()
        logger.info("Configuration validated successfully")
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        raise

    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

    try:
        from core.init_admin import init_superuser
        init_superuser()
    except Exception as e:
        logger.error(f"Superuser initialization failed: {e}")
        raise



    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_scheduled_cleanup,
        'interval',
        hours=6,
        args=[str(settings.DATABASE_URL)],
        id='cleanup_task'
    )
    scheduler.start()
    logger.info("Background cleanup scheduler started (runs every 6 hours)")

    yield

    logger.info("Shutting down Qwen3-TTS Backend Service...")

    scheduler.shutdown()
    logger.info("Scheduler shutdown completed")



app = FastAPI(
    title="Qwen3-TTS-WebUI Backend API",
    description="Backend service for Qwen3-TTS-WebUI text-to-speech system",
    version="0.1.0",
    lifespan=lifespan
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(tts.router)
app.include_router(users.router)
app.include_router(voice_designs.router)

@app.get("/health")
async def health_check():
    gpu_available = False
    gpu_memory_used_mb = 0
    gpu_memory_total_mb = 0
    current_model = "None"
    queue_length = 0

    database_connected = True
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        database_connected = False

    cache_dir_writable = True
    try:
        test_file = Path(settings.CACHE_DIR) / ".health_check"
        test_file.write_text("test")
        test_file.unlink()
    except Exception as e:
        logger.error(f"Cache directory health check failed: {e}")
        cache_dir_writable = False

    output_dir_writable = True
    try:
        test_file = Path(settings.OUTPUT_DIR) / ".health_check"
        test_file.write_text("test")
        test_file.unlink()
    except Exception as e:
        logger.error(f"Output directory health check failed: {e}")
        output_dir_writable = False

    critical_issues = []
    if not database_connected:
        critical_issues.append("database_disconnected")
    if not cache_dir_writable:
        critical_issues.append("cache_dir_not_writable")
    if not output_dir_writable:
        critical_issues.append("output_dir_not_writable")

    minor_issues = []
    if not gpu_available:
        minor_issues.append("gpu_not_available")
    if queue_length > 50:
        minor_issues.append("queue_congested")

    backends_status = {}

    try:
        backends_status["aliyun"] = {
            "available": True,
            "region": settings.ALIYUN_REGION,
            "note": "Requires user API key configuration"
        }
    except Exception as e:
        logger.error(f"Backend health check failed: {e}")
        backends_status = {"error": str(e)}

    if critical_issues:
        status = "unhealthy"
    elif minor_issues:
        status = "degraded"
    else:
        status = "healthy"

    return {
        "status": status,
        "gpu_available": gpu_available,
        "gpu_memory_used_mb": gpu_memory_used_mb,
        "gpu_memory_total_mb": gpu_memory_total_mb,
        "queue_length": queue_length,
        "active_model": current_model,
        "database_connected": database_connected,
        "cache_dir_writable": cache_dir_writable,
        "output_dir_writable": output_dir_writable,
        "backends": backends_status,
        "issues": {
            "critical": critical_issues,
            "minor": minor_issues
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        workers=settings.WORKERS,
        log_level=settings.LOG_LEVEL.lower()
    )
