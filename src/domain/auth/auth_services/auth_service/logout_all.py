# File: domain/auth/auth_services/auth_service/logout_all.py

from fastapi import HTTPException, status
from common.security.jwt_handler import revoke_all_user_tokens, revoke_token
from infrastructure.database.redis.redis_client import keys, delete, get
from common.logging.logger import log_info, log_error
from datetime import datetime, timezone
from infrastructure.database.redis.redis_client import hgetall


async def logout_all_service(user_id: str, client_ip: str) -> dict:
    try:
        # === Revoke all sessions and refresh tokens ===
        session_keys = keys(f"sessions:{user_id}:*")
        revoked_sessions = 0

        for key in session_keys:
            session_data = hgetall(key)
            delete(key)
            revoked_sessions += 1

            # Try to revoke access token too (if jti exists in session)
            if isinstance(session_data, dict):
                jti = session_data.get("jti")
                if jti:
                    revoke_token(jti, 900)  # Revoke access token (15 min TTL)

        # Revoke all refresh tokens
        refresh_keys = keys(f"refresh_tokens:{user_id}:*")
        for rkey in refresh_keys:
            delete(rkey)
            jti = rkey.split(":")[-1]
            revoke_token(jti, 86400)

        log_info("User logged out from all sessions", extra={
            "user_id": user_id,
            "revoked_sessions": revoked_sessions,
            "revoked_refresh_tokens": len(refresh_keys),
            "ip": client_ip,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return {
            "message": "Logged out from all sessions successfully",
            "revoked_sessions": revoked_sessions,
            "revoked_refresh_tokens": len(refresh_keys)
        }

    except Exception as e:
        log_error("Logout all failed", extra={
            "user_id": user_id,
            "error": str(e),
            "ip": client_ip
        })
        raise HTTPException(status_code=500, detail="Failed to log out from all sessions")
