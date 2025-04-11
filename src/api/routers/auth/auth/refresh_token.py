from typing import Annotated

from fastapi import APIRouter, Request, Depends, HTTPException, status
from pydantic import Field, ConfigDict
from redis.asyncio import Redis

from common.logging.logger import log_info, log_error
from common.schemas.request_base import BaseRequestModel
from common.schemas.standard_response import StandardResponse, Meta
from common.translations.messages import get_message
from common.utils.ip_utils import extract_client_ip
from domain.auth.services.refresh_token_service import refresh_tokens
from infrastructure.database.mongodb.mongo_client import get_mongo_collection
from infrastructure.database.mongodb.repository import MongoRepository
from infrastructure.database.redis.redis_client import get_redis_client

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
    response_model=StandardResponse,
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
    client_ip = await extract_client_ip(request)
    try:
        result = await refresh_tokens(
            request=request,
            refresh_token=body.refresh_token,
            redis=redis,
            users_repo=users_repo,
            vendors_repo=vendors_repo,
            language=body.response_language
        )
        log_info("Refresh token successful", extra={
            "ip": client_ip,
            "user_id": result.get("user_id", "unknown"),
            "session_id": result.get("session_id", "unknown")
        })
        return StandardResponse(
            meta=Meta(
                message=result["message"],
                status="success",
                code=200
            ),
            data={
                "access_token": result["access_token"],
                "refresh_token": result["refresh_token"],
                "status": result["status"]
            }
        )

    except HTTPException as e:
        log_error("Refresh token HTTPException", extra={"detail": str(e.detail), "ip": client_ip})
        raise

    except Exception as e:
        log_error("Refresh token error", extra={"error": str(e), "ip": client_ip})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_message("server.error", body.response_language)
        )