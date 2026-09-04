import redis
from app.core.config import settings

def get_redis():
    client = redis.from_url(settings.redis_url, decode_responses=True)
    try:
        yield client
    finally:
        client.close()
