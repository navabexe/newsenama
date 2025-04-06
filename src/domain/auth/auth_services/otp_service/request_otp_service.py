# File: domain/auth/auth_services/otp_service/request_otp_service.py

import os
import hashlib
from datetime import datetime, timezone
from uuid import uuid4
from redis.asyncio import Redis
from jose import jwt
from fastapi import Request

from common.logging.logger import log_info, log_error
from common.translations.messages import get_message
from common.security.jwt.payload_builder import build_jwt_payload
from common.config.settings import settings
from common.utils.ip_utils import extract_client_ip
from common.utils.string_utils import generate_otp_code
from common.exceptions.base_exception import TooManyRequestsException, InternalServerErrorException
from infrastructure.database.mongodb.mongo_client import insert_one

from infrastructure.database.redis.operations.get import get
from infrastructure.database.redis.operations.setex import setex
from infrastructure.database.redis.operations.incr import incr
from infrastructure.database.redis.operations.expire import expire
from infrastructure.database.redis.redis_client import get_redis_client

from domain.notification.notification_services.builder import build_notification_content
from domain.notification.notification_services.dispatcher import dispatch_notification
from domain.notification.entities.notification_entity import NotificationChannel

OTP_EXPIRY = settings.OTP_EXPIRY
BLOCK_DURATION = settings.BLOCK_DURATION
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
OTP_SALT = settings.OTP_SALT

def hash_otp(otp: str) -> str:
    salted = f"{OTP_SALT}:{otp}"
    return hashlib.sha256(salted.encode()).hexdigest()

async def check_rate_limits(phone: str, role: str, redis: Redis, language: str):
    keys_limits = {
        f"otp-limit:{role}:{phone}": (3, 60, "otp.too_many.1min"),
        f"otp-limit-10min:{role}:{phone}": (5, 600, "otp.too_many.10min"),
        f"otp-limit-1h:{role}:{phone}": (10, 3600, "otp.too_many.blocked"),
    }
    for key, (limit, ttl, msg_key) in keys_limits.items():
        attempts = await get(key, redis)
        if attempts and int(attempts) >= limit:
            if "1h" in key:
                await setex(f"otp-blocked:{role}:{phone}", BLOCK_DURATION, "1", redis)
            raise TooManyRequestsException(detail=get_message(msg_key, lang=language))

async def store_rate_limit_keys(phone: str, role: str, redis: Redis):
    for key, ttl in [
        (f"otp-limit:{role}:{phone}", 60),
        (f"otp-limit-10min:{role}:{phone}", 600),
        (f"otp-limit-1h:{role}:{phone}", 3600),
    ]:
        await incr(key, redis)
        await expire(key, ttl, redis)

async def send_otp_notification(phone: str, role: str, otp_code: str, purpose: str, language: str):
    try:
        content = await build_notification_content(
            template_key="otp_requested",
            language=language,
            variables={"phone": phone, "otp": otp_code, "purpose": purpose}
        )
        await dispatch_notification(
            receiver_id=phone,
            receiver_type=role,
            title=content["title"],
            body=content["body"],
            channel=NotificationChannel.INAPP,
            reference_type="otp",
            reference_id=phone
        )
        return True
    except Exception as notify_error:
        log_error("Notification dispatch failed", extra={"error": str(notify_error)})
        return False

async def log_audit(action: str, details: dict):
    await insert_one("audit_logs", {
        "action": action,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": details
    })

async def request_otp_service(
    phone: str,
    role: str,
    purpose: str,
    request: Request,
    language: str = "fa",
    redis: Redis = None,
    request_id: str = None,
    client_version: str = None,
    device_fingerprint: str = None
) -> dict:
    try:
        redis = redis or await get_redis_client()
        client_ip = await extract_client_ip(request)  # await شده

        redis_key = f"otp:{role}:{phone}"
        block_key = f"otp-blocked:{role}:{phone}"

        if await get(block_key, redis):
            raise TooManyRequestsException(detail=get_message("otp.too_many.blocked", lang=language))

        await check_rate_limits(phone, role, redis, language)

        otp_code = generate_otp_code()
        otp_hash = hash_otp(otp_code)
        jti = str(uuid4())

        payload = build_jwt_payload(
            token_type="temp",
            role=role,
            subject_id=phone,
            phone=phone,
            language=language,
            status="incomplete",
            phone_verified=False,
            jti=jti,
            expires_in=OTP_EXPIRY
        )
        temp_token = jwt.encode(payload, settings.ACCESS_SECRET, algorithm=settings.ALGORITHM)

        await setex(redis_key, OTP_EXPIRY, otp_hash, redis)
        await setex(f"temp_token:{jti}", OTP_EXPIRY, phone, redis)
        await store_rate_limit_keys(phone, role, redis)

        log_data = {
            "phone": phone,
            "role": role,
            "purpose": purpose,
            "jti": jti,
            "ip": client_ip,  # حالا یه str هست
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "endpoint": "request_otp_service",
            "request_id": request_id,
            "client_version": client_version,
            "device_fingerprint": device_fingerprint
        }
        if ENVIRONMENT == "development":
            log_data["otp"] = otp_code

        await log_audit("otp_requested", log_data)
        log_info("OTP requested", extra=log_data)
        notification_sent = await send_otp_notification(phone, role, otp_code, purpose, language)

        return {
            "temporary_token": temp_token,
            "message": get_message("otp.sent", lang=language),
            "expires_in": OTP_EXPIRY,
            "notification_sent": notification_sent
        }

    except TooManyRequestsException:
        raise
    except Exception as e:
        log_error("OTP request failed", extra={
            "error": str(e),
            "phone": phone,
            "role": role,
            "ip": await extract_client_ip(request),  # await اضافه شده
            "endpoint": "request_otp_service",
            "request_id": request_id,
            "client_version": client_version,
            "device_fingerprint": device_fingerprint
        }, exc_info=True)
        raise InternalServerErrorException(detail=get_message("server.error", lang=language))