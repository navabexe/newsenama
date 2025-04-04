# File: src/application/auth/otp/verify_otp.py

from fastapi import APIRouter, Request, status, Depends, HTTPException
from pydantic import Field
from typing import Annotated
from redis.asyncio import Redis

from common.schemas.request_base import BaseRequestModel
from common.schemas.standard_response import StandardResponse, Meta
from common.translations.messages import get_message
from common.logging.logger import log_info, log_error
from common.exceptions.base_exception import (
    BadRequestException,
    InternalServerErrorException,
    UnauthorizedException
)
from common.utils.ip_utils import extract_client_ip

from infrastructure.database.redis.redis_client import get_redis_client
from domain.auth.auth_services.otp_service.verify_otp_service import verify_otp_service

router = APIRouter()


class VerifyOTPModel(BaseRequestModel):
    otp: Annotated[str, Field(min_length=4, max_length=10, description="One-time password")]
    temporary_token: Annotated[str, Field(description="Temporary token issued with OTP")]

    model_config = {
        "str_strip_whitespace": True,
        "extra": "allow",  # ← اجازه به request_id و client_version و response_language
    }


@router.post(
    "/verify-otp",
    status_code=status.HTTP_200_OK,
    response_model=StandardResponse,
    summary="Verify OTP",
    tags=["Authentication"]
)
async def verify_otp_endpoint(
    data: VerifyOTPModel,
    request: Request,
    redis: Annotated[Redis, Depends(get_redis_client)]
):
    client_ip = extract_client_ip(request)
    language = getattr(data, "response_language", "fa")

    try:
        result = await verify_otp_service(
            otp=data.otp,
            temporary_token=data.temporary_token,
            client_ip=client_ip,
            language=language,
            redis=redis
        )

        log_info("OTP verified", extra={
            "phone": result.get("phone"),
            "ip": client_ip,
            "endpoint": "/verify-otp"
        })

        return StandardResponse(
            meta=Meta(
                message=result["message"],
                status="success",
                code=200
            ),
            data={key: val for key, val in result.items() if key != "message"}
        )

    except HTTPException as http_exc:
        # خطاهای JWT یا 400/401 که خود verify_otp_service انداخته
        log_error("Handled error in /verify-otp", extra={
            "error": str(http_exc.detail),
            "ip": client_ip,
            "endpoint": "/verify-otp"
        })
        raise http_exc

    except Exception as e:
        log_error("Internal server error in /verify-otp", extra={
            "error": str(e),
            "ip": client_ip,
            "endpoint": "/verify-otp"
        }, exc_info=True)
        raise InternalServerErrorException(detail=get_message("server.error", language))
