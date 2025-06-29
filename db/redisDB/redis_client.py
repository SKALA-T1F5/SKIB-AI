import redis.asyncio as redis

from config.settings import settings

redis_client = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db,
    password=settings.redis_password,
    decode_responses=True,  # 문자열 자동 디코딩
)
