# File: application/auth/controllers/force_logout.py

from fastapi import APIRouter, Request, Depends, HTTPException, status
from redis.asyncio import Redis
from typing import Annotated
from pydantic import BaseModel, Field, ConfigDict

from common.security.jwt_handler import get_current_user
from common.translations.messages import get_message
from domain.auth.auth_services.auth_service.force_logout_service import force_logout_service
from infrastructure.database.redis.redis_client import get_redis_client
from common.logging.logger import log_info, log_error

router = APIRouter()

class ForceLogoutRequest(BaseModel):
    target_user_id: Annotated[str, Field(description="ID of the user to force logout", examples=["user_123"])]
    language: Annotated[str, Field(description="Response language", examples=["fa", "en"])] = "fa"

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid"
    )

@router.post(
    "/force-logout",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "User has been forcefully logged out."},
        400: {"description": "Invalid request."},
        401: {"description": "Unauthorized."},
        403: {"description": "Forbidden. Admins only."},
        404: {"description": "User not found or no active sessions."},
        500: {"description": "Internal server error."}
    }
)
async def force_logout(
    data: ForceLogoutRequest,
    request: Request,
    current_user: Annotated[dict, Depends(get_current_user)],
    redis: Annotated[Redis, Depends(get_redis_client)]
):
    """
    Force logout a specific user from all sessions (admin only).
    """
    try:
        if current_user.get("role") != "admin":
            log_error("Force logout forbidden", extra={"user": current_user.get("id")})
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=get_message("auth.forbidden", data.language)
            )

        result = await force_logout_service(
            current_user=current_user,
            target_user_id=data.target_user_id,
            client_ip=request.client.host,
            language=data.language,
            redis=redis
        )
        log_info("Force logout successful", extra={"admin": current_user.get("id"), "target": data.target_user_id})
        return result

    except HTTPException as e:
        log_error("Force logout HTTPException", extra={"detail": str(e.detail)})
        raise

    except Exception as e:
        log_error("Unexpected error in force logout", extra={"error": str(e)})
        raise HTTPException(
            status_code=500,
            detail=get_message("server.error", data.language)
        )