# File: infrastructure/database/redis/redis_client.py

import ssl
from typing import Optional

from redis.asyncio import Redis, ConnectionPool
from redis.exceptions import RedisError

from common.config.settings import settings
from common.exceptions.base_exception import ServiceUnavailableException
from common.logging.logger import log_info, log_error

# Redis connection pool (global, but managed)
redis_pool: Optional[ConnectionPool] = None
redis_client: Optional[Redis] = None


async def init_redis_pool() -> ConnectionPool:
    """Initialize Redis connection pool with settings from .env."""
    global redis_pool, redis_client
    try:
        connection_kwargs = {
            "host": settings.REDIS_HOST,
            "port": settings.REDIS_PORT,
            "db": settings.REDIS_DB,
            "decode_responses": True
        }

        redis_password = getattr(settings, "REDIS_PASSWORD", None)
        if redis_password and redis_password.strip():
            connection_kwargs["password"] = redis_password
            log_info("Using Redis with password", extra={"host": settings.REDIS_HOST})

        if settings.REDIS_USE_SSL:  # تغییر به استفاده مستقیم از مقدار بولی
            ssl_context = ssl.create_default_context(cafile=settings.REDIS_SSL_CA_CERTS)
            ssl_context.load_cert_chain(certfile=settings.REDIS_SSL_CERT, keyfile=settings.REDIS_SSL_KEY)
            connection_kwargs["ssl_context"] = ssl_context
            redis_pool = ConnectionPool.from_url(
                f"rediss://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
                **connection_kwargs
            )
        else:
            redis_pool = ConnectionPool(**connection_kwargs)

        redis_client = Redis(connection_pool=redis_pool)
        await redis_client.ping()
        log_info("Redis connection established", extra={
            "host": settings.REDIS_HOST,
            "port": settings.REDIS_PORT,
            "db": settings.REDIS_DB,
            "ssl": settings.REDIS_USE_SSL
        })

    except RedisError as e:
        log_error("Redis connection failed", extra={"error": str(e), "host": settings.REDIS_HOST}, exc_info=True)
        raise ServiceUnavailableException("Redis unavailable")

    return redis_pool


async def close_redis_pool():
    """Close Redis connection pool."""
    global redis_pool, redis_client
    if redis_client:
        await redis_client.close()
    if redis_pool:
        await redis_pool.disconnect()
    log_info("Redis connection pool closed")
    redis_pool = None
    redis_client = None


async def get_redis_client() -> Redis:
    """Dependency to get Redis client."""
    global redis_client
    try:
        if redis_client is None or not await redis_client.ping():
            await init_redis_pool()
        return redis_client
    except Exception as e:
        log_error("Failed to get Redis client", extra={"error": str(e)}, exc_info=True)
        raise ServiceUnavailableException("Could not connect to Redis")