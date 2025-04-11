# redis_operations.py
from typing import Optional, Dict, List

from fastapi import Depends
from redis.asyncio import Redis
from redis.exceptions import RedisError

from common.logging.logger import log_info, log_error
from infrastructure.database.redis.redis_client import get_redis_client


# delete
async def delete(key: str, redis: Redis = Depends(get_redis_client)) -> int:
    try:
        result = await redis.delete(key)
        log_info("Redis delete", extra={"key": key, "deleted": result})
        return result
    except RedisError as e:
        log_error("Redis delete failed", extra={"key": key, "error": str(e)})
        raise

# expire
async def expire(key: str, ttl: int, redis: Redis = Depends(get_redis_client)):
    try:
        await redis.expire(key, ttl)
        log_info("Redis expire", extra={"key": key, "ttl": ttl})
    except RedisError as e:
        log_error("Redis expire failed", extra={"key": key, "error": str(e)})
        raise

# get
async def get(key: str, redis: Redis = Depends(get_redis_client)) -> Optional[str]:
    try:
        value = await redis.get(key)
        log_info("Redis get", extra={"key": key, "value": value})
        return value
    except RedisError as e:
        log_error("Redis get failed", extra={"key": key, "error": str(e)})
        raise

# hgetall
async def hgetall(key: str, redis: Redis = Depends(get_redis_client)) -> Dict[str, str]:
    try:
        result = await redis.hgetall(key)
        log_info("Redis hgetall", extra={"key": key, "result": result})
        return result
    except RedisError as e:
        log_error("Redis hgetall failed", extra={"key": key, "error": str(e)})
        raise

# hset
async def hset(key: str, mapping: Dict[str, str], redis: Redis = Depends(get_redis_client)):
    try:
        await redis.hset(key, mapping=mapping)
        log_info("Redis hset", extra={"key": key})
    except RedisError as e:
        log_error("Redis hset failed", extra={"key": key, "error": str(e)})
        raise

# incr
async def incr(key: str, redis: Redis = Depends(get_redis_client)) -> int:
    try:
        value = await redis.incr(key)
        log_info("Redis incr", extra={"key": key, "value": value})
        return value
    except RedisError as e:
        log_error("Redis incr failed", extra={"key": key, "error": str(e)})
        raise

# keys
async def keys(pattern: str, redis: Redis = Depends(get_redis_client)) -> List[str]:
    try:
        result = await redis.keys(pattern)
        log_info("Redis keys", extra={"pattern": pattern, "result": result})
        return result
    except RedisError as e:
        log_error("Redis keys failed", extra={"pattern": pattern, "error": str(e)})
        raise

# scan
async def scan_keys(redis: Redis, pattern: str) -> List[str]:
    try:
        cursor = b"0"
        keys = []
        while cursor != 0:
            cursor, batch = await redis.scan(cursor=cursor, match=pattern, count=100)
            keys.extend(batch)
        return [key.decode() if isinstance(key, bytes) else key for key in keys]
    except RedisError as e:
        log_error("Redis SCAN failed", extra={"pattern": pattern, "error": str(e)})
        return []

# setex
async def setex(key: str, ttl: int, value: str, redis: Redis = Depends(get_redis_client)):
    try:
        await redis.setex(key, ttl, value)
        log_info("Redis setex", extra={"key": key, "ttl": ttl})
    except RedisError as e:
        log_error("Redis setex failed", extra={"key": key, "error": str(e)})
        raise

# ttl
async def ttl(key: str, redis: Redis) -> int:
    return await redis.ttl(key)
