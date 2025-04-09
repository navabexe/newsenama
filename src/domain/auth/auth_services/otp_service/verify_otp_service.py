# File: src/domain/auth/services/otp/verify_otp_service.py
import hashlib
from datetime import datetime
from uuid import uuid4
from redis.asyncio import Redis
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from common.config.settings import settings
from common.logging.logger import log_error, log_info
from common.security.jwt_handler import decode_token, generate_access_token, generate_temp_token, generate_refresh_token
from common.translations.messages import get_message
from common.exceptions.base_exception import InternalServerErrorException, BadRequestException, TooManyRequestsException
from common.utils.date_utils import utc_now
from common.utils.ip_utils import get_location_from_ip
from domain.auth.entities.token_entity import VendorJWTProfile
from domain.auth.services.session_service import get_session_service
from domain.notification.notification_services.notification_service import notification_service
from infrastructure.database.redis.repositories.otp_repository import OTPRepository
from infrastructure.database.mongodb.repositories.auth_repository import AuthRepository
from infrastructure.database.mongodb.connection import get_mongo_db

def hash_otp(otp: str) -> str:
    salted = f"{settings.OTP_SALT}:{otp}"
    return hashlib.sha256(salted.encode()).hexdigest()

def create_user_data(phone: str, role: str, language: str, now: datetime) -> dict:
    return {
        "phone": phone,
        "role": role,
        "status": "incomplete",
        "phone_verified": True,
        "preferred_languages": [language],
        "created_at": now,
        "updated_at": now
    }

async def verify_otp_service(
    otp: str,
    temporary_token: str,
    client_ip: str,
    language: str = "fa",
    redis: Redis = None,
    db: AsyncIOMotorDatabase = None,
    request_id: str = None,
    client_version: str = None,
    device_fingerprint: str = None,
    user_agent: str = "Unknown"
) -> dict:
    repo = OTPRepository(redis)
    if db is None:
        db = await get_mongo_db()
    auth_repo = AuthRepository(db)
    session_service = get_session_service(redis)

    try:
        payload = await decode_token(temporary_token, token_type="temp", redis=redis)
    except HTTPException as e:
        log_error("Token decode failed", extra={"error": e.detail, "ip": client_ip, "request_id": request_id})
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

        if await repo.get(block_key):
            raise TooManyRequestsException(detail=get_message("otp.too_many.attempts", language))

        stored_otp_hash = await repo.get(redis_key)
        stored_phone = await repo.get(temp_key)

        if not stored_otp_hash or not stored_phone:
            raise BadRequestException(detail=get_message("otp.expired", language))

        if stored_phone != phone or hash_otp(otp) != stored_otp_hash:
            attempts = await repo.incr(attempt_key)
            await repo.expire(attempt_key, 600)
            remaining_attempts = settings.MAX_OTP_ATTEMPTS - int(attempts)

            log_error("Invalid OTP attempt", extra={
                "submitted_otp": otp,
                "phone": phone,
                "ip": client_ip,
                "attempts": attempts,
                "remaining_attempts": remaining_attempts
            })

            if int(attempts) >= settings.MAX_OTP_ATTEMPTS:
                await repo.delete(redis_key)
                await repo.delete(temp_key)
                await repo.setex(block_key, settings.BLOCK_DURATION_OTP, "1")
                raise TooManyRequestsException(detail=get_message("otp.too_many.attempts", language))

            raise BadRequestException(detail=get_message(
                "otp.invalid.with_attempts",
                language,
                variables={"remaining": remaining_attempts}
            ))

        await repo.delete(redis_key)
        await repo.delete(temp_key)
        await repo.delete(attempt_key)

        collection = f"{role}s"
        user = await auth_repo.find_user(collection, phone)
        now = utc_now()

        if not user:
            user_data = create_user_data(phone, role, language, now)
            user_id = await auth_repo.insert_user(collection, user_data)
            user = {"_id": user_id, **user_data}
        else:
            user_id = str(user["_id"])
            update_fields = {"updated_at": now}
            if not user.get("phone_verified"):
                update_fields["phone_verified"] = True
            if not user.get("preferred_languages"):
                update_fields["preferred_languages"] = [language]
            if update_fields:
                await auth_repo.update_user(collection, user_id, update_fields)

        status = user.get("status")
        preferred_language = (user.get("preferred_languages") or [language])[0]
        notification_sent = await notification_service.send_otp_verified(phone, role, preferred_language)

        if status in ["incomplete", "pending"]:
            new_jti = str(uuid4())
            temp_token = await generate_temp_token(
                phone=phone,
                role=role,
                jti=new_jti,
                status=status,
                phone_verified=True,
                language=preferred_language
            )
            await repo.setex(f"temp_token:{new_jti}", settings.TEMP_TOKEN_EXPIRY, phone)

            await auth_repo.log_audit("otp_verified_incomplete", {
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
            await session_service.delete_incomplete_sessions(user_id)
            session_id = str(uuid4())
            updated_user = await auth_repo.find_user(collection, phone)
            if updated_user is None:
                log_error("User not found after OTP verification", extra={"phone": phone, "user_id": user_id})
                raise InternalServerErrorException(detail=get_message("server.error", language))
            profile_data = VendorJWTProfile(**updated_user).model_dump() if role == "vendor" else None

            location = await get_location_from_ip(client_ip)
            if location == "Unknown":
                log_info("Location fetch failed, using default", extra={"ip": client_ip})
            session_data = {  # تبدیل به bytes
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
            await repo.hset(session_key, session_data)
            await repo.expire(session_key, settings.SESSION_EXPIRY)

            access_token = await generate_access_token(
                user_id=user_id,
                role=role,
                session_id=session_id,
                vendor_profile=profile_data if role == "vendor" else None,
                language=preferred_language,
                status="active",
                phone_verified=True
            )

            refresh_token, refresh_jti = await generate_refresh_token(
                user_id=user_id,
                role=role,
                session_id=session_id,
                status="active",
                language=preferred_language,
                return_jti=True
            )

            await repo.setex(
                f"refresh_tokens:{user_id}:{refresh_jti}",
                settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
                "active"
            )

            await auth_repo.log_audit("otp_verified_active", {
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
            "endpoint": settings.VERIFY_OTP_PATH,
            "request_id": request_id
        }, exc_info=True)
        raise InternalServerErrorException(detail=get_message("server.error", language))