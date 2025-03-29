# infrastructure/database/redis/operations/scan.py
from redis.asyncio import Redis
from redis.exceptions import RedisError
from typing import List

from common.logging.logger import log_error

async def scan_keys(redis: Redis, pattern: str) -> List[str]:
    """Scan all keys matching pattern using async scan."""
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
