# File: domain/auth/auth_services/otp_service/request.py
import os
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException, status
from redis.asyncio import Redis

from common.logging.logger import log_info, log_error
from common.translations.messages import get_message
from common.utils.token_utils import generate_otp_code
from common.security.jwt.payload_builder import build_jwt_payload
from common.config.settings import settings
from infrastructure.database.redis.operations.expire import expire
from infrastructure.database.redis.operations.get import get
from infrastructure.database.redis.operations.incr import incr
from infrastructure.database.redis.operations.setex import setex
from infrastructure.database.redis.redis_client import get_redis_client

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

async def request_otp_service(
    phone: str,
    role: str,
    purpose: str,
    client_ip: str,
    language: str = "fa",
    redis: Redis = None
) -> dict:
    """
    Request an OTP for a given phone number and role.

    Args:
        phone (str): Phone number in E164 format (e.g., +989123456789).
        role (str): Role of the user ('user' or 'vendor').
        purpose (str): Purpose of the OTP ('login' or 'signup').
        client_ip (str): IP address of the client.
        language (str): Language for response messages (e.g., 'fa', 'en').
        redis (Redis): Redis client instance.

    Returns:
        dict: Response containing temporary token, message, and expiration time.

    Raises:
        HTTPException: On rate limit exceed or internal errors.
    """
    try:
        if redis is None:
            redis = await get_redis_client()

        redis_key = f"otp:{role}:{phone}"
        rate_limit_1min = f"otp-limit:{role}:{phone}"
        rate_limit_10min = f"otp-limit-10min:{role}:{phone}"
        rate_limit_1h = f"otp-limit-1h:{role}:{phone}"
        block_key = f"otp-blocked:{role}:{phone}"

        if await get(block_key, redis):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=get_message("otp.too_many.blocked", language)
            )

        if (attempts := await get(rate_limit_1min, redis)) and int(attempts) >= 3:
            raise HTTPException(status_code=429, detail=get_message("otp.too_many.1min", language))
        if (attempts := await get(rate_limit_10min, redis)) and int(attempts) >= 5:
            raise HTTPException(status_code=429, detail=get_message("otp.too_many.10min", language))
        if (attempts := await get(rate_limit_1h, redis)) and int(attempts) >= 10:
            await setex(block_key, 3600, "1", redis)
            raise HTTPException(status_code=429, detail=get_message("otp.too_many.blocked", language))

        otp_code = generate_otp_code()
        jti = str(uuid4())

        # Generate temp token using payload builder
        payload = build_jwt_payload(
            token_type="temp",
            role=role,
            subject_id=phone,
            phone=phone,
            language=language,
            status="incomplete",
            phone_verified=False,
            jti=jti,
            expires_in=300  # 5 minutes
        )
        from jose import jwt
        temp_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

        await setex(redis_key, 300, otp_code, redis)
        await setex(f"temp_token:{jti}", 300, phone, redis)

        for key, ttl in [(rate_limit_1min, 60), (rate_limit_10min, 600), (rate_limit_1h, 3600)]:
            await incr(key, redis)
            await expire(key, ttl, redis)

        log_data = {
            "phone": phone,
            "role": role,
            "purpose": purpose,
            "jti": jti,
            "ip": client_ip,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        if ENVIRONMENT == "development":
            log_data["otp"] = otp_code

        log_info("OTP requested", extra=log_data)

        return {
            "temporary_token": temp_token,
            "message": get_message("otp.sent", language),
            "expires_in": 300
        }

    except HTTPException:
        raise
    except Exception as e:
        log_error("OTP request failed", extra={"phone": phone, "error": str(e), "ip": client_ip}, exc_info=True)
        raise HTTPException(status_code=500, detail=get_message("server.error", language))