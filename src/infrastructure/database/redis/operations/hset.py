# src/infrastructure/database/redis/operations/hset.py
from typing import Dict

from fastapi import Depends
from redis.asyncio import Redis
from redis.exceptions import RedisError

from common.logging.logger import log_info, log_error
from ..redis_client import get_redis_client


async def hset(key: str, mapping: Dict[str, str], redis: Redis = Depends(get_redis_client)):
    """Set a hash in Redis."""
    try:
        await redis.hset(key, mapping=mapping)
        log_info("Redis hset", extra={"key": key})
    except RedisError as e:
        log_error("Redis hset failed", extra={"key": key, "error": str(e)})
        raise
