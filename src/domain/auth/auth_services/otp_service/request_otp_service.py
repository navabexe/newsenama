# File: src/domain/auth/services/otp/request_otp_service.py
import hashlib
from datetime import datetime, timezone
from uuid import uuid4
from redis.asyncio import Redis
from fastapi import Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from common.logging.logger import log_info, log_error
from common.translations.messages import get_message
from common.security.jwt_handler import generate_temp_token
from common.config.settings import settings
from common.utils.ip_utils import extract_client_ip
from common.utils.string_utils import generate_otp_code
from common.exceptions.base_exception import TooManyRequestsException, InternalServerErrorException
from infrastructure.database.redis.repositories.otp_repository import OTPRepository
from infrastructure.database.mongodb.repositories.auth_repository import AuthRepository
from domain.auth.services.rate_limiter import check_rate_limits, store_rate_limit_keys
from domain.notification.notification_services.notification_service import notification_service
from infrastructure.database.mongodb.connection import get_mongo_db

def hash_otp(otp: str) -> str:
    salted = f"{settings.OTP_SALT}:{otp}"
    return hashlib.sha256(salted.encode()).hexdigest()

def create_log_data(phone: str, role: str, purpose: str, jti: str, client_ip: str, request_id: str, client_version: str, device_fingerprint: str, otp: str = None) -> dict:
    log_data = {
        "phone": phone,
        "role": role,
        "purpose": purpose,
        "jti": jti,
        "ip": client_ip,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "endpoint": settings.REQUEST_OTP_PATH,
        "request_id": request_id,
        "client_version": client_version,
        "device_fingerprint": device_fingerprint
    }
    if settings.ENVIRONMENT == "development" and otp:  # استفاده مستقیم از settings
        log_data["otp"] = otp
    return log_data

async def request_otp_service(
    phone: str,
    role: str,
    purpose: str,
    request: Request,
    language: str = "fa",
    redis: Redis = None,
    db: AsyncIOMotorDatabase = None,
    request_id: str = None,
    client_version: str = None,
    device_fingerprint: str = None
) -> dict:
    repo = OTPRepository(redis)
    if db is None:
        db = await get_mongo_db()
    auth_repo = AuthRepository(db)

    try:
        client_ip = await extract_client_ip(request)
        redis_key = f"otp:{role}:{phone}"
        block_key = f"otp-blocked:{role}:{phone}"

        if await repo.get(block_key):
            raise TooManyRequestsException(detail=get_message("otp.too_many.blocked", lang=language))

        await check_rate_limits(phone, role, repo, language)

        otp_code = generate_otp_code()
        otp_hash = hash_otp(otp_code)
        jti = str(uuid4())

        temp_token = await generate_temp_token(
            phone=phone,
            role=role,
            jti=jti,
            status="incomplete",
            phone_verified=False,
            language=language
        )

        await repo.setex(redis_key, settings.OTP_EXPIRY, otp_hash)
        await repo.setex(f"temp_token:{jti}", settings.OTP_EXPIRY, phone)
        await store_rate_limit_keys(phone, role, repo)

        log_data = create_log_data(phone, role, purpose, jti, client_ip, request_id, client_version, device_fingerprint, otp_code)
        await auth_repo.log_audit("otp_requested", log_data)
        log_info("OTP requested", extra=log_data)

        notification_sent = await notification_service.send(
            receiver_id=phone,
            receiver_type=role,
            template_key="otp_requested",
            variables={"phone": phone, "otp": otp_code, "purpose": purpose},
            reference_type="otp",
            reference_id=phone,
            language=language,
            return_bool=True
        )

        return {
            "temporary_token": temp_token,
            "message": get_message("otp.sent", lang=language),
            "expires_in": settings.OTP_EXPIRY,
            "notification_sent": notification_sent
        }

    except TooManyRequestsException:
        raise
    except Exception as e:
        log_error("OTP request failed", extra={
            "error": str(e),
            "phone": phone,
            "role": role,
            "ip": await extract_client_ip(request),
            "endpoint": settings.REQUEST_OTP_PATH,
            "request_id": request_id,
            "client_version": client_version,
            "device_fingerprint": device_fingerprint
        }, exc_info=True)
        raise InternalServerErrorException(detail=get_message("server.error", lang=language))