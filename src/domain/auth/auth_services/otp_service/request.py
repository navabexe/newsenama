from fastapi import HTTPException, status
from common.security.jwt_handler import generate_temp_token
from infrastructure.database.redis.redis_client import get, setex, incr, expire
from common.utils.token_utils import generate_otp_code
from common.logging.logger import log_info, log_error
from datetime import datetime, timezone
from uuid import uuid4
import os

# Check environment (default to 'development')
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")


async def request_otp_service(phone: str, role: str, purpose: str, client_ip: str) -> dict:
    redis_key = f"otp:{role}:{phone}"
    rate_limit_key = f"otp-limit:{role}:{phone}"

    try:
        # Check rate limit (max 3 attempts per minute)
        attempts = get(rate_limit_key)
        if attempts and int(attempts) >= 3:
            log_error("Rate limit exceeded", extra={"phone": phone, "role": role, "ip": client_ip})
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many OTP requests")

        # Generate OTP and token
        otp_code = generate_otp_code()
        jti = str(uuid4())
        temp_token = generate_temp_token(phone=phone, role=role, jti=jti)

        # Store in Redis
        otp_ttl = 300  # 5 minutes
        setex(redis_key, otp_ttl, otp_code)
        setex(f"temp_token:{jti}", otp_ttl, phone)
        incr(rate_limit_key)
        expire(rate_limit_key, 60)  # 1 minute rate limit window

        # Log success with OTP only in development
        log_data = {
            "phone": phone,
            "role": role,
            "purpose": purpose,
            "jti": jti,
            "ip": client_ip,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        if ENVIRONMENT == "development":
            log_data["otp"] = otp_code  # فقط توی development لاگ می‌شه

        log_info("OTP requested", extra=log_data)

        return {
            "temporary_token": temp_token,
            "message": "OTP sent to your phone",
            "expires_in": otp_ttl
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        log_error("OTP request failed", extra={"phone": phone, "error": str(e), "ip": client_ip})
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to process OTP request")