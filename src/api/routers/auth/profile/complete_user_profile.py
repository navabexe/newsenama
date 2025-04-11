# File: src/routers/auth/complete_user_profile.py
from typing import List, Optional, Annotated

from fastapi import APIRouter, Request, status, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import EmailStr, Field, ConfigDict
from redis.asyncio import Redis

from common.config.settings import settings
from common.exceptions.base_exception import InternalServerErrorException
from common.logging.logger import log_info, log_error
from common.schemas.request_base import BaseRequestModel
from common.schemas.standard_response import StandardResponse
from common.translations.messages import get_message
from common.utils.ip_utils import extract_client_ip
from domain.auth.services.complete_profile_service import complete_profile_service
from infrastructure.database.mongodb.connection import get_mongo_db
from infrastructure.database.redis.redis_client import get_redis_client

router = APIRouter()

class CompleteUserProfile(BaseRequestModel):
    temporary_token: Annotated[str, Field(description="Temporary token from verify-otp")]
    first_name: Annotated[str, Field(min_length=2, max_length=30, description="User's first name")]
    last_name: Annotated[str, Field(min_length=2, max_length=30, description="User's last name")]
    email: Optional[EmailStr] = Field(default=None, description="User's email address")
    preferred_languages: Optional[List[str]] = Field(
        default_factory=list,
        description="Preferred languages for the user profile"
    )
    request_id: Optional[str] = Field(default=None, max_length=36, description="Request identifier for tracing")
    client_version: Optional[str] = Field(default=None, max_length=15, description="Version of the client app")
    device_fingerprint: Optional[str] = Field(default=None, max_length=100, description="Device fingerprint")

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

def log_endpoint_error(error: str | Exception, client_ip: str, data: CompleteUserProfile, endpoint: str = settings.COMPLETE_USER_PROFILE_PATH):
    log_error(f"Handled error in {endpoint}", extra={
        "error": str(error),
        "ip": client_ip,
        "endpoint": endpoint,
        "request_id": data.request_id,
        "client_version": data.client_version,
        "device_fingerprint": data.device_fingerprint
    })

@router.post(
    settings.COMPLETE_USER_PROFILE_PATH,
    status_code=status.HTTP_200_OK,
    response_model=StandardResponse,
    summary="Complete user profile",
    tags=[settings.AUTH_TAG]
)
async def complete_user_profile(
    data: CompleteUserProfile,
    request: Request,
    redis: Annotated[Redis, Depends(get_redis_client)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_mongo_db)]
):
    client_ip = await extract_client_ip(request)
    language = data.response_language

    try:
        result = await complete_profile_service(
            temporary_token=data.temporary_token,
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            languages=data.preferred_languages,
            request=request,
            language=language,
            redis=redis,
            db=db
        )

        log_info("User profile completed", extra={
            "email": data.email,
            "ip": client_ip,
            "endpoint": settings.COMPLETE_USER_PROFILE_PATH,
            "request_id": data.request_id,
            "client_version": data.client_version,
            "device_fingerprint": data.device_fingerprint
        })

        return StandardResponse(
            meta=result["meta"],
            data=result["data"]
        )

    except HTTPException as http_exc:
        log_endpoint_error(http_exc.detail, client_ip, data)
        raise http_exc

    except Exception as e:
        log_endpoint_error(e, client_ip, data, exc_info=True)
        raise InternalServerErrorException(detail=get_message("server.error", language))