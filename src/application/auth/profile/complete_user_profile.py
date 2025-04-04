from fastapi import APIRouter, Request, status, Depends
from pydantic import EmailStr, Field, ConfigDict
from typing import List, Optional, Annotated
from redis.asyncio import Redis

from common.schemas.request_base import BaseRequestModel
from common.schemas.standard_response import StandardResponse, Meta
from common.translations.messages import get_message
from domain.auth.auth_services.auth_service.complete_profile_service import complete_profile_service
from infrastructure.database.redis.redis_client import get_redis_client

from common.exceptions.base_exception import BadRequestException, InternalServerErrorException
from common.logging.logger import log_info, log_error
from common.utils.ip_utils import extract_client_ip

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

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


@router.post(
    "/complete-user-profile",
    status_code=status.HTTP_200_OK,
    response_model=StandardResponse,
    summary="Complete user profile",
    tags=["Authentication"]
)
async def complete_user_profile(
    data: CompleteUserProfile,
    request: Request,
    redis: Annotated[Redis, Depends(get_redis_client)]
):
    client_ip = extract_client_ip(request)

    try:
        result = await complete_profile_service(
            temporary_token=data.temporary_token,
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            languages=data.preferred_languages,
            request=request,
            language=data.response_language,
            redis=redis
        )

        log_info("User profile completed", extra={
            "email": data.email,
            "ip": client_ip,
            "endpoint": "/complete-user-profile"
        })

        return StandardResponse(**result)

    except BadRequestException as e:
        log_error("Validation error in profile completion", extra={
            "error": str(e.detail),
            "ip": client_ip,
            "endpoint": "/complete-user-profile"
        })
        raise

    except Exception as e:
        log_error("Unexpected error in profile completion", extra={
            "error": str(e),
            "ip": client_ip,
            "endpoint": "/complete-user-profile"
        }, exc_info=True)
        raise InternalServerErrorException(detail=get_message("server.error", data.response_language))
