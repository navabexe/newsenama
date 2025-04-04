import os
from datetime import datetime, timezone
from uuid import uuid4
from redis.asyncio import Redis

from jose import jwt

from common.logging.logger import log_info, log_error
from common.translations.messages import get_message
from common.security.jwt.payload_builder import build_jwt_payload
from common.config.settings import settings
from common.utils.string_utils import generate_otp_code
from common.exceptions.base_exception import TooManyRequestsException, InternalServerErrorException

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
    Includes rate limiting and temporary token issuance.
    """
    try:
        if redis is None:
            redis = await get_redis_client()

        redis_key = f"otp:{role}:{phone}"
        rate_limit_1min = f"otp-limit:{role}:{phone}"
        rate_limit_10min = f"otp-limit-10min:{role}:{phone}"
        rate_limit_1h = f"otp-limit-1h:{role}:{phone}"
        block_key = f"otp-blocked:{role}:{phone}"

        # Check block status
        if await get(block_key, redis):
            raise TooManyRequestsException(detail=get_message("otp.too_many.blocked", language))

        # Enforce rate limits
        if (attempts := await get(rate_limit_1min, redis)) and int(attempts) >= 3:
            raise TooManyRequestsException(detail=get_message("otp.too_many.1min", language))
        if (attempts := await get(rate_limit_10min, redis)) and int(attempts) >= 5:
            raise TooManyRequestsException(detail=get_message("otp.too_many.10min", language))
        if (attempts := await get(rate_limit_1h, redis)) and int(attempts) >= 10:
            await setex(block_key, 3600, "1", redis)
            raise TooManyRequestsException(detail=get_message("otp.too_many.blocked", language))

        # Generate OTP and payload
        otp_code = generate_otp_code()
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
            expires_in=300
        )

        temp_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

        # Store OTP and token reference in Redis
        await setex(redis_key, 300, otp_code, redis)
        await setex(f"temp_token:{jti}", 300, phone, redis)

        # Increment rate limit counters
        for key, ttl in [(rate_limit_1min, 60), (rate_limit_10min, 600), (rate_limit_1h, 3600)]:
            await incr(key, redis)
            await expire(key, ttl, redis)

        # Structured logging
        log_data = {
            "phone": phone,
            "role": role,
            "purpose": purpose,
            "jti": jti,
            "ip": client_ip,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "endpoint": "request_otp_service"
        }
        if ENVIRONMENT == "development":
            log_data["otp"] = otp_code

        log_info("OTP requested", extra=log_data)

        return {
            "temporary_token": temp_token,
            "message": get_message("otp.sent", language),
            "expires_in": 300
        }

    except TooManyRequestsException:
        raise

    except Exception as e:
        log_error("OTP request failed", extra={
            "error": str(e),
            "phone": phone,
            "role": role,
            "ip": client_ip,
            "endpoint": "request_otp_service"
        }, exc_info=True)
        raise InternalServerErrorException(detail=get_message("server.error", language))