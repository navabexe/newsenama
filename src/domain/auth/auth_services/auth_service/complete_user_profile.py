# File: domain/auth/auth_services/auth_service/complete_user_profile.py

from fastapi import HTTPException, status
from common.security.jwt_handler import decode_token, generate_access_token, generate_refresh_token
from infrastructure.database.redis.redis_client import get, delete, hset
from infrastructure.database.mongodb.mongo_client import find_one, update_one
from common.logging.logger import log_info, log_error
from datetime import datetime, timezone
from uuid import uuid4

async def complete_user_profile_service(
    temporary_token: str,
    first_name: str,
    last_name: str,
    email: str,
    client_ip: str
) -> dict:
    """
    Complete a user's profile after OTP verification.
    """
    try:
        # Decode and verify temporary token
        payload = decode_token(temporary_token, "temp")
        phone = payload["sub"]
        role = payload["role"]
        jti = payload["jti"]
        token_key = f"temp_token:{jti}"

        if get(token_key) != phone:
            log_error("Invalid temporary token", extra={"jti": jti, "ip": client_ip})
            raise HTTPException(status_code=401, detail="Invalid temporary token")

        if role != "user":
            log_error("Role mismatch", extra={"phone": phone, "role": role, "ip": client_ip})
            raise HTTPException(status_code=403, detail="Only users can complete this profile")

        # Fetch user
        user = await find_one("users", {"phone": phone})
        if not user or user.get("status") != "incomplete":
            log_error("User not eligible for profile completion", extra={"phone": phone, "ip": client_ip})
            raise HTTPException(status_code=400, detail="Profile not eligible for completion")

        user_id = str(user["_id"])

        # Update user profile
        update_result = await update_one("users", {"_id": user_id}, {
            "first_name": first_name.strip(),
            "last_name": last_name.strip(),
            "email": email.strip().lower(),
            "status": "active",
            "updated_at": datetime.now(timezone.utc)
        })

        if update_result == 0:
            raise HTTPException(status_code=500, detail="Failed to update profile")

        # Delete temp token from Redis
        delete(token_key)

        # Generate session and tokens
        session_id = str(uuid4())
        access_token = await generate_access_token(user_id, role, session_id)
        refresh_token = await generate_refresh_token(user_id, role, session_id)

        # Store session in Redis
        hset(f"sessions:{user_id}:{session_id}", mapping={
            "ip": client_ip,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "active",
            "device": "unknown"
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
        }, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to complete profile")
