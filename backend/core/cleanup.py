import logging
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.config import settings
from db.models import Job

logger = logging.getLogger(__name__)

async def cleanup_expired_caches(db_url: str) -> dict:
    return {
        'deleted_count': 0,
        'freed_space_mb': 0
    }

async def cleanup_old_jobs(db_url: str, days: int = 7) -> dict:
    try:
        engine = create_engine(db_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        old_jobs = db.query(Job).filter(
            Job.completed_at < cutoff_date,
            Job.status.in_(['completed', 'failed'])
        ).all()

        deleted_files = 0
        for job in old_jobs:
            if job.output_path:
                output_file = Path(job.output_path)
                if output_file.exists():
                    output_file.unlink()
                    deleted_files += 1

            db.delete(job)

        db.commit()
        deleted_jobs = len(old_jobs)

        db.close()

        logger.info(f"Cleanup: deleted {deleted_jobs} old jobs, {deleted_files} files")

        return {
            'deleted_jobs': deleted_jobs,
            'deleted_files': deleted_files
        }

    except Exception as e:
        logger.error(f"Old job cleanup failed: {e}", exc_info=True)
        return {
            'deleted_jobs': 0,
            'deleted_files': 0,
            'error': str(e)
        }


async def cleanup_orphaned_files(db_url: str) -> dict:
    try:
        engine = create_engine(db_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        deleted_orphans = 0
        freed_space_bytes = 0

        if output_dir.exists():
            for output_file in output_dir.glob("*.wav"):
                if output_file.name not in output_files_in_db:
                    size = output_file.stat().st_size
                    output_file.unlink()
                    deleted_orphans += 1
                    freed_space_bytes += size

        freed_space_mb = freed_space_bytes / (1024 * 1024)

        db.close()

        logger.info(f"Cleanup: deleted {deleted_orphans} orphaned files, freed {freed_space_mb:.2f} MB")

        return {
            'deleted_orphans': deleted_orphans,
            'freed_space_mb': freed_space_mb
        }

    except Exception as e:
        logger.error(f"Orphaned file cleanup failed: {e}", exc_info=True)
        return {
            'deleted_orphans': 0,
            'freed_space_mb': 0,
            'error': str(e)
        }


async def run_scheduled_cleanup(db_url: str) -> dict:
    logger.info("Starting scheduled cleanup task...")

    try:
        cache_result = await cleanup_expired_caches(db_url)
        job_result = await cleanup_old_jobs(db_url)
        orphan_result = await cleanup_orphaned_files(db_url)

        result = {
            'timestamp': datetime.utcnow().isoformat(),
            'expired_caches': cache_result,
            'old_jobs': job_result,
            'orphaned_files': orphan_result,
            'status': 'completed'
        }

        logger.info(f"Scheduled cleanup completed: {result}")

        return result

    except Exception as e:
        logger.error(f"Scheduled cleanup failed: {e}", exc_info=True)
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'failed',
            'error': str(e)
        }
