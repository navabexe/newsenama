# File: src/application/auth/otp/request_otp.py

from fastapi import APIRouter, Request, Depends
from redis.asyncio import Redis
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Annotated

from starlette import status

from domain.auth.auth_services.otp_service.request_otp_service import otp_request_service
from domain.auth.entities.otp_entity import RequestOTPInput
from infrastructure.database.redis.redis_client import get_redis_client
from infrastructure.database.mongodb.connection import get_mongo_db
from common.schemas.standard_response import StandardResponse
from common.logging.logger import log_info
from common.dependencies.ip_dep import get_client_ip
from common.config.settings import settings

router = APIRouter()

@router.post(
    settings.REQUEST_OTP_PATH,
    status_code=status.HTTP_200_OK,
    response_model=StandardResponse,
    summary="Request OTP for login/signup",
    tags=[settings.AUTH_TAG]
)
async def request_otp_endpoint(
    data: RequestOTPInput,
    request: Request,
    redis: Annotated[Redis, Depends(get_redis_client)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_mongo_db)],
    client_ip: Annotated[str, Depends(get_client_ip)]
):
    result = await otp_request_service.request_otp_service(
        phone=data.phone,
        role=data.role,
        purpose=data.purpose,
        request=request,
        language=data.response_language,
        redis=redis,
        db=db,
        request_id=data.request_id,
        client_version=data.client_version,
        device_fingerprint=data.device_fingerprint
    )

    log_info("OTP request successful", extra={
        "phone": data.phone,
        "role": data.role,
        "purpose": data.purpose,
        "ip": client_ip,
        "endpoint": settings.REQUEST_OTP_PATH,
        "request_id": data.request_id,
        "client_version": data.client_version,
        "device_fingerprint": data.device_fingerprint
    })

    return StandardResponse.success(
        data={
            "temporary_token": result["temporary_token"],
            "expires_in": result["expires_in"],
            "notification_sent": result["notification_sent"]
        },
        message=result["message"]
    )
