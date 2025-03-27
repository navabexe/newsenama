# domain/auth/auth_services/otp_service/verify.py - نسخه اصلاح شده

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from redis.asyncio import Redis

from common.logging.logger import log_info, log_error
from common.translations.messages import get_message
from common.security.jwt.tokens import (
    generate_access_token,
    generate_refresh_token,
    generate_temp_token
)
from common.security.jwt.decode import decode_token
from infrastructure.database.mongodb.mongo_client import find_one, insert_one, update_one
from infrastructure.database.redis.operations.delete import delete
from infrastructure.database.redis.operations.get import get
from infrastructure.database.redis.operations.hset import hset
from infrastructure.database.redis.operations.expire import expire
from infrastructure.database.redis.redis_client import get_redis_client


async def verify_otp_service(
    otp: str,
    temporary_token: str,
    client_ip: str,
    language: str = "fa",
    redis: Redis = None
) -> dict:
    try:
        if redis is None:
            redis = await get_redis_client()

        payload = await decode_token(temporary_token, token_type="temp", redis=redis)

        phone = payload.get("sub")
        role = payload.get("role")
        jti = payload.get("jti")
        status = payload.get("status", "incomplete")

        if not phone or not role or not jti:
            raise HTTPException(status_code=401, detail=get_message("token.invalid", language))

        redis_key = f"otp:{role}:{phone}"
        temp_key = f"temp_token:{jti}"

        stored_otp = await get(redis_key, redis)
        if stored_otp != otp:
            log_error("Invalid OTP", extra={"phone": phone, "ip": client_ip})
            raise HTTPException(status_code=401, detail=get_message("otp.invalid", language))

        if await get(temp_key, redis) != phone:
            raise HTTPException(status_code=401, detail=get_message("otp.expired", language))

        await delete(redis_key, redis)
        await delete(temp_key, redis)

        collection = f"{role}s"
        user = await find_one(collection, {"phone": phone})

        if not user:
            user_data = {
                "phone": phone,
                "role": role,
                "status": "incomplete",
                "phone_verified": True,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            user_id = str(await insert_one(collection, user_data))
            user = {"_id": user_id, **user_data}
        else:
            user_id = str(user["_id"])
            if not user.get("phone_verified"):
                await update_one(collection, {"_id": user["_id"]}, {
                    "phone_verified": True,
                    "updated_at": datetime.now(timezone.utc)
                })

        status = user.get("status")
        role = user.get("role", role)

        user_profile = {
            "first_name": str(user.get("first_name")) if user.get("first_name") else None,
            "last_name": str(user.get("last_name")) if user.get("last_name") else None,
            "email": str(user.get("email")) if user.get("email") else None,
            "phone": str(user.get("phone")) if user.get("phone") else None,
            "business_name": user.get("business_name"),
            "location": user.get("location"),
            "address": user.get("address"),
            "status": user.get("status"),
            "business_category_ids": user.get("business_category_ids", []),
            "profile_picture": user.get("profile_picture")
        }

        if status == "incomplete":
            new_jti = str(uuid4())
            temp_token = await generate_temp_token(
                phone=phone,
                role=role,
                jti=new_jti,
                status="incomplete",
                phone_verified=True,
                language=language,
            )
            await redis.setex(f"temp_token:{new_jti}", 86400, phone)
            return {
                "temporary_token": temp_token,
                "refresh_token": None,
                "next_action": "complete_profile",
                "status": "incomplete",
                "message": get_message("auth.profile.incomplete", language)
            }

        elif status == "pending" and role == "vendor":
            new_jti = str(uuid4())
            temp_token = await generate_temp_token(
                phone=phone,
                role=role,
                jti=new_jti,
                status="pending",
                phone_verified=True,
                language=language,
            )
            await redis.setex(f"temp_token:{new_jti}", 86400, phone)
            return {
                "temporary_token": temp_token,
                "refresh_token": None,
                "next_action": "await_admin_approval",
                "status": "pending",
                "message": get_message("auth.profile.pending", language)
            }

        elif status == "active":
            session_id = str(uuid4())
            access_token = await generate_access_token(
                user_id=user_id,
                role=role,
                session_id=session_id,
                user_profile=user_profile,
                language=language,
            )
            refresh_token = await generate_refresh_token(
                user_id=user_id,
                role=role,
                session_id=session_id,
            )

            session_key = f"sessions:{user_id}:{session_id}"
            key_type = await redis.type(session_key)
            if key_type != b'hash' and key_type != b'none':
                await redis.delete(session_key)

            await hset(session_key, mapping={
                "ip": client_ip,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "device": "unknown",
                "status": "active",
                "jti": session_id
            }, redis=redis)
            await expire(session_key, 86400, redis=redis)

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "next_action": None,
                "status": "active",
                "message": get_message("auth.login.success", language)
            }

        raise HTTPException(status_code=400, detail=get_message("server.error", language))

    except HTTPException:
        raise
    except Exception as e:
        log_error("OTP verification failed", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(status_code=500, detail=get_message("server.error", language))