# File: domain/auth/auth_services/otp_service/request.py

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
    rate_limit_1min = f"otp-limit:{role}:{phone}"        # 3 per 1min
    rate_limit_10min = f"otp-limit-10min:{role}:{phone}" # 5 per 10min
    rate_limit_1h = f"otp-limit-1h:{role}:{phone}"        # 10 per hour
    block_key = f"otp-blocked:{role}:{phone}"

    try:
        # Blocked check
        if get(block_key):
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many OTP requests. Try again later.")

        # === Rate Limit Checks ===
        if (attempts := get(rate_limit_1min)) and int(attempts) >= 3:
            raise HTTPException(status_code=429, detail="Too many OTP requests (1-minute limit)")
        if (attempts := get(rate_limit_10min)) and int(attempts) >= 5:
            raise HTTPException(status_code=429, detail="Too many OTP requests (10-minute limit)")
        if (attempts := get(rate_limit_1h)) and int(attempts) >= 10:
            setex(block_key, 3600, "1")  # Block for 1 hour
            raise HTTPException(status_code=429, detail="Too many OTP requests. Temporarily blocked")

        # === Generate OTP and token ===
        otp_code = generate_otp_code()
        jti = str(uuid4())
        temp_token = await generate_temp_token(phone=phone, role=role, jti=jti)

        # === Save OTP and Token ===
        otp_ttl = 300  # 5 minutes
        setex(redis_key, otp_ttl, otp_code)
        setex(f"temp_token:{jti}", otp_ttl, phone)

        # === Increment Rate Limit Counters ===
        for key, ttl in [
            (rate_limit_1min, 60),
            (rate_limit_10min, 600),
            (rate_limit_1h, 3600)
        ]:
            incr(key)
            expire(key, ttl)

        # === Logging ===
        log_data = {
            "phone": phone,
            "role": role,
            "purpose": purpose,
            "jti": jti,
            "ip": client_ip,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        if ENVIRONMENT == "development":
            log_data["otp"] = otp_code  # Show OTP only in dev

        log_info("OTP requested", extra=log_data)

        return {
            "temporary_token": temp_token,
            "message": "OTP sent to your phone",
            "expires_in": otp_ttl
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        log_error("OTP request failed", extra={"phone": phone, "error": str(e), "ip": client_ip}, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process OTP request")