# File: domain/auth/auth_services/otp_service/verify_otp_service.py

import hashlib
from os import access
from uuid import uuid4
from redis.asyncio import Redis
from jose import jwt
from fastapi import HTTPException

from common.config.settings import settings
from common.logging.logger import log_error, log_info
from common.translations.messages import get_message
from common.security.jwt.decode import decode_token
from common.security.jwt.payload_builder import build_jwt_payload
from common.security.jwt.tokens import generate_access_token
from common.exceptions.base_exception import (
    InternalServerErrorException,
    BadRequestException,
    TooManyRequestsException
)
from domain.auth.auth_services.session_service.get_sessions_service import decode_value
from domain.auth.entities.token_entity import VendorJWTProfile

from infrastructure.database.mongodb.mongo_client import find_one, insert_one, update_one
from infrastructure.database.redis.operations.redis_operations import scan_keys, get, incr, expire, setex, hset, delete
from infrastructure.database.redis.redis_client import get_redis_client

from common.utils.date_utils import utc_now
from common.utils.ip_utils import get_location_from_ip
from domain.notification.notification_services.builder import build_notification_content
from domain.notification.notification_services.dispatcher import dispatch_notification
from domain.notification.entities.notification_entity import NotificationChannel

MAX_OTP_ATTEMPTS = settings.MAX_OTP_ATTEMPTS
BLOCK_DURATION_OTP = settings.BLOCK_DURATION_OTP  # 10 minutes
IPINFO_TOKEN = settings.IPINFO_TOKEN
OTP_SALT = settings.OTP_SALT

def hash_otp(otp: str) -> str:
    salted = f"{settings.OTP_SALT}:{otp}"
    return hashlib.sha256(salted.encode()).hexdigest()

async def delete_incomplete_sessions(user_id: str, redis: Redis):
    session_keys = await scan_keys(redis, f"sessions:{user_id}:*")
    for key in session_keys:
        session_data = await redis.hgetall(key)
        status = session_data.get(b"status") or session_data.get("status", b"")
        if decode_value(status) != "active":
            await redis.delete(key)
            log_info("Deleted incomplete session", extra={"user_id": user_id, "session_key": key})

async def log_audit(action: str, details: dict):
    await insert_one("audit_logs", {
        "action": action,
        "timestamp": utc_now().isoformat(),
        "details": details
    })

async def send_otp_verified_notification(phone: str, role: str, language: str):
    try:
        notification = await build_notification_content(
            template_key="otp_verified",
            language=language,
            variables={"phone": phone, "role": role}
        )
        await dispatch_notification(
            receiver_id=phone,
            receiver_type=role,
            title=notification["title"],
            body=notification["body"],
            channel=NotificationChannel.INAPP,
            reference_type="otp",
            reference_id=phone
        )
        return True
    except Exception as notify_error:
        log_error("OTP verified but notification failed", extra={"error": str(notify_error)})
        return False

