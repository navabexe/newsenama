# File: domain/auth/auth_services/auth_service/complete_user_profile.py

from fastapi import HTTPException, status
from common.security.jwt_handler import decode_token, generate_access_token, generate_refresh_token
from infrastructure.database.redis.redis_client import get, delete, hset
from infrastructure.database.mongodb.mongo_client import find_one, update_one
from common.logging.logger import log_info, log_error
from datetime import datetime, timezone
from uuid import uuid4

async def complete_user_profile_service(temporary_token: str, first_name: str, last_name: str, email: str, client_ip: str) -> dict:
    """Handle user profile completion logic."""
    try:
        # Decode temporary token
        payload = decode_token(temporary_token, "temp")
        phone = payload["sub"]
        role = payload["role"]
        jti = payload["jti"]
        token_key = f"temp_token:{jti}"

        # Verify token and role
        if get(token_key) != phone:
            log_error("Invalid temporary token", extra={"phone": phone, "jti": jti, "ip": client_ip})
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid temporary token")
        if role != "user":
            log_error("Role mismatch", extra={"phone": phone, "role": role, "ip": client_ip})
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This endpoint is for users only")

        # Check user in MongoDB
        user = find_one("users", {"phone": phone})
        if not user or user["status"] != "incomplete":
            log_error("User not found or already complete", extra={"phone": phone, "ip": client_ip})
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profile not eligible for completion")

        user_id = str(user["_id"])

        # Update profile
        update_one("users", {"_id": user_id}, {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "status": "active",
            "updated_at": datetime.now(timezone.utc)
        })

        # Clean up Redis
        delete(token_key)

        # Generate full tokens
        session_id = str(uuid4())
        access_token = generate_access_token(user_id, role, session_id)
        refresh_token = generate_refresh_token(user_id, role, session_id)

        # Store session info
        hset(f"sessions:{user_id}:{session_id}", mapping={
            "ip": client_ip,
            "created_at": datetime.now(timezone.utc).isoformat()
        })

        # Log success
        log_info("User profile completed", extra={
            "user_id": user_id,
            "phone": phone,
            "email": email,
            "ip": client_ip,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "status": "active",
            "message": "Profile completed successfully"
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        log_error("Profile completion failed", extra={
            "phone": phone if "phone" in locals() else "unknown",
            "error": str(e),
            "ip": client_ip
        })
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to complete profile")