# File: domain/auth/auth_services/auth_service/logout.py
from datetime import datetime, timezone
from fastapi import HTTPException, status
from redis.asyncio import Redis

from common.logging.logger import log_info, log_error
from common.security.jwt_handler import revoke_token
from common.translations.messages import get_message
from infrastructure.database.redis.operations.delete import delete
from infrastructure.database.redis.operations.hgetall import hgetall
from infrastructure.database.redis.operations.keys import keys
from infrastructure.database.redis.redis_client import get_redis_client

async def logout_service(
    user_id: str,
    session_id: str,
    client_ip: str,
    redis: Redis = None,
    language: str = "fa"
) -> dict:
    """
    Logout user from all sessions and revoke all refresh tokens.

    Args:
        user_id (str): User ID.
        session_id (str): Current session ID (for logging).
        client_ip (str): Client IP address.
        redis (Redis): Redis client instance.
        language (str): Language for response messages.

    Returns:
        dict: Logout result with revoked counts.
    """
    try:
        if redis is None:
            redis = await get_redis_client()

        revoked_sessions = 0
        revoked_refresh_tokens = 0

        # حذف همه سشن‌ها
        session_keys = await keys(f"sessions:{user_id}:*", redis=redis)
        for key in session_keys:
            session_data = await hgetall(key, redis=redis)
            deleted = await delete(key, redis=redis)
            if deleted:
                revoked_sessions += 1
                jti = session_data.get("jti") if isinstance(session_data, dict) else None
                if jti:
                    await revoke_token(jti, ttl=900, redis=redis)
                    log_info("Session token revoked", extra={"jti": jti, "user_id": user_id})

        # حذف همه توکن‌های رفرش
        refresh_keys = await keys(f"refresh_tokens:{user_id}:*", redis=redis)
        for rkey in refresh_keys:
            deleted = await delete(rkey, redis=redis)
            if deleted:
                revoked_refresh_tokens += 1
                jti = rkey.split(":")[-1]
                if jti:
                    await revoke_token(jti, ttl=86400, redis=redis)
                    log_info("Refresh token revoked", extra={"jti": jti, "user_id": user_id})

        log_info("User fully logged out", extra={
            "user_id": user_id,
            "revoked_sessions": revoked_sessions,
            "revoked_refresh_tokens": revoked_refresh_tokens,
            "ip": client_ip,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        if revoked_sessions == 0 and revoked_refresh_tokens == 0:
            log_info("No sessions or refresh tokens found to revoke", extra={"user_id": user_id})

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