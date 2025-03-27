from redis.asyncio import Redis

from common.config.settings import settings
from common.logging.logger import log_info, log_error
from infrastructure.database.redis.operations.delete import delete
from infrastructure.database.redis.operations.keys import keys
from infrastructure.database.redis.operations.setex import setex
from infrastructure.database.redis.redis_client import get_redis_client
from .errors import JWTError


async def revoke_token(
    jti: str,
    ttl: int,
    redis: Redis = None
):
    """
    Revoke a specific token by blacklisting it in Redis.
    """
    try:
        if redis is None:
            redis = await get_redis_client()

        await setex(f"blacklist:{jti}", ttl, "revoked", redis)
        log_info("Token revoked", extra={"jti": jti, "ttl": ttl})

    except Exception as e:
        log_error("Token revocation failed", extra={"jti": jti, "error": str(e)})
        raise JWTError(f"Failed to revoke token: {str(e)}")


async def revoke_all_user_tokens(
    user_id: str,
    redis: Redis = None
):
    """
    Revoke all tokens and sessions associated with a user.
    """
    try:
        if redis is None:
            redis = await get_redis_client()

        # Revoke all refresh tokens
        refresh_keys = await keys(f"refresh_tokens:{user_id}:*", redis)
        for key in refresh_keys:
            jti = key.split(":")[-1]
            await delete(key, redis)
            await setex(f"blacklist:{jti}", settings.REFRESH_TTL, "revoked", redis)
            log_info("Refresh token revoked", extra={"user_id": user_id, "jti": jti})

        # Remove all session records
        session_keys = await keys(f"sessions:{user_id}:*", redis)
        for key in session_keys:
            await delete(key, redis)
            log_info("Session removed", extra={"user_id": user_id, "key": key})

    except Exception as e:
        log_error("Revoke all tokens failed", extra={"user_id": user_id, "error": str(e)})
        raise JWTError(f"Failed to revoke all tokens: {str(e)}")
