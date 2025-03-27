# src/infrastructure/database/redis/operations/expire.py
from fastapi import Depends
from redis.asyncio import Redis
from redis.exceptions import RedisError

from common.logging.logger import log_info, log_error
from ..redis_client import get_redis_client


async def expire(key: str, ttl: int, redis: Redis = Depends(get_redis_client)):
    """Set expiration time for a key in Redis."""
    try:
        await redis.expire(key, ttl)
        log_info("Redis expire", extra={"key": key, "ttl": ttl})
    except RedisError as e:
        log_error("Redis expire failed", extra={"key": key, "error": str(e)})
        raise
