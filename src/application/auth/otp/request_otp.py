# File: src/application/auth/otp/request_otp.py

from fastapi import APIRouter, Request, status, Depends, HTTPException
from redis.asyncio import Redis
from typing import Annotated

from domain.auth.entities.otp_entity import RequestOTPInput
from infrastructure.database.redis.redis_client import get_redis_client
from domain.auth.auth_services.otp_service.request_otp_service import request_otp_service
from common.schemas.standard_response import StandardResponse, Meta
from common.translations.messages import get_message
from common.logging.logger import log_info, log_error
from common.exceptions.base_exception import BadRequestException, InternalServerErrorException
from common.utils.ip_utils import extract_client_ip

router = APIRouter()

@router.post(
    "/request-otp",
    status_code=status.HTTP_200_OK,
    response_model=StandardResponse,
    summary="Request OTP for login/signup",
    tags=["Authentication"]
)
async def request_otp_endpoint(
    data: RequestOTPInput,
    request: Request,
    redis: Annotated[Redis, Depends(get_redis_client)]
):
    try:
        result = await request_otp_service(
            phone=data.phone,
            role=data.role,
            purpose=data.purpose,
            request=request,
            language=data.response_language,
            redis=redis
        )

        log_info("OTP request successful", extra={
            "phone": data.phone,
            "role": data.role,
            "purpose": data.purpose,
            "ip": extract_client_ip(request),
            "endpoint": "/request-otp",
            "client_version": data.client_version,
            "device_fingerprint": data.device_fingerprint,
            "request_id": data.request_id
        })

        return StandardResponse(
            meta=Meta(
                message=result["message"],
                status="success",
                code=200
            ),
            data={
                "temporary_token": result["temporary_token"],
                "expires_in": result["expires_in"]
            }
        )

    except HTTPException as http_exc:
        log_error("Handled HTTPException in /request-otp", extra={
            "error": str(http_exc.detail),
            "phone": data.phone,
            "role": data.role,
            "ip": extract_client_ip(request),
            "endpoint": "/request-otp",
            "client_version": data.client_version,
            "device_fingerprint": data.device_fingerprint,
            "request_id": data.request_id
        })
        raise http_exc

    except Exception as e:
        log_error("Internal server error in /request-otp", extra={
            "error": str(e),
            "phone": data.phone,
            "role": data.role,
            "ip": extract_client_ip(request),
            "endpoint": "/request-otp",
            "client_version": data.client_version,
            "device_fingerprint": data.device_fingerprint,
            "request_id": data.request_id
        }, exc_info=True)
        raise InternalServerErrorException(detail=get_message("server.error", data.response_language))
