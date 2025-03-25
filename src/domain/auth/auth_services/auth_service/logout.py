from fastapi import HTTPException, status
from common.security.jwt_handler import revoke_token
from infrastructure.database.redis.redis_client import delete, get
from common.logging.logger import log_info, log_error
from datetime import datetime, timezone

async def logout_service(user_id: str, session_id: str, client_ip: str) -> dict:
    """
    Handle logout logic by invalidating the current session.

    Args:
        user_id (str): ID of the user.
        session_id (str): ID of the session to invalidate.
        client_ip (str): Client's IP address.

    Returns:
        dict: Confirmation message.

    Raises:
        HTTPException: If logout fails.
    """
    try:
        session_key = f"sessions:{user_id}:{session_id}"
        token_key = f"refresh_tokens:{user_id}:*"

        # Check if session exists
        session_data = get(session_key)
        if not session_data:
            log_error("Session not found", extra={"user_id": user_id, "session_id": session_id, "ip": client_ip})
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session not found")

        # Delete session
        delete(session_key)

        # Revoke refresh token (assuming jti is stored in token)
        refresh_token_key = f"refresh_tokens:{user_id}:{session_id}"
        if get(refresh_token_key):
            delete(refresh_token_key)
            revoke_token(session_id, 86400)  # Revoke for 1 day

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