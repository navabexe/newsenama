# File: src/infrastructure/database/redis/repositories/otp_repository.py
from typing import Optional, Dict, List

from redis.asyncio import Redis

from common.logging.logger import log_info, log_error
from infrastructure.database.redis.redis_client import get_redis_client


class OTPRepository:
    def __init__(self, redis: Redis = None):
        self.redis = redis or get_redis_client()

    async def get(self, key: str) -> Optional[str]:
        try:
            redis = await self.redis
            value = await redis.get(key)
            log_info("Redis get", extra={"key": key, "value": value})
            return value
        except Exception as e:
            log_error("Redis get failed", extra={"key": key, "error": str(e)})
            raise

    async def setex(self, key: str, ttl: int, value: str):
        try:
            redis = await self.redis
            await redis.setex(key, ttl, value)
            log_info("Redis setex", extra={"key": key, "ttl": ttl})
        except Exception as e:
            log_error("Redis setex failed", extra={"key": key, "error": str(e)})
            raise

    async def incr(self, key: str) -> int:
        try:
            redis = await self.redis
            value = await redis.incr(key)
            log_info("Redis incr", extra={"key": key, "value": value})
            return value
        except Exception as e:
            log_error("Redis incr failed", extra={"key": key, "error": str(e)})
            raise

    async def expire(self, key: str, ttl: int):
        try:
            redis = await self.redis
            await redis.expire(key, ttl)
            log_info("Redis expire", extra={"key": key, "ttl": ttl})
        except Exception as e:
            log_error("Redis expire failed", extra={"key": key, "error": str(e)})
            raise

    async def delete(self, key: str):
        try:
            redis = await self.redis
            await redis.delete(key)
            log_info("Redis delete", extra={"key": key})
        except Exception as e:
            log_error("Redis delete failed", extra={"key": key, "error": str(e)})
            raise

    async def hset(self, key: str, mapping: Dict[bytes, bytes]):
        try:
            redis = await self.redis
            await redis.hset(key, mapping=mapping)
            log_info("Redis hset", extra={"key": key})
        except Exception as e:
            log_error("Redis hset failed", extra={"key": key, "error": str(e)})
            raise

    async def hgetall(self, key: str) -> Dict[bytes, bytes]:
        try:
            redis = await self.redis
            result = await redis.hgetall(key)
            log_info("Redis hgetall", extra={"key": key, "result": result})
            return result
        except Exception as e:
            log_error("Redis hgetall failed", extra={"key": key, "error": str(e)})
            raise

    async def scan_keys(self, pattern: str) -> List[str]:
        try:
            redis = await self.redis
            cursor = b"0"
            keys = []
            while cursor != 0:
                cursor, batch = await redis.scan(cursor=cursor, match=pattern, count=100)
                keys.extend(batch)
            decoded_keys = [key.decode() if isinstance(key, bytes) else key for key in keys]
            log_info("Redis scan_keys", extra={"pattern": pattern, "keys": decoded_keys})
            return decoded_keys
        except Exception as e:
            log_error("Redis scan_keys failed", extra={"pattern": pattern, "error": str(e)})
            raise