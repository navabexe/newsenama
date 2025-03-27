from fastapi import APIRouter, Request, Depends, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict
from redis.asyncio import Redis

from common.security.jwt_handler import get_current_user
from domain.auth.auth_services.auth_service.force_logout import force_logout_service
from common.translations.messages import get_message
from infrastructure.database.redis.redis_client import get_redis_client

router = APIRouter()


class ForceLogoutRequest(BaseModel):
    target_user_id: str = Field(..., description="ID of the user to force logout")
    language: str = Field(default="fa", description="Response language")

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid"
    )


@router.post("/force-logout", status_code=status.HTTP_200_OK)
async def force_logout(
    data: ForceLogoutRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
    redis: Redis = Depends(get_redis_client)
):
    """
    Force logout a specific user from all sessions (admin only).
    """
    try:
        if current_user.get("role") != "admin":
            raise HTTPException(
                status_code=403,
                detail=get_message("auth.forbidden", data.language)
            )

        return await force_logout_service(
            current_user=current_user,
            target_user_id=data.target_user_id,
            client_ip=request.client.host,
            language=data.language,
            redis=redis
        )

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail=get_message("server.error", data.language)
        )
