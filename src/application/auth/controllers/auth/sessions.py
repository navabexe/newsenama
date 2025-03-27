from fastapi import APIRouter, Request, Depends, HTTPException, status
from redis.asyncio import Redis

from common.security.jwt_handler import get_current_user
from common.translations.messages import get_message
from domain.auth.auth_services.session_service.read import get_sessions_service
from infrastructure.database.redis.redis_client import get_redis_client

router = APIRouter()


@router.get("/sessions", status_code=status.HTTP_200_OK)
async def get_sessions(
    request: Request,
    current_user: dict = Depends(get_current_user),
    redis: Redis = Depends(get_redis_client)
):
    try:
        return await get_sessions_service(current_user["user_id"], request.client.host, redis)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_message("server.error", "fa")
        )
