# File: domain/auth/auth_services/auth_service/logout_all.py

from fastapi import HTTPException, status
from common.security.jwt_handler import revoke_all_user_tokens
from infrastructure.database.redis.redis_client import keys, delete
from common.logging.logger import log_info, log_error
from datetime import datetime, timezone

async def logout_all_service(user_id: str, client_ip: str) -> dict:
    """Handle logout from all sessions for a user."""
    try:
        # Revoke all tokens and sessions
        revoke_all_user_tokens(user_id)

        # Log success
        log_info("User logged out from all sessions", extra={
            "user_id": user_id,
            "ip": client_ip,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return {"message": "Logged out from all sessions successfully"}

    except Exception as e:
        log_error("Logout all failed", extra={
            "user_id": user_id,
            "error": str(e),
            "ip": client_ip
        })
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to log out from all sessions")