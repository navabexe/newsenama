# refresh_token_endpoint.py
from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import Field
from redis.asyncio import Redis

from common.schemas.request_base import BaseRequestModel
from domain.auth.auth_services.auth_service.refresh_token import refresh_tokens
from infrastructure.database.redis.redis_client import get_redis_client
from infrastructure.database.mongodb.mongo_client import get_mongo_collection
from infrastructure.database.mongodb.repository import MongoRepository

router = APIRouter()

class RefreshTokenRequest(BaseRequestModel):
    refresh_token: str = Field(..., min_length=10, description="Valid refresh token")
    response_language: str = Field(default="fa", description="Preferred response language")

@router.post("/refresh-token")
async def refresh_token(
    request: Request,
    body: RefreshTokenRequest,
    redis: Redis = Depends(get_redis_client),
    users_repo: MongoRepository = Depends(get_mongo_collection("users")),
    vendors_repo: MongoRepository = Depends(get_mongo_collection("vendors"))
):
    try:
        return await refresh_tokens(
            request=request,
            refresh_token=body.refresh_token,
            redis=redis,
            users_repo=users_repo,
            vendors_repo=vendors_repo,
            language=body.response_language
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
