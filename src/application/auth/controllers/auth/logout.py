# File: application/auth/controllers/logout.py
from fastapi import APIRouter, Request, Depends, HTTPException, status
from pydantic import Field
from redis.asyncio import Redis

from common.schemas.request_base import BaseRequestModel
from common.security.jwt_handler import get_current_user
from common.translations.messages import get_message
from common.logging.logger import log_info, log_error
from domain.auth.auth_services.auth_service.logout import logout_service
from infrastructure.database.redis.redis_client import get_redis_client

router = APIRouter()


class LogoutRequest(BaseRequestModel):
    """Request model for logging out a user."""
    logout_all: bool = Field(default=False, description="If true, logs out from all sessions")


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
        request: Request,
        body: LogoutRequest,
        current_user: dict = Depends(get_current_user),
        redis: Redis = Depends(get_redis_client)
):
    """
    Logout a user from current session or all sessions.

    Args:
        request (Request): FastAPI request object.
        body (LogoutRequest): Logout options.
        current_user (dict): Current authenticated user.
        redis (Redis): Redis client instance.

    Returns:
        dict: Logout confirmation message.
    """
    try:
        user_id = current_user["user_id"]
        session_id = current_user["session_id"]
        language = body.response_language

        if body.logout_all:
            result = await logout_service(
                user_id=user_id,
                session_id=session_id,
                client_ip=request.client.host,
                redis=redis,
                language=language
            )
            return result

        session_key = f"sessions:{user_id}:{session_id}"
        refresh_key = f"refresh_tokens:{user_id}:{session_id}"

        session_deleted = await redis.delete(session_key)
        refresh_deleted = await redis.delete(refresh_key)

        log_info("User logged out from single session", extra={
            "user_id": user_id,
            "session_id": session_id,
            "session_deleted": session_deleted,
            "refresh_deleted": refresh_deleted,
            "ip": request.client.host
        })

        return {
            "message": get_message("auth.logout.single", language)
        }

    except HTTPException:
        raise
    except Exception as e:
        log_error("Logout failed", extra={"user_id": user_id, "session_id": session_id, "error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_message("server.error", language)
        )