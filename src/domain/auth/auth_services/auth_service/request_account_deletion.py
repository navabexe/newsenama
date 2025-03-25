# File: domain/auth/auth_services/auth_service/request_account_deletion.py

from fastapi import HTTPException, status
from common.security.jwt_handler import revoke_all_user_tokens
from infrastructure.database.mongodb.mongo_client import update_one
from common.logging.logger import log_info, log_error
from datetime import datetime, timezone

async def request_account_deletion_service(user_id: str, client_ip: str) -> dict:
    """Handle account deletion request logic."""
    try:
        # Mark account for deletion
        update_one("users", {"_id": user_id}, {
            "status": "pending_deletion",
            "deletion_requested_at": datetime.now(timezone.utc)
        })

        # Revoke all tokens and sessions
        revoke_all_user_tokens(user_id)

        # Log success
        log_info("Account deletion requested", extra={
            "user_id": user_id,
            "ip": client_ip,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return {"message": "Account deletion request submitted. It will be processed soon."}

    except Exception as e:
        log_error("Account deletion request failed", extra={
            "user_id": user_id,
            "error": str(e),
            "ip": client_ip
        })
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to request account deletion")