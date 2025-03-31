# File: application/auth/controllers/profile/complete_user_profile.py
from fastapi import APIRouter, Request, HTTPException, status, Depends
from pydantic import EmailStr, Field
from typing import List, Optional
from redis.asyncio import Redis

from common.schemas.request_base import BaseRequestModel
from common.translations.messages import get_message
from domain.auth.auth_services.auth_service.complete_profile import complete_profile_service
from infrastructure.database.redis.redis_client import get_redis_client

router = APIRouter()


class CompleteUserProfile(BaseRequestModel):
    """Request model for completing a user profile."""

    temporary_token: str = Field(..., description="Temporary token from verify-otp")
    first_name: str = Field(..., min_length=2, description="User's first name")
    last_name: str = Field(..., min_length=2, description="User's last name")
    email: Optional[EmailStr] = Field(default=None, description="User's email address")
    preferred_languages: Optional[List[str]] = Field(
        default_factory=list,
        description="Preferred languages for the user profile"
    )

    model_config = {
        "str_strip_whitespace": True,
        "extra": "forbid"
    }


@router.post("/complete-user-profile", status_code=status.HTTP_200_OK)
async def complete_user_profile(
        data: CompleteUserProfile,
        request: Request,
        redis: Redis = Depends(get_redis_client)
):
    """
    Complete a user's profile using provided data.

    Args:
        data (CompleteUserProfile): User profile data.
        request (Request): FastAPI request object.
        redis (Redis): Redis client instance.

    Returns:
        dict: Response with access token, refresh token, status, and message.
    """
    try:
        return await complete_profile_service(
            temporary_token=data.temporary_token,
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            languages=data.preferred_languages,
            client_ip=request.client.host,
            language=data.response_language,
            redis=redis
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_message("server.error", data.response_language)
        )