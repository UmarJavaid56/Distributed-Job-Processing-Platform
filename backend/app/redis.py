import redis
from app.config import settings

redis_url = settings.redis_url
redis_client = redis.from_url(redis_url, decode_responses=True, socket_timeout=None)