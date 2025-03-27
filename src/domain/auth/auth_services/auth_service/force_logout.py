# force_logout_service.py - نسخه اصلاح‌شده با بررسی نوع کلید Redis قبل از حذف و عملیات revoke

from datetime import datetime, timezone

from fastapi import HTTPException, status
from redis.asyncio import Redis

from common.logging.logger import log_info, log_error
from common.translations.messages import get_message
from common.security.jwt_handler import revoke_token
from infrastructure.database.redis.operations.delete import delete
from infrastructure.database.redis.operations.hgetall import hgetall
from infrastructure.database.redis.operations.keys import keys
from infrastructure.database.redis.redis_client import get_redis_client


async def force_logout_service(
    current_user: dict,
    target_user_id: str,
    client_ip: str,
    redis: Redis = None,
    language: str = "fa"
) -> dict:
    try:
        if redis is None:
            redis = await get_redis_client()

        if current_user.get("role") != "admin":
            log_error("Unauthorized force logout attempt", extra={
                "user_id": current_user.get("user_id"),
                "target_user_id": target_user_id,
                "ip": client_ip
            })
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=get_message("auth.forbidden", language))

        # Revoke all sessions
        session_keys = await keys(f"sessions:{target_user_id}:*", redis=redis)
        revoked_sessions = 0

        for key in session_keys:
            key_type = await redis.type(key)
            if key_type != b'hash':
                continue

            session_data = await hgetall(key, redis=redis)
            await delete(key, redis=redis)
            revoked_sessions += 1

            jti = session_data.get("jti") if isinstance(session_data, dict) else None
            if jti:
                await revoke_token(jti, ttl=900, redis=redis)

        # Revoke refresh tokens
        refresh_keys = await keys(f"refresh_tokens:{target_user_id}:*", redis=redis)
        for rkey in refresh_keys:
            await delete(rkey, redis=redis)
            jti = rkey.split(":")[-1]
            if jti:
                await revoke_token(jti, ttl=86400, redis=redis)

        log_info("User force logged out", extra={
            "admin_id": current_user.get("user_id"),
            "target_user_id": target_user_id,
            "revoked_sessions": revoked_sessions,
            "revoked_refresh_tokens": len(refresh_keys),
            "ip": client_ip,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return {
            "message": get_message("auth.force_logout.success", language),
            "revoked_sessions": revoked_sessions,
            "revoked_refresh_tokens": len(refresh_keys)
        }

    except HTTPException:
        raise
    except Exception as e:
        log_error("Force logout failed", extra={
            "admin_id": current_user.get("user_id"),
            "target_user_id": target_user_id,
            "error": str(e),
            "ip": client_ip
        })
        raise HTTPException(
            status_code=500,
            detail=get_message("server.error", language)
        )