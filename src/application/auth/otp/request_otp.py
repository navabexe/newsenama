# File: application/auth/controllers/otp/request_otp.py

import phonenumbers
from fastapi import APIRouter, Request, HTTPException, status, Depends
from pydantic import Field, model_validator, ConfigDict
from redis.asyncio import Redis
from typing import Annotated

from common.schemas.request_base import BaseRequestModel
from common.translations.messages import get_message
from domain.auth.auth_services.otp_service.request import request_otp_service
from infrastructure.database.redis.redis_client import get_redis_client
from common.logging.logger import log_info, log_error

router = APIRouter()


class RequestOTP(BaseRequestModel):
    """Request model for requesting an OTP."""

    phone: Annotated[str, Field(description="Phone number (e.g., +989123456789)", examples=["+989123456789"])]
    role: Annotated[str, Field(pattern=r"^(user|vendor)$", description="User or vendor", examples=["user", "vendor"])]
    purpose: Annotated[str, Field(pattern=r"^(login|signup)$", description="Login or signup", examples=["login", "signup"])]

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid"
    )

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


@router.post(
    "/request-otp",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "OTP sent successfully."},
        400: {"description": "Invalid input."},
        500: {"description": "Internal server error."}
    }
)
async def request_otp(
    data: RequestOTP,
    request: Request,
    redis: Annotated[Redis, Depends(get_redis_client)]
):
    """
    Request an OTP for a given phone number.
    """
    try:
        result = await request_otp_service(
            phone=data.phone,
            role=data.role,
            purpose=data.purpose,
            client_ip=request.client.host,
            language=data.response_language,
            redis=redis
        )
        log_info("OTP requested", extra={"phone": data.phone, "ip": request.client.host, "purpose": data.purpose})
        return result

    except HTTPException as e:
        log_error("OTP HTTPException", extra={"detail": str(e.detail)})
        raise

    except ValueError as e:
        log_error("OTP validation error", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except Exception as e:
        log_error("Unexpected error in OTP request", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_message("server.error", data.response_language)
        )
