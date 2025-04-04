# File: application/auth/controllers/profile/complete_user_profile.py

from fastapi import APIRouter, Request, HTTPException, status, Depends
from pydantic import EmailStr, Field, ConfigDict
from typing import List, Optional, Annotated
from redis.asyncio import Redis

from common.schemas.request_base import BaseRequestModel
from common.translations.messages import get_message
from domain.auth.auth_services.auth_service.complete_profile import complete_profile_service
from infrastructure.database.redis.redis_client import get_redis_client
from common.logging.logger import log_info, log_error

router = APIRouter()


class CompleteUserProfile(BaseRequestModel):
    """Request model for completing a user profile."""

    temporary_token: Annotated[str, Field(description="Temporary token from verify-otp", examples=["eyJhbGciOi..."])]
    first_name: Annotated[str, Field(min_length=2, description="User's first name", examples=["Ali"])]
    last_name: Annotated[str, Field(min_length=2, description="User's last name", examples=["Rezaei"])]
    email: Optional[EmailStr] = Field(default=None, description="User's email address", examples=["user@example.com"])
    preferred_languages: Optional[List[str]] = Field(
        default_factory=list,
        description="Preferred languages for the user profile",
        examples=[["fa", "en"]]
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid"
    )


@router.post(
    "/complete-user-profile",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Profile completed successfully."},
        400: {"description": "Validation failed."},
        500: {"description": "Internal server error."}
    }
)
async def complete_user_profile(
    data: CompleteUserProfile,
    request: Request,
    redis: Annotated[Redis, Depends(get_redis_client)]
):
    """
    Complete a user's profile using provided data.
    """
    try:
        result = await complete_profile_service(
            temporary_token=data.temporary_token,
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            languages=data.preferred_languages,
            client_ip=request.client.host,
            language=data.response_language,
            redis=redis
        )
        log_info("User profile completed", extra={"ip": request.client.host, "email": data.email})
        return result

    except HTTPException as e:
        log_error("Complete profile HTTPException", extra={"detail": str(e.detail)})
        raise

    except Exception as e:
        log_error("Unexpected error in completing profile", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_message("server.error", data.response_language)
        )