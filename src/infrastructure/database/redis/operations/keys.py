# src/infrastructure/database/redis/operations/keys.py
from typing import List

from fastapi import Depends
from redis.asyncio import Redis
from redis.exceptions import RedisError

from common.logging.logger import log_info, log_error
from ..redis_client import get_redis_client


async def keys(pattern: str, redis: Redis = Depends(get_redis_client)) -> List[str]:
    """Get keys matching a pattern from Redis."""
    try:
        result = await redis.keys(pattern)
        log_info("Redis keys", extra={"pattern": pattern, "result": result})
        return result
    except RedisError as e:
        log_error("Redis keys failed", extra={"pattern": pattern, "error": str(e)})
        raise
