# File: src/application/auth/otp/verify_otp.py
from fastapi import APIRouter, Request, status, Depends, HTTPException
from pydantic import Field
from typing import Annotated
from redis.asyncio import Redis
from motor.motor_asyncio import AsyncIOMotorDatabase

from common.schemas.request_base import BaseRequestModel
from common.schemas.standard_response import StandardResponse, Meta
from common.translations.messages import get_message
from common.logging.logger import log_info, log_error
from common.exceptions.base_exception import InternalServerErrorException, DatabaseConnectionException
from common.dependencies.ip_dep import get_client_ip  # استفاده از Dependency
from domain.auth.auth_services.otp_service.verify_otp_service import verify_otp_service
from infrastructure.database.redis.redis_client import get_redis_client
from infrastructure.database.mongodb.connection import get_mongo_db
from common.config.settings import settings

router = APIRouter()

class VerifyOTPModel(BaseRequestModel):
    otp: Annotated[str, Field(min_length=4, max_length=10, description="One-time password")]
    temporary_token: Annotated[str, Field(description="Temporary token issued with OTP")]
    request_id: Annotated[str | None, Field(default=None, description="Request identifier for tracing")]
    client_version: Annotated[str | None, Field(default=None, description="Version of the client app")]
    device_fingerprint: Annotated[str | None, Field(default=None, description="Device fingerprint")]

    model_config = {
        "str_strip_whitespace": True,
        "extra": "allow",
    }

@router.post(
    settings.VERIFY_OTP_PATH,
    status_code=status.HTTP_200_OK,
    response_model=StandardResponse,
    summary="Verify OTP",
    tags=[settings.AUTH_TAG]
)
async def verify_otp_endpoint(
    data: VerifyOTPModel,
    request: Request,
    redis: Annotated[Redis, Depends(get_redis_client)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_mongo_db)],
    client_ip: Annotated[str, Depends(get_client_ip)]
):
    language = getattr(data, "response_language", "fa")
    user_agent = request.headers.get("User-Agent", "Unknown")

    try:
        result = await verify_otp_service(
            otp=data.otp,
            temporary_token=data.temporary_token,
            client_ip=client_ip,
            language=language,
            redis=redis,
            db=db,
            request_id=data.request_id,
            client_version=data.client_version,
            device_fingerprint=data.device_fingerprint,
            user_agent=user_agent
        )

        log_info("OTP verified successfully", extra={
            "phone": result.get("phone"),
            "ip": client_ip,
            "endpoint": settings.VERIFY_OTP_PATH,
            "request_id": data.request_id,
            "client_version": data.client_version,
            "device_fingerprint": data.device_fingerprint,
            "user_agent": user_agent
        })

        return StandardResponse(
            meta=Meta(
                message=result["message"],
                status="success",
                code=200
            ),
            data={key: val for key, val in result.items() if key != "message"}
        )

    except DatabaseConnectionException as db_exc:
        log_error("Database error in verify-otp", extra={
            "error": str(db_exc),
            "ip": client_ip,
            "endpoint": settings.VERIFY_OTP_PATH,
            "request_id": data.request_id,
            "client_version": data.client_version,
            "device_fingerprint": data.device_fingerprint
        }, exc_info=True)
        raise
    except HTTPException as http_exc:
        log_error("Handled HTTPException in verify-otp", extra={
            "error": str(http_exc.detail),
            "ip": client_ip,
            "endpoint": settings.VERIFY_OTP_PATH,
            "request_id": data.request_id,
            "client_version": data.client_version,
            "device_fingerprint": data.device_fingerprint
        })
        raise http_exc

    except Exception as e:
        log_error("Internal server error in verify-otp", extra={
            "error": str(e),
            "ip": client_ip,
            "endpoint": settings.VERIFY_OTP_PATH,
            "request_id": data.request_id,
            "client_version": data.client_version,
            "device_fingerprint": data.device_fingerprint
        }, exc_info=True)
        raise InternalServerErrorException(detail=get_message("server.error", language))