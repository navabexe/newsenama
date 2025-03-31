# File: application/auth/controllers/otp/request_otp.py
import phonenumbers
from fastapi import APIRouter, Request, HTTPException, status, Depends
from pydantic import Field, model_validator
from redis.asyncio import Redis

from common.schemas.request_base import BaseRequestModel
from common.translations.messages import get_message
from domain.auth.auth_services.otp_service.request import request_otp_service
from infrastructure.database.redis.redis_client import get_redis_client

router = APIRouter()


class RequestOTP(BaseRequestModel):
    """Request model for requesting an OTP."""

    phone: str = Field(..., description="Phone number (e.g., +989123456789)")
    role: str = Field(..., pattern=r"^(user|vendor)$", description="User or vendor")
    purpose: str = Field(..., pattern=r"^(login|signup)$", description="Login or signup")

    @model_validator(mode="after")
    def validate_phone(self) -> "RequestOTP":
        try:
            parsed = phonenumbers.parse(self.phone)
            if not phonenumbers.is_valid_number(parsed):
                raise ValueError("Invalid phone number")
            self.phone = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
            return self
        except phonenumbers.NumberParseException:
            raise ValueError("Phone number must be in international format (e.g., +989123456789)")

    model_config = {
        "str_strip_whitespace": True,
        "extra": "forbid"
    }


@router.post("/request-otp", status_code=status.HTTP_200_OK)
async def request_otp(
        data: RequestOTP,
        request: Request,
        redis: Redis = Depends(get_redis_client)
):
    """
    Request an OTP for a given phone number.

    Args:
        data (RequestOTP): OTP request data.
        request (Request): FastAPI request object.
        redis (Redis): Redis client instance.

    Returns:
        dict: Response with temporary token and OTP status.
    """
    try:
        return await request_otp_service(
            phone=data.phone,
            role=data.role,
            purpose=data.purpose,
            client_ip=request.client.host,
            language=data.response_language,
            redis=redis
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_message("server.error", data.response_language)
        )