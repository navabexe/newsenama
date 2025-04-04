from fastapi import APIRouter, Request, status, Depends, HTTPException, Query
from redis.asyncio import Redis
from typing import Annotated

from common.security.jwt_handler import get_current_user
from common.translations.messages import get_message
from domain.auth.auth_services.session_service.read import get_sessions_service
from infrastructure.database.redis.redis_client import get_redis_client
from common.logging.logger import log_info, log_error
from common.exceptions.base_exception import (
    BadRequestException,
    InternalServerErrorException,
    ForbiddenException
)

router = APIRouter()

@router.get(
    "/sessions",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "List of active sessions."},
        401: {"description": "Unauthorized."},
        500: {"description": "Internal server error."}
    }
)
async def get_sessions(
    request: Request,
    current_user: Annotated[dict, Depends(get_current_user)],
    redis: Annotated[Redis, Depends(get_redis_client)],
    language: Annotated[str, Query(description="Response language (fa/en)", examples=["fa", "en"])] = "fa"
):
    """
    Retrieve active sessions for the current user.
    """
    try:
        result = await get_sessions_service(
            user_id=current_user["user_id"],
            client_ip=request.client.host,
            redis=redis
        )
        log_info(
            "Sessions retrieved",
            extra={
                "user_id": current_user.get("user_id"),
                "ip": request.client.host
            }
        )
        return result

    except HTTPException as e:
        log_error("Get sessions HTTPException", extra={"detail": str(e.detail)}, exc_info=True)
        raise

    except ValueError as e:
        log_error("Get sessions validation error", extra={"error": str(e)}, exc_info=True)
        raise BadRequestException(detail=str(e))

    except Exception as e:
        log_error("Unexpected error in get_sessions", extra={"error": str(e)}, exc_info=True)
        raise InternalServerErrorException(
            detail=get_message("server.error", language)
        )
