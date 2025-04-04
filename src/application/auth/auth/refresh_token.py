# File: application/auth/controllers/refresh_token.py

from fastapi import APIRouter, Request, Depends, HTTPException, status
from redis.asyncio import Redis
from typing import Annotated
from pydantic import Field, ConfigDict

from common.schemas.request_base import BaseRequestModel
from common.translations.messages import get_message
from domain.auth.auth_services.auth_service.refresh_token import refresh_tokens
from infrastructure.database.redis.redis_client import get_redis_client
from infrastructure.database.mongodb.mongo_client import get_mongo_collection
from infrastructure.database.mongodb.repository import MongoRepository
from common.logging.logger import log_info, log_error

router = APIRouter()

class RefreshTokenRequest(BaseRequestModel):
    refresh_token: Annotated[str, Field(min_length=10, description="Valid refresh token", examples=["eyJhbGciOi..."])]
    response_language: Annotated[str, Field(description="Preferred response language", examples=["fa", "en"])] = "fa"

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid"
    )


@router.post(
    "/refresh-token",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Token refreshed successfully."},
        400: {"description": "Invalid refresh token."},
        401: {"description": "Unauthorized."},
        500: {"description": "Internal server error."}
    }
)
async def refresh_token(
    request: Request,
    body: RefreshTokenRequest,
    redis: Annotated[Redis, Depends(get_redis_client)],
    users_repo: Annotated[MongoRepository, Depends(get_mongo_collection("users"))],
    vendors_repo: Annotated[MongoRepository, Depends(get_mongo_collection("vendors"))]
):
    try:
        result = await refresh_tokens(
            request=request,
            refresh_token=body.refresh_token,
            redis=redis,
            users_repo=users_repo,
            vendors_repo=vendors_repo,
            language=body.response_language
        )
        log_info("Refresh token successful", extra={"ip": request.client.host})
        return result

    except HTTPException as e:
        log_error("Refresh token HTTPException", extra={"detail": str(e.detail)})
        raise

    except Exception as e:
        log_error("Refresh token error", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_message("server.error", body.response_language)
        )