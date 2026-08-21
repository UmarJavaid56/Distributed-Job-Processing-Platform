import redis
from app.config import settings
from app.schemas.job import JobRead

redis_url = settings.redis_url
redis_client = redis.from_url(redis_url, decode_responses=True, socket_timeout=None)

JOB_CACHE_TTL = 60

def job_cache_key(job_id) -> str:
    return f"job_status:{job_id}"

def get_cached_job(job_id):

    try:
        raw = redis_client.get(job_cache_key(job_id))
        if raw is None:
            return None
        else:
            return JobRead.model_validate_json(raw)
    except Exception:
        return None

def set_cached_job(job) -> None:
    try:
        job_read = JobRead.model_validate(job)
        redis_client.set(job_cache_key(job_read.id), job_read.model_dump_json(), ex=JOB_CACHE_TTL)
    except Exception:
        return None

def invalidated_job_cache(job_id) -> None:
    try:
        redis_client.delete(job_cache_key(job_id))
    except Exception:
        return None