from datetime import datetime, timezone

from fastapi import HTTPException, status
from redis.asyncio import Redis

from common.logging.logger import log_info, log_error
from common.security.jwt_handler import revoke_token
from infrastructure.database.redis.operations.delete import delete
from infrastructure.database.redis.operations.hgetall import hgetall
from infrastructure.database.redis.operations.keys import keys
from infrastructure.database.redis.redis_client import get_redis_client
from common.translations.messages import get_message


async def logout_service(
    user_id: str,
    session_id: str,
    client_ip: str,
    redis: Redis = None,
    language: str = "fa"
) -> dict:
    """
    Logout from all user sessions and revoke tokens (access + refresh).
    """
    try:
        if redis is None:
            redis = await get_redis_client()

        revoked_sessions = 0
        revoked_refresh_tokens = 0

        # Revoke all sessions
        session_keys = await keys(f"sessions:{user_id}:*", redis=redis)
        for key in session_keys:
            session_data = await hgetall(key, redis=redis)
            await delete(key, redis=redis)
            revoked_sessions += 1

            jti = session_data.get("jti") if isinstance(session_data, dict) else None
            if jti:
                await revoke_token(jti, ttl=900, redis=redis)

        # Revoke all refresh tokens
        refresh_keys = await keys(f"refresh_tokens:{user_id}:*", redis=redis)
        for rkey in refresh_keys:
            await delete(rkey, redis=redis)
            jti = rkey.split(":")[-1]
            if jti:
                await revoke_token(jti, ttl=86400, redis=redis)
            revoked_refresh_tokens += 1

        log_info("User fully logged out", extra={
            "user_id": user_id,
            "revoked_sessions": revoked_sessions,
            "revoked_refresh_tokens": revoked_refresh_tokens,
            "ip": client_ip,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return {
            "message": get_message("auth.logout.all", language),
            "revoked_sessions": revoked_sessions,
            "revoked_refresh_tokens": revoked_refresh_tokens
        }

    except Exception as e:
        log_error("Logout failed", extra={
            "user_id": user_id,
            "session_id": session_id,
            "error": str(e),
            "ip": client_ip
        }, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_message("server.error", language)
        )
