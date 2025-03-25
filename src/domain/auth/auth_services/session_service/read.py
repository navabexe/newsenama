# File: domain/auth/auth_services/session_service/read.py

from fastapi import HTTPException, status
from infrastructure.database.redis.redis_client import keys, hgetall
from common.logging.logger import log_info, log_error
from datetime import datetime, timezone

async def get_sessions_service(user_id: str, client_ip: str) -> dict:
    """Handle retrieval of all active sessions for a user."""
    try:
        # Get all session keys for the user
        session_keys = keys(f"sessions:{user_id}:*")
        sessions = []

        for key in session_keys:
            session_data = hgetall(key)
            session_id = key.split(":")[-1]
            sessions.append({
                "session_id": session_id,
                "ip": session_data.get("ip", "unknown"),
                "created_at": session_data.get("created_at", "unknown"),
                "last_refreshed": session_data.get("last_refreshed", None)
            })

        # Log success
        log_info("Sessions retrieved", extra={
            "user_id": user_id,
            "session_count": len(sessions),
            "ip": client_ip,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return {"sessions": sessions, "message": "Active sessions retrieved"}

    except Exception as e:
        log_error("Session retrieval failed", extra={
            "user_id": user_id,
            "error": str(e),
            "ip": client_ip
        })
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve sessions")