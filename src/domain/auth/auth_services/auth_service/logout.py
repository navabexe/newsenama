# File: domain/auth/auth_services/auth_service/logout.py

from fastapi import HTTPException, status
from common.security.jwt_handler import revoke_token
from infrastructure.database.redis.redis_client import delete, get
from common.logging.logger import log_info, log_error
from datetime import datetime, timezone
from infrastructure.database.redis.redis_client import hgetall  # اضافه کن


async def logout_service(user_id: str, session_id: str, client_ip: str) -> dict:
    try:
        session_key = f"sessions:{user_id}:{session_id}"
        refresh_token_key = f"refresh_tokens:{user_id}:{session_id}"

        # Check if session exists
        session_data = hgetall(session_key)
        if not session_data:
            log_error("Session not found", extra={"user_id": user_id, "session_id": session_id, "ip": client_ip})
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session not found")

        # Delete session
        delete(session_key)

        # Revoke refresh token (if present)
        if get(refresh_token_key):
            delete(refresh_token_key)
            revoke_token(session_id, 86400)

        # Revoke access token via jti (optional, if sent in payload)
        jti = session_data.get("jti") if isinstance(session_data, dict) else None
        if jti:
            revoke_token(jti, 900)  # Match access TTL

        log_info("Logout successful", extra={
            "user_id": user_id,
            "session_id": session_id,
            "ip": client_ip,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return {
            "message": "Logout successful"
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        log_error("Logout failed", extra={
            "user_id": user_id if "user_id" in locals() else "unknown",
            "session_id": session_id if "session_id" in locals() else "unknown",
            "error": str(e),
            "ip": client_ip
        })
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to logout")
