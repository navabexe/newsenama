# src/infrastructure/database/redis/operations/delete.py
from fastapi import Depends
from redis.asyncio import Redis
from redis.exceptions import RedisError

from common.logging.logger import log_info, log_error
from ..redis_client import get_redis_client


async def delete(key: str, redis: Redis = Depends(get_redis_client)) -> int:
    """Delete a key from Redis."""
    try:
        result = await redis.delete(key)
        log_info("Redis delete", extra={"key": key, "deleted": result})
        return result
    except RedisError as e:
        log_error("Redis delete failed", extra={"key": key, "error": str(e)})
        raise
