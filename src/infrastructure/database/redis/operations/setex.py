# src/infrastructure/database/redis/operations/setex.py
from fastapi import Depends
from redis.asyncio import Redis
from redis.exceptions import RedisError

from common.logging.logger import log_info, log_error
from ..redis_client import get_redis_client


async def setex(key: str, ttl: int, value: str, redis: Redis = Depends(get_redis_client)):
    """Set a value with expiration in Redis."""
    try:
        await redis.setex(key, ttl, value)
        log_info("Redis setex", extra={"key": key, "ttl": ttl})
    except RedisError as e:
        log_error("Redis setex failed", extra={"key": key, "error": str(e)})
        raise
