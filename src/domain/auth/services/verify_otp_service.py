# File: src/domain/auth/services/otp/verify_otp_service.py

import hashlib
from datetime import datetime
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis

from common.base_service.base_service import BaseService
from common.config.settings import settings
from common.exceptions.base_exception import BadRequestException, TooManyRequestsException
from common.security.jwt_handler import decode_token, generate_temp_token
from common.translations.messages import get_message
from common.utils.date_utils import utc_now
from common.utils.log_utils import create_log_data
from domain.auth.services.session_creator import create_user_session
from domain.auth.services.session_service import get_session_service
from domain.notification.services.notification_service import notification_service
from infrastructure.database.mongodb.connection import get_mongo_db
from infrastructure.database.mongodb.repositories.auth_repository import AuthRepository
from infrastructure.database.redis.repositories.otp_repository import OTPRepository


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

class OTPVerifyService(BaseService):
    async def verify_otp_service(
        self,
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

        context = {
            "entity_type": "otp",
            "entity_id": "unknown",
            "action": "verified",
            "endpoint": settings.VERIFY_OTP_PATH,
            "request_id": request_id
        }

        async def operation():
            payload = await decode_token(temporary_token, token_type="temp", redis=redis)
            phone = payload.get("sub")
            role = payload.get("role")
            jti = payload.get("jti")
            context["entity_id"] = phone

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
                remaining = settings.MAX_OTP_ATTEMPTS - int(attempts)
                if int(attempts) >= settings.MAX_OTP_ATTEMPTS:
                    await repo.delete(redis_key)
                    await repo.delete(temp_key)
                    await repo.setex(block_key, settings.BLOCK_DURATION_OTP, "1")
                    await notification_service.send(
                        receiver_id="admin",
                        receiver_type="admin",
                        template_key="notification_failed",
                        variables={"receiver_id": phone, "error": "Too many OTP attempts", "type": "security"},
                        reference_type="otp",
                        reference_id=phone,
                        language=language
                    )
                    raise TooManyRequestsException(detail=get_message("otp.too_many.attempts", language))
                raise BadRequestException(detail=get_message("otp.invalid.with_attempts", language, variables={"remaining": remaining}))

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

            log_data = create_log_data(
                entity_type="otp", entity_id=phone, action="verified", ip=client_ip,
                request_id=request_id, client_version=client_version, device_fingerprint=device_fingerprint,
                extra_data={"role": role, "status": status, "user_id": user_id}
            )
            await auth_repo.log_audit("otp_verified", log_data)

            if status in ["incomplete", "pending"]:
                new_jti = str(uuid4())
                temp_token = await generate_temp_token(phone=phone, role=role, jti=new_jti, status=status, phone_verified=True, language=preferred_language)
                await repo.setex(f"temp_token:{new_jti}", settings.TEMP_TOKEN_EXPIRY, phone)
                return {
                    "status": status,
                    "temporary_token": temp_token,
                    "message": get_message("auth.profile.incomplete" if status == "incomplete" else "auth.profile.pending", preferred_language),
                    "phone": phone,
                    "notification_sent": notification_sent
                }

            elif status == "active":
                await session_service.delete_incomplete_sessions(user_id)
                updated_user = await auth_repo.find_user(collection, phone)

                session_result = await create_user_session(
                    user_id=user_id,
                    phone=phone,
                    role=role,
                    user=updated_user,
                    redis=repo.redis,
                    client_ip=client_ip,
                    user_agent=user_agent,
                    language=preferred_language,
                    now=now
                )
                session_result["notification_sent"] = notification_sent
                session_result["message"] = get_message("otp.valid", preferred_language)
                return session_result

            raise BadRequestException(detail=get_message("server.error", language))

        return await self.execute(operation, context, language)

otp_verify_service = OTPVerifyService()
