# File: src/domain/auth/services/otp/request_otp_service.py

import hashlib
from uuid import uuid4

from fastapi import Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis

from common.base_service.base_service import BaseService
from common.config.settings import settings
from common.exceptions.base_exception import TooManyRequestsException
from common.security.jwt_handler import generate_temp_token
from common.translations.messages import get_message
from common.utils.agent_utils import parse_user_agent
from common.utils.ip_utils import extract_client_ip
from common.utils.log_utils import create_log_data
from common.utils.string_utils import generate_otp_code
from domain.auth.services.rate_limiter import check_rate_limits, store_rate_limit_keys
from domain.notification.services.notification_service import notification_service
from infrastructure.database.mongodb.connection import get_mongo_db
from infrastructure.database.mongodb.repositories.auth_repository import AuthRepository
from infrastructure.database.redis.repositories.otp_repository import OTPRepository


def hash_otp(otp: str) -> str:
    salted = f"{settings.OTP_SALT}:{otp}"
    return hashlib.sha256(salted.encode()).hexdigest()

class OTPRequestService(BaseService):
    async def request_otp_service(
        self,
        phone: str,
        role: str,
        purpose: str,
        request: Request,
        language: str = "fa",
        redis: Redis = None,
        db: AsyncIOMotorDatabase = None,
        request_id: str = None,
        client_version: str = None,
        device_fingerprint: str = None,
        user_agent: str = "Unknown"  # ✅ NEW
    ) -> dict:
        repo = OTPRepository(redis)
        if db is None:
            db = await get_mongo_db()
        auth_repo = AuthRepository(db)

        context = {
            "entity_type": "otp",
            "entity_id": phone,
            "action": "requested",
            "endpoint": settings.REQUEST_OTP_PATH,
            "request_id": request_id
        }

        async def operation():
            client_ip = await extract_client_ip(request)
            redis_key = f"otp:{role}:{phone}"
            block_key = f"otp-blocked:{role}:{phone}"
            temp_token_key = f"temp_token_used:{phone}"

            # Check if user is blocked
            if await repo.get(block_key):
                raise TooManyRequestsException(detail=get_message("otp.too_many.blocked", lang=language))

            # Rate limit check
            await check_rate_limits(phone, role, repo, language)

            # Generate OTP and temp token
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

            # Store OTP and token in Redis
            await repo.setex(redis_key, settings.OTP_EXPIRY, otp_hash)
            await repo.setex(f"temp_token:{jti}", settings.OTP_EXPIRY, phone)
            await repo.setex(temp_token_key, settings.OTP_EXPIRY, "generated")
            await store_rate_limit_keys(phone, role, repo)

            # Parse user-agent for device info
            agent_info = parse_user_agent(user_agent)

            # Audit log
            log_data = create_log_data(
                entity_type="otp",
                entity_id=phone,
                action="requested",
                ip=client_ip,
                request_id=request_id,
                client_version=client_version,
                device_fingerprint=device_fingerprint,
                extra_data={
                    "role": role,
                    "purpose": purpose,
                    "jti": jti,
                    "otp": otp_code if settings.ENVIRONMENT == "development" else None,
                    "device_name": agent_info["device_name"],
                    "device_type": agent_info["device_type"],
                    "os": agent_info["os"],
                    "browser": agent_info["browser"]
                }
            )
            await auth_repo.log_audit("otp_requested", log_data)

            # Send notification
            notification_sent = await notification_service.send(
                receiver_id=phone,
                receiver_type=role,
                template_key="otp_requested",
                variables={"phone": phone, "otp": otp_code, "purpose": purpose},
                reference_type="otp",
                reference_id=phone,
                language=language,
                return_bool=True,
                additional_receivers=[{"id": "admin", "type": "admin"}]
            )

            return {
                "temporary_token": temp_token,
                "message": get_message("otp.sent", lang=language),
                "expires_in": settings.OTP_EXPIRY,
                "notification_sent": notification_sent
            }

        return await self.execute(operation, context, language)

otp_request_service = OTPRequestService()
