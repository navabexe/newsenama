import phonenumbers
from fastapi import APIRouter, Request, status, Depends
from pydantic import Field, model_validator, ConfigDict
from typing import Annotated

from redis.asyncio import Redis

from common.schemas.request_base import BaseRequestModel
from common.schemas.standard_response import StandardResponse
from common.translations.messages import get_message
from domain.auth.auth_services.otp_service.request import request_otp_service
from infrastructure.database.redis.redis_client import get_redis_client
from common.logging.logger import log_info, log_error
from common.exceptions.base_exception import BadRequestException, InternalServerErrorException

router = APIRouter()


class RequestOTP(BaseRequestModel):
    """Request model for requesting an OTP."""
    phone: Annotated[str, Field(
        description="Phone number (e.g., +989123456789)",
        examples=["+989123456789"]
    )]
    role: Annotated[str, Field(
        pattern=r"^(user|vendor)$",
        description="User or vendor",
        examples=["user", "vendor"]
    )]
    purpose: Annotated[str, Field(
        pattern=r"^(login|signup)$",
        description="Login or signup",
        examples=["login", "signup"]
    )]

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
    response_model=StandardResponse,
    summary="Request OTP for login or signup",
    tags=["Authentication"],
    responses={
        200: {"description": "OTP sent successfully."},
        400: {"description": "Invalid input."},
        429: {"description": "Too many attempts."},
        500: {"description": "Internal server error."}
    }
)
async def request_otp(
    data: RequestOTP,
    request: Request,
    redis: Annotated[Redis, Depends(get_redis_client)]
):
    """
    Request an OTP for login or signup via phone number.
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
        log_info("OTP request successful", extra={
            "phone": data.phone,
            "role": data.role,
            "purpose": data.purpose,
            "ip": request.client.host,
            "endpoint": "/request-otp"
        })
        return StandardResponse(
            meta={
                "message": result["message"],
                "status": "success",
                "code": 200
            },
            data={
                "temporary_token": result["temporary_token"],
                "expires_in": result["expires_in"]
            }
        )

    except ValueError as e:
        log_error("OTP validation error", extra={
            "error": str(e),
            "ip": request.client.host,
            "endpoint": "/request-otp"
        })
        raise BadRequestException(detail=str(e))

    except Exception as e:
        log_error("OTP request failed", extra={
            "error": str(e),
            "ip": request.client.host,
            "endpoint": "/request-otp"
        }, exc_info=True)
        raise InternalServerErrorException(detail=get_message("server.error", data.response_language))
