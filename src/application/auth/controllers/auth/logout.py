from fastapi import APIRouter, Request, Depends, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict
from redis.asyncio import Redis

from common.security.jwt_handler import get_current_user
from common.translations.messages import get_message
from domain.auth.auth_services.auth_service.logout import logout_service
from infrastructure.database.redis.redis_client import get_redis_client

router = APIRouter()


class LogoutRequest(BaseModel):
    logout_all: bool = Field(default=False, description="If true, logs out from all sessions")
    language: str = Field(default="fa", description="Response language (fa/en)")

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid"
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    body: LogoutRequest,
    current_user: dict = Depends(get_current_user),
    redis: Redis = Depends(get_redis_client)
):
    try:
        user_id = current_user["user_id"]
        session_id = current_user["session_id"]

        if body.logout_all:
            return await logout_service(user_id, session_id, request.client.host, redis, body.language)

        # فقط همین session فعلی
        await redis.delete(f"sessions:{user_id}:{session_id}")
        await redis.delete(f"refresh_tokens:{user_id}:{session_id}")

        return {
            "message": get_message("auth.logout.single", body.language)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_message("server.error", body.language)
        )
