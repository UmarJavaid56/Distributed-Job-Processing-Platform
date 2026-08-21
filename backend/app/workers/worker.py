from app.database import session_Local
from app.models.job import Job, JobStatus
from app.redis import redis_client
from app.routes.jobs import QUEUE_KEY

from datetime import datetime, timezone
import uuid
import time


import redis

def run_worker():
    while True:
        try:
            result = redis_client.brpop(QUEUE_KEY, timeout=5)
        except redis.TimeoutError:
            continue

        if result is None:
            continue

        _, job_id_str = result
        db = session_Local()
        try:
            job_id = uuid.UUID(job_id_str)
            job = db.get(Job, job_id)

            if job is None or job.status != JobStatus.queued:
                print("skip")
                continue

            job.status = JobStatus.running
            job.started_at = datetime.now(timezone.utc)
            db.commit()
            print("running", job.id)


            try: 
                seconds = job.payload.get("seconds", 2)
                time.sleep(seconds)
                job.result = "done"
                job.status = JobStatus.completed
                job.completed_at = datetime.now(timezone.utc)
                db.commit()    
                print("completed", job.id)
            except Exception as e:
                job.status = JobStatus.failed
                job.error = str(e)
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
                print("failed", job.id, e)

        finally:
            db.close()
        
                
if __name__ == "__main__":
    run_worker()