# File: domain/auth/auth_services/auth_service/force_logout_service.py

from datetime import datetime, timezone
from fastapi import HTTPException, status
from redis.asyncio import Redis
from common.logging.logger import log_info, log_error
from common.translations.messages import get_message
from infrastructure.database.redis.operations.redis_operations import keys, delete, hgetall, setex
from infrastructure.database.redis.redis_client import get_redis_client

async def force_logout_service(
    current_user: dict,
    target_user_id: str,
    client_ip: str,
    redis: Redis = None,
    language: str = "fa"
) -> dict:
    try:
        log_info("Starting force logout process - v5", extra={
            "target_user_id": target_user_id,
            "client_ip": client_ip,
            "admin_id": current_user.get("user_id")
        })

        if redis is None:
            redis = await get_redis_client()
            log_info("Initialized new Redis client - v5", extra={"target_user_id": target_user_id})

        if current_user.get("role") != "admin":
            log_error("Force logout attempt by non-admin - v5", extra={
                "user_id": current_user.get("user_id"),
                "target_user_id": target_user_id,
                "ip": client_ip
            })
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=get_message("auth.forbidden", language))

        revoked_jtis = []
        current_time = int(datetime.now(timezone.utc).timestamp())

        # حذف سشن‌ها
        session_keys = await keys(f"sessions:{target_user_id}:*", redis=redis)
        log_info("Retrieved session keys from Redis - v5", extra={"target_user_id": target_user_id, "session_keys": session_keys})
        revoked_sessions = 0

        for key in session_keys:
            key_type = await redis.type(key)
            key_type_str = key_type.decode() if isinstance(key_type, bytes) else key_type
            log_info("Evaluating session key type - v5", extra={"key": key, "type": key_type_str})
            if key_type_str == 'hash':
                log_info("Processing hash-type session key - v5", extra={"key": key})
                session_data = await hgetall(key, redis=redis)
                log_info("Fetched session data before deletion - v5", extra={"key": key, "session_data": session_data})
                jti = session_data.get("jti") if isinstance(session_data, dict) else None
                if jti and jti not in revoked_jtis:
                    revoked_jtis.append(jti)
                    log_info("Extracted jti from session - v5", extra={"jti": jti, "key": key})
                deleted = await delete(key, redis=redis)
                if deleted:
                    revoked_sessions += 1
                    log_info("Session key successfully deleted - v5", extra={"key": key, "revoked_count": revoked_sessions})
            else:
                log_info("Ignoring non-hash session key - v5", extra={"key": key, "type": key_type_str})

        # حذف رفرش توکن‌ها
        refresh_keys = await keys(f"refresh_tokens:{target_user_id}:*", redis=redis)
        log_info("Retrieved refresh token keys - v5", extra={"target_user_id": target_user_id, "refresh_keys": refresh_keys})
        revoked_refresh_tokens = 0

        for rkey in refresh_keys:
            key_type = await redis.type(rkey)
            key_type_str = key_type.decode() if isinstance(key_type, bytes) else key_type
            log_info("Evaluating refresh token key type - v5", extra={"key": rkey, "type": key_type_str})
            if key_type_str in ['hash', 'string']:
                log_info("Processing refresh token key - v5", extra={"key": rkey, "type": key_type_str})
                if key_type_str == 'hash':
                    session_data = await hgetall(rkey, redis=redis)
                    jti = session_data.get("jti") if isinstance(session_data, dict) else None
                else:  # string
                    jti = rkey.split(":")[-1]
                if jti and jti not in revoked_jtis:
                    revoked_jtis.append(jti)
                    log_info("Extracted jti from refresh token - v5", extra={"jti": jti, "key": rkey})
                deleted = await delete(rkey, redis=redis)
                if deleted:
                    revoked_refresh_tokens += 1
                    log_info("Refresh token key deleted - v5", extra={"key": rkey, "revoked_count": revoked_refresh_tokens})
            else:
                log_info("Ignoring unsupported refresh token key - v5", extra={"key": rkey, "type": key_type_str})

        # باطل کردن JTI‌ها در لیست سیاه
        for jti in revoked_jtis:
            blacklist_key = f"blacklist:{jti}"
            # TTL بر اساس نوع: 24 ساعت برای سشن، 30 روز برای رفرش توکن
            ttl = 2592000 if jti in [rkey.split(":")[-1] for rkey in refresh_keys] else 86400
            ttl = max(ttl - (current_time - 1744231142), 0)  # کسر زمان سپری‌شده از زمان تولید توکن
            await setex(blacklist_key, ttl, "revoked", redis=redis)
            log_info("JTI added to blacklist - v5", extra={"jti": jti, "ttl": ttl, "user_id": target_user_id})

        log_info("Force logout completed - v5", extra={
            "admin_id": current_user.get("user_id"),
            "target_user_id": target_user_id,
            "revoked_sessions": revoked_sessions,
            "revoked_refresh_tokens": revoked_refresh_tokens,
            "revoked_jtis": revoked_jtis,
            "ip": client_ip,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        if revoked_sessions == 0 and revoked_refresh_tokens == 0 and not session_keys and not refresh_keys:
            log_error("No sessions or refresh tokens found for target user - v5", extra={"target_user_id": target_user_id})
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=get_message("auth.force_logout.no_sessions_found", language)
            )

        return {
            "message": get_message("auth.force_logout.success", language),
            "revoked_sessions": revoked_sessions,
            "revoked_refresh_tokens": revoked_refresh_tokens,
            "revoked_token_ids": revoked_jtis
        }

    except HTTPException:
        raise
    except Exception as e:
        log_error("Force logout process crashed - v5", extra={
            "admin_id": current_user.get("user_id"),
            "target_user_id": target_user_id,
            "error": str(e),
            "ip": client_ip
        })
        raise HTTPException(
            status_code=500,
            detail=get_message("server.error", language)
        )