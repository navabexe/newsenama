from fastapi import APIRouter, Request, Depends, HTTPException, status, Query
from redis.asyncio import Redis

from common.security.jwt_handler import get_current_user
from common.translations.messages import get_message
from domain.auth.auth_services.auth_service.request_account_deletion import request_account_deletion_service
from infrastructure.database.redis.redis_client import get_redis_client

router = APIRouter()


@router.post("/request-account-deletion", status_code=status.HTTP_200_OK)
async def request_account_deletion(
    request: Request,
    language: str = Query(default="fa", description="Response language"),
    current_user: dict = Depends(get_current_user),
    redis: Redis = Depends(get_redis_client)
):
    """
    درخواست حذف حساب کاربری توسط کاربر احراز شده
    """
    try:
        return await request_account_deletion_service(
            user_id=current_user["user_id"],
            role=current_user.get("role"),
            client_ip=request.client.host,
            language=language,
            redis=redis
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_message("server.error", language)
        )
