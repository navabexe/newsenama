# src/infrastructure/database/redis/operations/get.py
from typing import Optional

from fastapi import Depends
from redis.asyncio import Redis
from redis.exceptions import RedisError

from common.logging.logger import log_info, log_error
from ..redis_client import get_redis_client


async def get(key: str, redis: Redis = Depends(get_redis_client)) -> Optional[str]:
    """Get a value from Redis."""
    try:
        value = await redis.get(key)
        log_info("Redis get", extra={"key": key, "value": value})
        return value
    except RedisError as e:
        log_error("Redis get failed", extra={"key": key, "error": str(e)})
        raise
