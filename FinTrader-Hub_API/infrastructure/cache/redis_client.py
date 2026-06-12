from functools import lru_cache

import redis

from core.config import get_settings


@lru_cache
def get_redis_client() -> redis.Redis:
    settings = get_settings()
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


def check_redis_connection() -> bool:
    client = get_redis_client()
    if not client.ping():
        raise RuntimeError("Redis ping failed")
    return True
