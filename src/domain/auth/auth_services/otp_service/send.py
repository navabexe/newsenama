# File: domain/auth/auth_services/otp_service/send.py

from fastapi import HTTPException, status
from infrastructure.database.redis.redis_client import setex, get, incr, expire
from common.utils.token_utils import generate_otp_code
from common.logging.logger import log_info, log_error
from datetime import datetime, timezone

async def send_otp_service(phone: str, client_ip: str) -> dict:
    """Handle sending OTP to a phone number."""
    redis_key = f"otp:send:{phone}"
    rate_limit_key = f"otp-send-limit:{phone}"

    try:
        # Check rate limit (max 3 attempts per minute)
        attempts = get(rate_limit_key)
        if attempts and int(attempts) >= 3:
            log_error("Rate limit exceeded for OTP send", extra={"phone": phone, "ip": client_ip})
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many OTP requests")

        # Generate OTP
        otp_code = generate_otp_code()

        # Store OTP in Redis
        setex(redis_key, 300, otp_code)
        incr(rate_limit_key)
        expire(rate_limit_key, 60)

        # Log success
        log_info("OTP sent", extra={
            "phone": phone,
            "otp": otp_code,
            "ip": client_ip,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return {"message": "OTP sent to your phone", "expires_in": 300}

    except HTTPException as e:
        raise e
    except Exception as e:
        log_error("OTP send failed", extra={"phone": phone, "error": str(e), "ip": client_ip})
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send OTP")