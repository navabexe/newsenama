# src/infrastructure/database/redis/operations/hgetall.py
from typing import Dict

from fastapi import Depends
from redis.asyncio import Redis
from redis.exceptions import RedisError

from common.logging.logger import log_info, log_error
from ..redis_client import get_redis_client


async def hgetall(key: str, redis: Redis = Depends(get_redis_client)) -> Dict[str, str]:
    """Get all fields from a hash in Redis."""
    try:
        result = await redis.hgetall(key)
        log_info("Redis hgetall", extra={"key": key, "result": result})
        return result
    except RedisError as e:
        log_error("Redis hgetall failed", extra={"key": key, "error": str(e)})
        raise
