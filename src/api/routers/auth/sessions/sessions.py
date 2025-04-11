# File: src/routers/auth/sessions/sessions.py

from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Request, status, Depends, HTTPException, Query
from redis.asyncio import Redis

from common.exceptions.base_exception import BadRequestException, InternalServerErrorException, ForbiddenException
from common.logging.logger import log_info, log_error
from common.schemas.standard_response import StandardResponse, Meta
from common.security.jwt_handler import get_current_user
from common.translations.messages import get_message
from common.utils.ip_utils import extract_client_ip
from domain.auth.services.get_sessions_service import get_sessions_service
from infrastructure.database.redis.redis_client import get_redis_client

router = APIRouter(tags=["Sessions"])

@router.get(
    "/sessions",
    status_code=status.HTTP_200_OK,
    response_model=StandardResponse,
    summary="Retrieve user sessions",
    description="Retrieve a list of user sessions with optional status filtering. Admins can specify a target user ID.",
    responses={
        200: {"description": "List of sessions retrieved successfully."},
        400: {"description": "Invalid request parameters."},
        401: {"description": "Unauthorized."},
        403: {"description": "Forbidden."},
        500: {"description": "Internal server error."}
    }
)
async def get_sessions(
    request: Request,
    current_user: Annotated[dict, Depends(get_current_user)],
    redis: Annotated[Redis, Depends(get_redis_client)],
    status: Annotated[Literal["active", "all"], Query(description="Filter sessions by status (active/all)", examples=["active", "all"])] = "active",
    language: Annotated[Literal["fa", "en"], Query(description="Response language (fa/en)", examples=["fa", "en"])] = "fa",
    target_user_id: Annotated[Optional[str], Query(description="Target user ID (admin only)", examples=["67f1ab9aa90fbdfdf44e3984"])] = None
):
    """
    Retrieve sessions for the current user or a target user (admin only) with filtering options.

    Args:
        request (Request): The incoming HTTP request.
        current_user (dict): Authenticated user data from JWT.
        redis (Redis): Redis client dependency.
        status (str): Filter sessions by status ("active" or "all"). Defaults to "active".
        language (str): Language for response messages and notifications ("fa" or "en"). Defaults to "fa".
        target_user_id (str, optional): ID of the user to retrieve sessions for (admin only).

    Returns:
        StandardResponse: A structured response with session data and metadata.
    """
    client_ip = await extract_client_ip(request)  # await اضافه شده
    user_id = current_user["user_id"]
    user_role = current_user["role"]

    # Determine the target user ID
    if target_user_id:
        if user_role != "admin":
            log_error("Non-admin attempted to access another user's sessions", extra={
                "user_id": user_id,
                "target_user_id": target_user_id,
                "ip": client_ip,
                "endpoint": "/sessions"
            })
            raise ForbiddenException(detail=get_message("auth.forbidden", language))
        target_id = target_user_id
    else:
        target_id = user_id

    try:
        result = await get_sessions_service(
            user_id=target_id,
            client_ip=client_ip,  # حالا یه str هست
            status_filter=status,
            language=language,
            requester_role=user_role,
            redis=redis
        )

        log_info("Sessions retrieved endpoint", extra={
            "user_id": user_id,
            "role": user_role,
            "target_user_id": target_id,
            "ip": client_ip,
            "status_filter": status,
            "session_count": len(result["sessions"]),
            "endpoint": "/sessions"
        })

        message_key = "sessions.active_retrieved" if status == "active" else "sessions.all_retrieved"
        return StandardResponse(
            meta=Meta(
                status="success",
                code=200,
                message=get_message(message_key, language)
            ),
            data={
                "sessions": result["sessions"],
                "notification_sent": result["notification_sent"]
            }
        )

    except HTTPException as e:
        log_error("Get sessions HTTPException", extra={
            "detail": str(e.detail),
            "user_id": user_id,
            "target_user_id": target_id,
            "ip": client_ip,
            "endpoint": "/sessions"
        }, exc_info=True)
        raise

    except ValueError as e:
        log_error("Get sessions validation error", extra={
            "error": str(e),
            "user_id": user_id,
            "target_user_id": target_id,
            "ip": client_ip,
            "endpoint": "/sessions"
        }, exc_info=True)
        raise BadRequestException(detail=str(e))

    except Exception as e:
        log_error("Unexpected error in get_sessions endpoint", extra={
            "error": str(e),
            "user_id": user_id,
            "target_user_id": target_id,
            "ip": client_ip,
            "endpoint": "/sessions"
        }, exc_info=True)
        raise InternalServerErrorException(detail=get_message("server.error", language))