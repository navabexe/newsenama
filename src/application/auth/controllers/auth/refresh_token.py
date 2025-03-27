from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status, Request, Depends
from pydantic import BaseModel, Field, ConfigDict
from redis.asyncio import Redis

from common.logging.logger import log_info, log_error
from common.translations.messages import get_message
from common.security.jwt_handler import decode_token, generate_access_token, generate_refresh_token, revoke_token
from infrastructure.database.redis.operations.delete import delete
from infrastructure.database.redis.operations.get import get
from infrastructure.database.redis.operations.hset import hset
from infrastructure.database.redis.redis_client import get_redis_client

router = APIRouter()


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=10, description="Valid refresh token")
    language: str = Field(default="fa", description="Response language")

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid"
    )


@router.post("/refresh-token", status_code=status.HTTP_200_OK)
async def refresh_token_endpoint(
    data: RefreshTokenRequest,
    request: Request,
    redis: Redis = Depends(get_redis_client)
):
    """
     دریافت دوباره‌ی access/refresh token از طریق refresh token

    - اگر token معتبر و بازنویسی‌نشده باشد، access جدید و refresh جدید صادر می‌شود.
    """
    client_ip = request.client.host
    try:
        payload = await decode_token(data.refresh_token, token_type="refresh", redis=redis)

        user_id = payload.get("sub")
        role = payload.get("role")
        old_jti = payload.get("jti")
        session_id = payload.get("session_id")
        scopes = payload.get("scopes", [])
        language = data.language

        if not all([user_id, role, old_jti, session_id]):
            log_error("Malformed refresh token", extra={"payload": payload})
            raise HTTPException(status_code=400, detail=get_message("token.invalid", language))

        redis_key = f"refresh_tokens:{user_id}:{old_jti}"
        if not await get(redis_key, redis):
            log_error("Refresh token not found or reused", extra={
                "user_id": user_id,
                "jti": old_jti,
                "ip": client_ip
            })
            raise HTTPException(status_code=401, detail=get_message("token.expired", language))

        # Revoke old token
        await delete(redis_key, redis)
        await revoke_token(old_jti, ttl=7 * 24 * 60 * 60, redis=redis)

        # Generate new tokens
        access_token = await generate_access_token(
            user_id=user_id,
            role=role,
            session_id=session_id,
            scopes=scopes,
            redis=redis
        )

        refresh_token = await generate_refresh_token(
            user_id=user_id,
            role=role,
            session_id=session_id,
            redis=redis
        )

        # Update session last_refreshed
        await hset(f"sessions:{user_id}:{session_id}", mapping={
            "ip": client_ip,
            "last_refreshed": datetime.now(timezone.utc).isoformat()
        }, redis=redis)

        log_info("Tokens refreshed", extra={
            "user_id": user_id,
            "session_id": session_id,
            "role": role,
            "ip": client_ip
        })

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "message": get_message("token.refreshed", language),
            "status": "refreshed"
        }

    except HTTPException:
        raise
    except Exception as e:
        log_error("Token refresh failed", extra={"error": str(e), "ip": client_ip}, exc_info=True)
        raise HTTPException(status_code=500, detail=get_message("server.error", data.language))
