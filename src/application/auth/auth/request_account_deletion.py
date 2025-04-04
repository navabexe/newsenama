from fastapi import APIRouter, Request, status, Depends, HTTPException, Query
from redis.asyncio import Redis
from typing import Annotated

from common.security.jwt_handler import get_current_user
from common.translations.messages import get_message
from domain.auth.auth_services.auth_service.request_account_deletion import request_account_deletion_service
from infrastructure.database.redis.redis_client import get_redis_client
from common.logging.logger import log_info, log_error
from common.exceptions.base_exception import (
    BadRequestException,
    InternalServerErrorException
)

router = APIRouter()


@router.post(
    "/request-account-deletion",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Account deletion request submitted successfully."},
        400: {"description": "Invalid request payload."},
        401: {"description": "Unauthorized."},
        500: {"description": "Internal server error."}
    }
)
async def request_account_deletion(
    request: Request,
    current_user: Annotated[dict, Depends(get_current_user)],
    redis: Annotated[Redis, Depends(get_redis_client)],
    language: Annotated[str, Query(description="Response language (fa/en)")] = "fa",
):
    """
    Request account deletion for the authenticated user.
    """
    try:
        result = await request_account_deletion_service(
            user_id=current_user["user_id"],
            role=current_user.get("role"),
            client_ip=request.client.host,
            language=language,
            redis=redis
        )

        log_info("Account deletion requested", extra={"user_id": current_user["user_id"], "ip": request.client.host})
        return result

    except HTTPException as e:
        log_error("Account deletion HTTPException", extra={"detail": str(e.detail)}, exc_info=True)
        raise

    except ValueError as e:
        log_error("Account deletion validation error", extra={"error": str(e)}, exc_info=True)
        raise BadRequestException(detail=str(e))

    except Exception as e:
        log_error("Unexpected error in account deletion", extra={"error": str(e)}, exc_info=True)
        raise InternalServerErrorException(
            detail=get_message("server.error", language)
        )
