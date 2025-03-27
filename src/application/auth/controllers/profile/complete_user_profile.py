# application/auth/controllers/profile/complete_user_profile.py

from fastapi import APIRouter, Request, HTTPException, status, Depends
from pydantic import EmailStr, Field
from redis.asyncio import Redis

from common.schemas.request_base import BaseRequestModel
from common.translations.messages import get_message
from domain.auth.auth_services.auth_service.complete_profile import complete_profile_service
from infrastructure.database.redis.redis_client import get_redis_client

router = APIRouter()


class CompleteUserProfile(BaseRequestModel):
    temporary_token: str = Field(..., description="Temporary token from verify-otp")
    first_name: str = Field(..., min_length=2, description="User's first name")
    last_name: str = Field(..., min_length=2, description="User's last name")
    email: EmailStr = Field(..., description="User's email address")


@router.post("/complete-user-profile", status_code=status.HTTP_200_OK)
async def complete_user_profile(
    data: CompleteUserProfile,
    request: Request,
    redis: Redis = Depends(get_redis_client)
):
    try:
        return await complete_profile_service(
            temporary_token=data.temporary_token,
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            client_ip=request.client.host,
            language=data.language,
            redis=redis
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_message("server.error", data.language)
        )
