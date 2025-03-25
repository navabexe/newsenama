# File: domain/auth/auth_services/auth_service/force_logout.py

from fastapi import HTTPException, status
from common.security.jwt_handler import revoke_all_user_tokens, revoke_token
from infrastructure.database.redis.redis_client import keys, delete, get
from common.logging.logger import log_info, log_error
from datetime import datetime, timezone
from infrastructure.database.redis.redis_client import hgetall


async def force_logout_service(current_user: dict, target_user_id: str, client_ip: str) -> dict:
    try:
        if current_user["role"] != "admin":
            log_error("Unauthorized force logout attempt", extra={
                "user_id": current_user["user_id"],
                "target_user_id": target_user_id,
                "ip": client_ip
            })
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

        session_keys = keys(f"sessions:{target_user_id}:*")
        revoked_sessions = 0

        for key in session_keys:
            session_data = hgetall(key)
            delete(key)
            revoked_sessions += 1

            if isinstance(session_data, dict):
                jti = session_data.get("jti")
                if jti:
                    revoke_token(jti, 900)

        refresh_keys = keys(f"refresh_tokens:{target_user_id}:*")
        for rkey in refresh_keys:
            delete(rkey)
            jti = rkey.split(":")[-1]
            revoke_token(jti, 86400)

        log_info("User force logged out", extra={
            "admin_id": current_user["user_id"],
            "target_user_id": target_user_id,
            "revoked_sessions": revoked_sessions,
            "revoked_refresh_tokens": len(refresh_keys),
            "ip": client_ip,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return {
            "message": f"User {target_user_id} logged out successfully",
            "revoked_sessions": revoked_sessions,
            "revoked_refresh_tokens": len(refresh_keys)
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        log_error("Force logout failed", extra={
            "admin_id": current_user["user_id"],
            "target_user_id": target_user_id,
            "error": str(e),
            "ip": client_ip
        })
        raise HTTPException(status_code=500, detail="Failed to force logout")