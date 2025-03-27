from fastapi import APIRouter, Request, HTTPException, status, Depends
from redis.asyncio import Redis
from pydantic import Field, model_validator

from common.schemas.request_base import BaseRequestModel
from common.translations.messages import get_message
from domain.auth.auth_services.otp_service.verify import verify_otp_service
from infrastructure.database.redis.redis_client import get_redis_client

router = APIRouter()


class VerifyOTP(BaseRequestModel):
    otp: str = Field(
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="6-digit one-time password"
    )
    temporary_token: str = Field(
        min_length=1,
        description="Temporary token from request-otp"
    )

    @model_validator(mode="after")
    def validate_otp_format(self) -> "VerifyOTP":
        if not self.otp.isdigit():
            raise ValueError("OTP must be numeric")
        return self

    model_config = {
        "str_strip_whitespace": True,
        "extra": "forbid"
    }


@router.post("/verify-otp", status_code=status.HTTP_200_OK)
async def verify_otp(
    data: VerifyOTP,
    request: Request,
    redis: Redis = Depends(get_redis_client)
):
    """
    Verify OTP and return tokens or instructions for next step.
    """
    try:
        return await verify_otp_service(
            otp=data.otp,
            temporary_token=data.temporary_token,
            client_ip=request.client.host,
            language=data.language,
            redis=redis  # ✅ اضافه شد
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=get_message("otp.invalid", data.language)
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_message("server.error", data.language)
        )
