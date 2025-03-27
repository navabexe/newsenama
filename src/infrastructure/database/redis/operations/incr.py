# src/infrastructure/database/redis/operations/incr.py
from fastapi import Depends
from redis.asyncio import Redis
from redis.exceptions import RedisError

from common.logging.logger import log_info, log_error
from ..redis_client import get_redis_client


async def incr(key: str, redis: Redis = Depends(get_redis_client)) -> int:
    """Increment a numeric value in Redis."""
    try:
        value = await redis.incr(key)
        log_info("Redis incr", extra={"key": key, "value": value})
        return value
    except RedisError as e:
        log_error("Redis incr failed", extra={"key": key, "error": str(e)})
        raise
