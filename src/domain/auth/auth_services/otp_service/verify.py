# File: domain/auth/auth_services/otp_service/verify.py

from fastapi import HTTPException
from common.security.jwt_handler import decode_token, generate_temp_token, generate_access_token, generate_refresh_token
from infrastructure.database.redis.redis_client import get, delete, hset, setex
from infrastructure.database.mongodb.mongo_client import find_one, insert_one, update_one
from common.logging.logger import log_info, log_error
from datetime import datetime, timezone
from uuid import uuid4

async def verify_otp_service(otp: str, temporary_token: str, client_ip: str) -> dict:
    try:
        payload = decode_token(temporary_token, "temp")
        phone = payload["sub"]
        role = payload["role"]
        jti = payload["jti"]
        redis_key = f"otp:{role}:{phone}"
        token_key = f"temp_token:{jti}"

        stored_otp = get(redis_key)
        if not stored_otp or stored_otp != otp:
            log_error("Invalid or expired OTP", extra={"phone": phone, "jti": jti, "ip": client_ip})
            raise HTTPException(status_code=401, detail="Invalid or expired OTP")

        if get(token_key) != phone:
            log_error("Invalid temporary token", extra={"phone": phone, "jti": jti, "ip": client_ip})
            raise HTTPException(status_code=401, detail="Invalid temporary token")

        # Clean up OTP and temp token
        delete(redis_key)
        delete(token_key)

        collection = f"{role}s"
        user = find_one(collection, {"phone": phone})

        if not user:
            user_data = {
                "phone": phone,
                "role": role,
                "status": "incomplete",
                "phone_verified": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            user_id = insert_one(collection, user_data)
            user = {"_id": user_id, "status": "incomplete", "phone_verified": True}
        else:
            user_id = str(user["_id"])
            if not user.get("phone_verified"):
                update_one(collection, {"_id": user_id}, {
                    "phone_verified": True,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                })

        log_info("OTP verified", extra={
            "phone": phone,
            "role": role,
            "user_id": user_id,
            "ip": client_ip,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        if user["status"] == "incomplete":
            new_jti = str(uuid4())
            new_temp_token = generate_temp_token(phone=phone, role=role, jti=new_jti, phone_verified=True)
            setex(f"temp_token:{new_jti}", 86400, phone)  # 1 day TTL
            return {
                "temporary_token": new_temp_token,
                "refresh_token": None,
                "next_action": "complete_profile",
                "status": "incomplete",
                "message": "Please complete your profile"
            }

        elif user["status"] == "pending" and role == "vendor":
            return {
                "temporary_token": temporary_token,
                "refresh_token": None,
                "next_action": "await_admin_approval",
                "status": "pending",
                "message": "Profile is pending admin approval"
            }

        elif user["status"] == "active":
            session_id = str(uuid4())
            access_token = generate_access_token(user_id, role, session_id)
            refresh_token = generate_refresh_token(user_id, role, session_id)
            hset(f"sessions:{user_id}:{session_id}", mapping={
                "ip": client_ip,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "next_action": None,
                "status": "active",
                "message": "Login successful"
            }

        log_error("Invalid user status", extra={"phone": phone, "status": user["status"], "ip": client_ip})
        raise HTTPException(status_code=403, detail=f"Account status: {user['status']}")

    except HTTPException as e:
        raise e
    except Exception as e:
        log_error("OTP verification failed", extra={
            "phone": phone if "phone" in locals() else "unknown",
            "error": str(e),
            "ip": client_ip
        })
        raise HTTPException(status_code=500, detail="Failed to verify OTP")
