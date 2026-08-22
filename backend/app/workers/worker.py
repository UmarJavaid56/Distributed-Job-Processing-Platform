from datetime import datetime, timezone
import time
import uuid

import redis

from app.database import session_Local
from app.models.job import Job, JobStatus
from app.redis import redis_client, invalidated_job_cache
from app.routes.jobs import QUEUE_KEY


def process_job_id(job_id_str: str) -> str:
    """Load a job, run work if still queued, update status. Returns outcome label."""
    db = session_Local()
    try:
        job_id = uuid.UUID(job_id_str)
        job = db.get(Job, job_id)

        if job is None or job.status != JobStatus.queued:
            return "skipped"

        job.status = JobStatus.running
        job.started_at = datetime.now(timezone.utc)
        db.commit()
        invalidated_job_cache(job.id)

        try:
            seconds = float(job.payload.get("seconds", 2))
            if seconds > 0:
                time.sleep(seconds)
            job.result = "done"
            job.status = JobStatus.completed
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            invalidated_job_cache(job.id)
            return "completed"
        except Exception as e:
            job.status = JobStatus.failed
            job.error = str(e)
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            invalidated_job_cache(job.id)
            return "failed"
    finally:
        db.close()


def run_worker() -> None:
    while True:
        try:
            result = redis_client.brpop(QUEUE_KEY, timeout=5)
        except redis.TimeoutError:
            continue

        if result is None:
            continue

        _, job_id_str = result
        outcome = process_job_id(job_id_str)
        print(outcome, job_id_str)


if __name__ == "__main__":
    run_worker()