async def verify_otp_service(
        otp: str,
        temporary_token: str,
        client_ip: str,
        language: str = "fa",
        redis: Redis = None,
        request_id: str = None,
        client_version: str = None,
        device_fingerprint: str = None,
        user_agent: str = "Unknown"
) -> dict:
    redis = redis or await get_redis_client()

    try:
        payload = await decode_token(temporary_token, token_type="temp", redis=redis)
    except HTTPException as e:
        log_error("Token decode failed", extra={
            "error": e.detail,
            "ip": client_ip,
            "request_id": request_id,
            "client_version": client_version,
            "device_fingerprint": device_fingerprint
        })
        raise

    try:
        phone = payload.get("sub")
        role = payload.get("role")
        jti = payload.get("jti")

        if not phone or not role or not jti:
            raise BadRequestException(detail=get_message("token.invalid", language))

        redis_key = f"otp:{role}:{phone}"
        temp_key = f"temp_token:{jti}"
        attempt_key = f"otp-attempts:{role}:{phone}"
        block_key = f"otp-blocked:{role}:{phone}"

        if await get(block_key, redis):
            raise TooManyRequestsException(detail=get_message("otp.too_many.attempts", language))

        stored_otp_hash = await get(redis_key, redis)
        stored_phone = await get(temp_key, redis)

        if not stored_otp_hash or not stored_phone:
            raise BadRequestException(detail=get_message("otp.expired", language))

        if stored_phone != phone or hash_otp(otp) != stored_otp_hash:
            attempts = await incr(attempt_key, redis)
            await expire(attempt_key, 600, redis)
            remaining_attempts = MAX_OTP_ATTEMPTS - int(attempts)

            log_error("Invalid OTP attempt", extra={
                "submitted_otp": otp,
                "hashed_submitted": hash_otp(otp),
                "expected_hash": stored_otp_hash,
                "phone": phone,
                "ip": client_ip,
                "request_id": request_id,
                "client_version": client_version,
                "device_fingerprint": device_fingerprint,
                "attempts": attempts,
                "remaining_attempts": remaining_attempts
            })

            if int(attempts) >= MAX_OTP_ATTEMPTS:
                await delete(redis_key, redis)
                await delete(temp_key, redis)
                await setex(block_key, BLOCK_DURATION_OTP, "1", redis)
                raise TooManyRequestsException(detail=get_message("otp.too_many.attempts", language))

            raise BadRequestException(detail=get_message(
                "otp.invalid.with_attempts",
                language,
                variables={"remaining": remaining_attempts}
            ))

        await delete(redis_key, redis)
        await delete(temp_key, redis)
        await delete(attempt_key, redis)

        collection = f"{role}s"
        user = await find_one(collection, {"phone": phone})
        now = utc_now()

        if not user:
            user_data = {
                "phone": phone,
                "role": role,
                "status": "incomplete",
                "phone_verified": True,
                "preferred_languages": [language],
                "created_at": now,
                "updated_at": now
            }
            user_id = str(await insert_one(collection, user_data))
            user = {"_id": user_id, **user_data}
        else:
            user_id = str(user["_id"])
            update_fields = {"updated_at": now}
            if not user.get("phone_verified"):
                update_fields["phone_verified"] = True
            if not user.get("preferred_languages"):
                update_fields["preferred_languages"] = [language]
            if update_fields:
                await update_one(collection, {"_id": user["_id"]}, update_fields)

        status = user.get("status")
        preferred_language = (user.get("preferred_languages") or [language])[0]
        notification_sent = await send_otp_verified_notification(phone, role, preferred_language)

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
                expires_in=86400
            )
            temp_token = jwt.encode(temp_payload, settings.ACCESS_SECRET, algorithm=settings.ALGORITHM)
            await setex(f"temp_token:{new_jti}", 86400, phone, redis)

            await log_audit("otp_verified_incomplete", {
                "user_id": user_id,
                "phone": phone,
                "role": role,
                "ip": client_ip,
                "request_id": request_id,
                "client_version": client_version,
                "device_fingerprint": device_fingerprint
            })

            return {
                "status": status,
                "temporary_token": temp_token,
                "message": get_message(
                    "auth.profile.incomplete" if status == "incomplete" else "auth.profile.pending",
                    preferred_language
                ),
                "phone": phone,
                "notification_sent": notification_sent
            }

        elif status == "active":
            await delete_incomplete_sessions(user_id, redis)
            session_id = str(uuid4())
            updated_user = await find_one(collection, {"_id": user["_id"]})
            profile_data = VendorJWTProfile(**updated_user).model_dump() if role == "vendor" else None

            location = await get_location_from_ip(client_ip)

            session_data = {
                b"ip": client_ip.encode(),
                b"created_at": now.isoformat().encode(),
                b"last_seen_at": now.isoformat().encode(),
                b"device_name": b"Unknown Device",
                b"device_type": b"Desktop",
                b"os": b"Windows",
                b"browser": b"Chrome",
                b"user_agent": user_agent.encode(),
                b"location": location.encode(),
                b"status": b"active",
                b"jti": session_id.encode()
            }
            session_key = f"sessions:{user_id}:{session_id}"
            await hset(session_key, mapping=session_data, redis=redis)
            await expire(session_key, 86400, redis)

            access_token = await generate_access_token(
                user_id=user_id,
                role=role,
                session_id=session_id,
                vendor_profile=profile_data if role == "vendor" else None,
                language=preferred_language,
                scopes=[],
                status="active",
                phone_verified=True
            )

            refresh_payload = build_jwt_payload(
                token_type="refresh",
                role=role,
                subject_id=user_id,
                session_id=session_id,
                status="active",
                expires_in=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
            )
            refresh_token = jwt.encode(refresh_payload, settings.REFRESH_SECRET, algorithm=settings.ALGORITHM)

            await setex(
                f"refresh_tokens:{user_id}:{refresh_payload['jti']}",
                settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
                "active",
                redis
            )

            await log_audit("otp_verified_active", {
                "user_id": user_id,
                "phone": phone,
                "role": role,
                "session_id": session_id,
                "ip": client_ip,
                "request_id": request_id,
                "client_version": client_version,
                "device_fingerprint": device_fingerprint,
                "location": location
            })

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "status": "active",
                "message": get_message("otp.valid", preferred_language),
                "phone": phone,
                "notification_sent": notification_sent
            }

        raise InternalServerErrorException(detail=get_message("server.error", language))

    except HTTPException:
        raise

    except Exception as e:
        log_error("OTP verification failed", extra={
            "error": str(e),
            "ip": client_ip,
            "endpoint": "/verify-otp",
            "request_id": request_id,
            "client_version": client_version,
            "device_fingerprint": device_fingerprint
        }, exc_info=True)
        raise InternalServerErrorException(detail=get_message("server.error", language))