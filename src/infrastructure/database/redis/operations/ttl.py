# File: infrastructure/database/redis/operations/ttl.py

from redis.asyncio import Redis

async def ttl(key: str, redis: Redis) -> int:
    """
    Get the time-to-live (TTL) in seconds for a given key in Redis.

    Args:
        key (str): The Redis key to check.
        redis (Redis): The Redis client instance.

    Returns:
        int: TTL in seconds:
            - Positive value: Remaining time in seconds.
            - -1: Key exists but has no expiration.
            - -2: Key does not exist.

    Raises:
        RedisError: If there is an issue communicating with Redis.
    """
    return await redis.ttl(key)