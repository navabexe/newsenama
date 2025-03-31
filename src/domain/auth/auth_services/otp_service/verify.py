# File: domain/auth/auth_services/otp_service/verify.py
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from redis.asyncio import Redis
from jose import jwt

from common.config.settings import settings
from common.logging.logger import log_error
from common.translations.messages import get_message
from common.security.jwt.decode import decode_token
from common.security.jwt.payload_builder import build_jwt_payload
from infrastructure.database.mongodb.mongo_client import find_one, insert_one, update_one
from infrastructure.database.redis.operations.delete import delete
from infrastructure.database.redis.operations.get import get
from infrastructure.database.redis.operations.hset import hset
from infrastructure.database.redis.operations.expire import expire
from infrastructure.database.redis.redis_client import get_redis_client
from infrastructure.database.redis.operations.scan import scan_keys

async def delete_incomplete_sessions(user_id: str, redis: Redis):
    """Delete all incomplete sessions for a user from Redis."""
    session_keys = await scan_keys(redis, f"sessions:{user_id}:*")
    for key in session_keys:
        session_data = await redis.hgetall(key)
        status = session_data.get(b"status")
        if status and status.decode() != "active":
            await redis.delete(key)

async def verify_otp_service(
    otp: str,
    temporary_token: str,
    client_ip: str,
    language: str = "fa",
    redis: Redis = None
) -> dict:
    """
    Verify an OTP and issue appropriate tokens or instructions.

    Args:
        otp (str): 6-digit one-time password.
        temporary_token (str): Temporary token from OTP request.
        client_ip (str): Client IP address.
        language (str): Language for response messages (e.g., 'fa', 'en').
        redis (Redis): Redis client instance.

    Returns:
        dict: Response with tokens or next action instructions.

    Raises:
        HTTPException: On invalid OTP, token, or internal errors.
    """
    try:
        redis = redis or await get_redis_client()
        payload = await decode_token(temporary_token, token_type="temp", redis=redis)

        phone = payload.get("sub")
        role = payload.get("role")
        jti = payload.get("jti")

        if not phone or not role or not jti:
            raise HTTPException(status_code=401, detail=get_message("token.invalid", language))

        redis_key = f"otp:{role}:{phone}"
        temp_key = f"temp_token:{jti}"

        if await get(redis_key, redis) != otp or await get(temp_key, redis) != phone:
            log_error("Invalid or expired OTP", extra={"phone": phone, "ip": client_ip})
            raise HTTPException(status_code=401, detail=get_message("otp.invalid", language))

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
                "preferred_languages": [language],
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
            user_id = str(await insert_one(collection, user_data))
            user = {"_id": user_id, **user_data}
        else:
            user_id = str(user["_id"])
            update_fields = {"updated_at": datetime.now(timezone.utc)}
            if not user.get("phone_verified"):
                update_fields["phone_verified"] = True
            if not user.get("preferred_languages"):
                update_fields["preferred_languages"] = [language]
            if update_fields:
                await update_one(collection, {"_id": user["_id"]}, update_fields)

        status = user.get("status")
        role = user.get("role", role)

        profile_data = {
            "first_name": user.get("first_name"),
            "last_name": user.get("last_name"),
            "email": user.get("email"),
            "phone": user.get("phone"),
            "bio": user.get("bio"),
            "avatar_urls": user.get("avatar_urls", []),
            "additional_phones": user.get("additional_phones", []),
            "birthdate": user.get("birthdate"),
            "gender": user.get("gender"),
            "preferred_languages": user.get("preferred_languages", []),
            "status": user.get("status"),
        }

        response_language = language
        profile_language = profile_data["preferred_languages"][0] if profile_data["preferred_languages"] else language

        if status in ["incomplete", "pending"]:
            new_jti = str(uuid4())
            temp_payload = build_jwt_payload(
                token_type="temp",
                role=role,
                subject_id=phone,
                phone=phone,
                jti=new_jti,
                status=status,
                phone_verified=True,
                user_data=profile_data if role == "user" else None,
                vendor_data=profile_data if role == "vendor" else None,
                expires_in=86400,
            )
            temp_token = jwt.encode(temp_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
            await redis.setex(f"temp_token:{new_jti}", 86400, phone)

            return {
                "temporary_token": temp_token,
                "refresh_token": None,
                "next_action": "complete_profile" if status == "incomplete" else "await_admin_approval",
                "status": status,
                "message": get_message(
                    "auth.profile.incomplete" if status == "incomplete" else "auth.profile.pending",
                    response_language
                )
            }

        elif status == "active":
            await delete_incomplete_sessions(user_id, redis)

            session_id = str(uuid4())
            access_payload = build_jwt_payload(
                token_type="access",
                role=role,
                subject_id=user_id,
                session_id=session_id,
                status="active",
                phone_verified=True,
                scopes=[],
                user_data=profile_data if role == "user" else None,
                vendor_data=profile_data if role == "vendor" else None,
            )
            access_token = jwt.encode(access_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

            refresh_payload = build_jwt_payload(
                token_type="refresh",
                role=role,
                subject_id=user_id,
                session_id=session_id,
                status="active"
            )
            refresh_token = jwt.encode(refresh_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

            session_key = f"sessions:{user_id}:{session_id}"
            key_type = await redis.type(session_key)
            if key_type not in [b"hash", b"none"]:
                await redis.delete(session_key)

            await hset(
                session_key,
                mapping={
                    "ip": client_ip,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "device": "unknown",
                    "status": "active",
                    "jti": session_id
                },
                redis=redis
            )
            await expire(session_key, 86400, redis=redis)

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "next_action": None,
                "status": "active",
                "message": get_message("auth.login.success", response_language)
            }

        raise HTTPException(status_code=400, detail=get_message("server.error", response_language))

    except HTTPException:
        raise
    except Exception as e:
        log_error("OTP verification failed", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(status_code=500, detail=get_message("server.error", language))