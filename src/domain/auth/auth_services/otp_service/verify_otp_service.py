# File: domain/auth/auth_services/otp_service/verify_otp_service.py

import hashlib
import os
from uuid import uuid4
from redis.asyncio import Redis
from jose import jwt
from fastapi import HTTPException

from common.config.settings import settings
from common.logging.logger import log_error
from common.translations.messages import get_message
from common.security.jwt.decode import decode_token
from common.security.jwt.payload_builder import build_jwt_payload
from common.exceptions.base_exception import (
    InternalServerErrorException,
    BadRequestException,
    TooManyRequestsException
)

from infrastructure.database.mongodb.mongo_client import find_one, insert_one, update_one
from infrastructure.database.redis.operations.get import get
from infrastructure.database.redis.operations.setex import setex
from infrastructure.database.redis.operations.delete import delete
from infrastructure.database.redis.operations.hset import hset
from infrastructure.database.redis.operations.expire import expire
from infrastructure.database.redis.operations.incr import incr
from infrastructure.database.redis.operations.scan import scan_keys
from infrastructure.database.redis.redis_client import get_redis_client

from common.utils.date_utils import utc_now
from domain.notification.notification_services.builder import build_notification_content
from domain.notification.notification_services.dispatcher import dispatch_notification
from domain.notification.entities.notification_entity import NotificationChannel

MAX_OTP_ATTEMPTS = 5

# Salt generator
OTP_SALT = settings.OTP_SALT


def hash_otp(otp: str) -> str:
    salted = f"{OTP_SALT}:{otp}"
    return hashlib.sha256(salted.encode()).hexdigest()


async def delete_incomplete_sessions(user_id: str, redis: Redis):
    session_keys = await scan_keys(redis, f"sessions:{user_id}:*")
    for key in session_keys:
        session_data = await redis.hgetall(key)
        if session_data.get(b"status", b"").decode() != "active":
            await redis.delete(key)


async def verify_otp_service(
    otp: str,
    temporary_token: str,
    client_ip: str,
    language: str = "fa",
    redis: Redis = None,
    request_id: str = None,
    client_version: str = None,
    device_fingerprint: str = None
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

        stored_otp_hash = await get(redis_key, redis)
        stored_phone = await get(temp_key, redis)

        if not stored_otp_hash or not stored_phone:
            raise BadRequestException(detail=get_message("otp.expired", language))

        if stored_phone != phone or hash_otp(otp) != stored_otp_hash:
            attempts = await incr(attempt_key, redis)
            await expire(attempt_key, 600, redis)

            log_error("Invalid OTP attempt", extra={
                "submitted_otp": otp,
                "hashed_submitted": hash_otp(otp),
                "expected_hash": stored_otp_hash,
                "phone": phone,
                "ip": client_ip,
                "request_id": request_id,
                "client_version": client_version,
                "device_fingerprint": device_fingerprint,
                "attempts": attempts
            })

            if int(attempts) >= MAX_OTP_ATTEMPTS:
                await delete(redis_key, redis)
                await delete(temp_key, redis)
                raise TooManyRequestsException(detail=get_message("otp.too_many.attempts", language))

            raise BadRequestException(detail=get_message("otp.invalid", language))

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

        try:
            notification = await build_notification_content(
                template_key="otp_verified",
                language=preferred_language,
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
        except Exception as notify_error:
            log_error("OTP verified but notification failed", extra={"error": str(notify_error)})

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
            temp_token = jwt.encode(temp_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
            await setex(f"temp_token:{new_jti}", 86400, phone, redis)

            return {
                "status": status,
                "temporary_token": temp_token,
                "message": get_message(
                    "auth.profile.incomplete" if status == "incomplete" else "auth.profile.pending",
                    preferred_language
                ),
                "phone": phone
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
                expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            )
            access_token = jwt.encode(access_payload, settings.ACCESS_SECRET, algorithm=settings.ALGORITHM)

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

            session_key = f"sessions:{user_id}:{session_id}"
            await hset(session_key, mapping={
                "ip": client_ip,
                "created_at": now.isoformat(),
                "device": device_fingerprint or "unknown",
                "status": "active",
                "jti": session_id
            }, redis=redis)
            await expire(session_key, 86400, redis)

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "status": "active",
                "message": get_message("otp.valid", preferred_language),
                "phone": phone
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
