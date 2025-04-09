# File: application/auth/controllers/logout.py

from fastapi import APIRouter, Request, Depends, HTTPException, status
from pydantic import Field, ConfigDict
from redis.asyncio import Redis
from typing import Annotated

from common.schemas.request_base import BaseRequestModel
from common.security.jwt_handler import get_current_user
from common.translations.messages import get_message
from common.logging.logger import log_info, log_error
from domain.auth.auth_services.auth_service.logout_service import logout_service
from infrastructure.database.redis.redis_client import get_redis_client
from common.utils.ip_utils import extract_client_ip

router = APIRouter()

class LogoutRequest(BaseRequestModel):
    """Request model for logging out a user."""
    logout_all: Annotated[bool, Field(description="If true, logs out from all sessions", examples=[True])]

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid"
    )

@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "User successfully logged out."},
        400: {"description": "Invalid request payload."},
        401: {"description": "Unauthorized."},
        404: {"description": "Session not found."},
        500: {"description": "Internal server error."}
    }
)
async def logout(
    request: Request,
    body: LogoutRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    redis: Annotated[Redis, Depends(get_redis_client)]
):
    """
    Logout a user from current session or all sessions.
    """
    try:
        user_id = current_user["user_id"]
        session_id = current_user["session_id"]
        language = body.response_language
        client_ip = await extract_client_ip(request)  # استفاده از extract_client_ip برای سازگاری

        if body.logout_all:
            result = await logout_service(
                user_id=user_id,
                session_id=session_id,
                client_ip=client_ip,
                redis=redis,
                language=language
            )
            log_info("User logged out from all sessions", extra={"user_id": user_id, "ip": client_ip})
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
            "ip": client_ip
        })

        if session_deleted == 0:
            log_error("Session not found for logout", extra={"user_id": user_id, "session_id": session_id})
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=get_message("auth.logout.session_not_found", language)
            )

        return {
            "message": get_message("auth.logout.single", language)
        }

    except HTTPException as e:
        raise e

    except Exception as e:
        log_error("Logout failed", extra={"user_id": user_id, "session_id": session_id, "error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_message("server.error", language)
        )