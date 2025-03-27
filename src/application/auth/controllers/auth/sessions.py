from fastapi import APIRouter, Request, Depends, HTTPException, status, Query
from redis.asyncio import Redis

from common.security.jwt_handler import get_current_user
from common.translations.messages import get_message
from domain.auth.auth_services.session_service.read import get_sessions_service
from infrastructure.database.redis.redis_client import get_redis_client

router = APIRouter()


@router.get("/sessions", status_code=status.HTTP_200_OK)
async def get_sessions(
    request: Request,
    language: str = Query(default="fa", description="Response language (fa/en)"),
    current_user: dict = Depends(get_current_user),
    redis: Redis = Depends(get_redis_client)
):
    try:
        return await get_sessions_service(
            user_id=current_user["user_id"],
            client_ip=request.client.host,
            redis=redis
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_message("server.error", language)
        )
