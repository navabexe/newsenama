# File: application/auth/controllers/otp/verify_otp.py

from fastapi import APIRouter, Request, HTTPException, status, Depends
from redis.asyncio import Redis
from pydantic import Field, model_validator, ConfigDict
from typing import Annotated

from common.schemas.request_base import BaseRequestModel
from common.translations.messages import get_message
from domain.auth.auth_services.otp_service.verify import verify_otp_service
from infrastructure.database.redis.redis_client import get_redis_client
from common.logging.logger import log_info, log_error

router = APIRouter()


class VerifyOTP(BaseRequestModel):
    """Request model for verifying an OTP."""

    otp: Annotated[str, Field(
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="6-digit one-time password",
        examples=["123456"]
    )]
    temporary_token: Annotated[str, Field(
        min_length=1,
        description="Temporary token from request-otp",
        examples=["eyJhbGciOi..."]
    )]

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid"
    )

    @model_validator(mode="after")
    def validate_otp_format(self) -> "VerifyOTP":
        if not self.otp.isdigit():
            raise ValueError("OTP must be numeric")
        return self


@router.post(
    "/verify-otp",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "OTP verified successfully."},
        400: {"description": "Invalid OTP or token."},
        500: {"description": "Internal server error."}
    }
)
async def verify_otp(
    data: VerifyOTP,
    request: Request,
    redis: Annotated[Redis, Depends(get_redis_client)]
):
    """
    Verify OTP and return tokens or instructions for next step.
    """
    try:
        result = await verify_otp_service(
            otp=data.otp,
            temporary_token=data.temporary_token,
            client_ip=request.client.host,
            language=data.response_language,
            redis=redis
        )
        log_info("OTP verified", extra={"ip": request.client.host, "token": data.temporary_token})
        return result

    except HTTPException as e:
        log_error("OTP HTTPException", extra={"detail": str(e.detail)})
        raise

    except ValueError as e:
        log_error("OTP validation error", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=get_message("otp.invalid", data.response_language)
        )

    except Exception as e:
        log_error("Unexpected OTP error", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_message("server.error", data.response_language)
        )
