# src/infrastructure/database/redis/repositories/otp_repository.py
from typing import Optional, Dict, List

from redis.asyncio import Redis

from infrastructure.database.redis.redis_client import get_redis_client


class OTPRepository:
    def __init__(self, redis: Redis = None):
        self.redis = redis or get_redis_client()

    async def get(self, key: str) -> Optional[str]:
        return await (await self.redis).get(key)

    async def setex(self, key: str, ttl: int, value: str):
        await (await self.redis).setex(key, ttl, value)

    async def incr(self, key: str) -> int:
        return await (await self.redis).incr(key)

    async def expire(self, key: str, ttl: int):
        await (await self.redis).expire(key, ttl)

    async def delete(self, key: str):
        await (await self.redis).delete(key)

    async def hset(self, key: str, mapping: Dict[bytes, bytes]):
        await (await self.redis).hset(key, mapping=mapping)

    async def hgetall(self, key: str) -> Dict[bytes, bytes]:
        return await (await self.redis).hgetall(key)

    async def scan_keys(self, pattern: str) -> List[str]:
        cursor = b"0"
        keys = []
        redis = await self.redis
        while cursor != 0:
            cursor, batch = await redis.scan(cursor=cursor, match=pattern, count=100)
            keys.extend(batch)
        return [key.decode() if isinstance(key, bytes) else key for key in keys]