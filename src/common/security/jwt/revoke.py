# File: common/security/jwt/revoke.py
from redis.asyncio import Redis
from fastapi import Depends

from common.config.settings import settings
from common.logging.logger import log_info, log_error
from infrastructure.database.redis.operations.delete import delete
from infrastructure.database.redis.operations.keys import keys
from infrastructure.database.redis.operations.setex import setex
from infrastructure.database.redis.redis_client import get_redis_client
from .errors import JWTError

async def get_redis(redis: Redis = Depends(get_redis_client)) -> Redis:
    """Dependency to provide Redis client."""
    return redis

async def revoke_token(
    jti: str,
    ttl: int,
    redis: Redis = Depends(get_redis),
) -> None:
    """
    Revoke a specific token by adding it to the Redis blacklist.

    Args:
        jti (str): JWT token identifier.
        ttl (int): Time-to-live in seconds for the blacklist entry.
        redis (Redis): Redis client instance.

    Raises:
        JWTError: If token revocation fails.
    """
    try:
        effective_ttl = max(ttl, settings.ACCESS_TTL)
        blacklist_key = f"blacklist:{jti}"
        await setex(blacklist_key, effective_ttl, "revoked", redis)
        log_info("Token revoked", extra={"jti": jti, "ttl": effective_ttl})
    except Exception as e:
        log_error("Token revocation failed", extra={"jti": jti, "error": str(e)})
        raise JWTError(f"Failed to revoke token: {str(e)}")

async def revoke_all_user_tokens(
    user_id: str,
    redis: Redis = Depends(get_redis),
) -> None:
    """
    Revoke all tokens and sessions associated with a user.

    Args:
        user_id (str): User identifier.
        redis (Redis): Redis client instance.

    Raises:
        JWTError: If revocation process fails.
    """
    try:
        refresh_pattern = f"refresh_tokens:{user_id}:*"
        refresh_keys = await keys(refresh_pattern, redis)
        for key in refresh_keys:
            jti = key.split(":")[-1]
            await delete(key, redis)
            await setex(f"blacklist:{jti}", settings.REFRESH_TTL, "revoked", redis)
            log_info("Refresh token revoked", extra={"user_id": user_id, "jti": jti})

        session_pattern = f"sessions:{user_id}:*"
        session_keys = await keys(session_pattern, redis)
        for key in session_keys:
            await delete(key, redis)
            log_info("Session removed", extra={"user_id": user_id, "key": key})

    except Exception as e:
        log_error("Revoke all tokens failed", extra={"user_id": user_id, "error": str(e)})
        raise JWTError(f"Failed to revoke all tokens: {str(e)}")