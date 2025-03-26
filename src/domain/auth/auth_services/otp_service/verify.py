# File: domain/auth/auth_services/otp_service/verify.py

from fastapi import HTTPException
from common.security.jwt_handler import (
    decode_token, generate_temp_token, generate_access_token, generate_refresh_token
)
from infrastructure.database.redis.redis_client import get, delete, hset, setex
from infrastructure.database.mongodb.mongo_client import find_one, insert_one, update_one
from common.logging.logger import log_info, log_error
from datetime import datetime, timezone
from uuid import uuid4
import traceback


async def verify_otp_service(otp: str, temporary_token: str, client_ip: str) -> dict:
    try:
        print("==[START]==")

        payload = decode_token(temporary_token, "temp")
        print("✅ PAYLOAD:", payload)

        phone = payload["sub"]
        role = payload["role"]
        jti = payload["jti"]
        redis_key = f"otp:{role}:{phone}"
        token_key = f"temp_token:{jti}"

        stored_otp = get(redis_key)
        print("✅ OTP from Redis:", stored_otp)

        if stored_otp != otp:
            print("❌ OTP mismatch")
            raise HTTPException(status_code=401, detail="Invalid OTP")

        if get(token_key) != phone:
            print("❌ Token phone mismatch")
            raise HTTPException(status_code=401, detail="Invalid temp token")

        delete(redis_key)
        delete(token_key)
        print("✅ Redis keys deleted")

        collection = f"{role}s"
        user = await find_one(collection, {"phone": phone})
        print("✅ USER FIND:", user)

        if not user:
            print("🆕 No user found, creating...")
            user_data = {
                "phone": phone,
                "role": role,
                "status": "incomplete",
                "phone_verified": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            user_id = await insert_one(collection, user_data)
            print("✅ User created:", user_id)
            user = {"_id": user_id, "status": "incomplete", "phone_verified": True}
        else:
            user_id = str(user["_id"])
            print("✅ User exists:", user_id)
            if not user.get("phone_verified", False):
                await update_one(collection, {"_id": user_id}, {
                    "phone_verified": True,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                })
                print("✅ User phone verified")

        status = user.get("status")
        print("✅ User status:", status)

        if status == "incomplete":
            new_jti = str(uuid4())
            new_temp_token = await generate_temp_token(
                phone=phone,
                role=role,
                jti=new_jti,
                phone_verified=True
            )
            setex(f"temp_token:{new_jti}", 86400, phone)
            print("✅ Temp token issued for incomplete user")
            return {
                "temporary_token": new_temp_token,
                "refresh_token": None,
                "next_action": "complete_profile",
                "status": "incomplete",
                "message": "Please complete your profile"
            }

        elif status == "pending" and role == "vendor":
            print("✅ Vendor pending")
            return {
                "temporary_token": temporary_token,
                "refresh_token": None,
                "next_action": "await_admin_approval",
                "status": "pending",
                "message": "Profile is pending admin approval"
            }

        elif status == "active":
            session_id = str(uuid4())
            print("✅ Generating access tokens")
            access_token = await generate_access_token(user_id, role, session_id)
            refresh_token = await generate_refresh_token(user_id, role, session_id)
            hset(f"sessions:{user_id}:{session_id}", mapping={
                "ip": client_ip,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "device": "unknown",
                "status": "active"
            })
            print("✅ Login complete")
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "next_action": None,
                "status": "active",
                "message": "Login successful"
            }

        print("❌ Unknown status:", status)
        raise HTTPException(status_code=403, detail=f"Unsupported status: {status}")

    except HTTPException as e:
        print("❗ HTTPException:", e.detail)
        raise e
    except Exception as e:
        print("❗ Unhandled exception:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to verify OTP")