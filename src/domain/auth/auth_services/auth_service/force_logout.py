# File: domain/auth/auth_services/auth_service/force_logout.py

from fastapi import HTTPException, status
from common.security.jwt_handler import revoke_all_user_tokens
from common.logging.logger import log_info, log_error
from datetime import datetime, timezone

async def force_logout_service(current_user: dict, target_user_id: str, client_ip: str) -> dict:
    """Handle forced logout of a target user by an admin."""
    try:
        # Check if current user is admin
        if current_user["role"] != "admin":
            log_error("Unauthorized force logout attempt", extra={
                "user_id": current_user["user_id"],
                "target_user_id": target_user_id,
                "ip": client_ip
            })
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

        # Revoke all tokens and sessions for target user
        revoke_all_user_tokens(target_user_id)

        # Log success
        log_info("User force logged out", extra={
            "admin_id": current_user["user_id"],
            "target_user_id": target_user_id,
            "ip": client_ip,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return {"message": f"User {target_user_id} logged out successfully"}

    except HTTPException as e:
        raise e
    except Exception as e:
        log_error("Force logout failed", extra={
            "admin_id": current_user["user_id"],
            "target_user_id": target_user_id,
            "error": str(e),
            "ip": client_ip
        })
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to force logout")