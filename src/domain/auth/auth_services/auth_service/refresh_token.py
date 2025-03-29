from datetime import datetime, timezone

from fastapi import HTTPException
from redis.asyncio import Redis

from common.logging.logger import log_info, log_error
from common.security.jwt.decode import decode_token as decode_refresh_token
from common.security.jwt.revoke import revoke_token
from common.security.jwt.tokens import generate_access_token, generate_refresh_token
from common.translations.messages import get_message
from infrastructure.database.redis.operations.delete import delete
from infrastructure.database.redis.operations.expire import expire
from infrastructure.database.redis.operations.get import get
from infrastructure.database.redis.operations.hset import hset
from infrastructure.database.mongodb.mongo_client import find_one


async def refresh_token_service(
    refresh_token: str,
    client_ip: str,
    language: str = "fa",
    redis: Redis = None
) -> dict:
    try:
        if redis is None:
            from infrastructure.database.redis.redis_client import get_redis_client
            redis = await get_redis_client()

        payload = await decode_refresh_token(refresh_token, token_type="refresh", redis=redis)

        user_id = payload.get("sub")
        role = payload.get("role")
        old_jti = payload.get("jti")
        session_id = payload.get("session_id")
        scopes = payload.get("scopes", [])

        if not all([user_id, role, old_jti, session_id]):
            raise HTTPException(status_code=400, detail=get_message("token.invalid", language))

        redis_key = f"refresh_tokens:{user_id}:{old_jti}"
        if not await get(redis_key, redis):
            raise HTTPException(status_code=401, detail=get_message("token.expired", language))

        #  Revoke old refresh token
        await delete(redis_key, redis)
        await revoke_token(old_jti, ttl=7 * 24 * 60 * 60, redis=redis)

        #  Load user or vendor profile
        collection = "vendors" if role == "vendor" else "users"
        user_data = await find_one(collection, {"_id": user_id})
        if not user_data:
            raise HTTPException(status_code=404, detail=get_message("user.not_found", language))

        #  Generate new tokens
        access_token = await generate_access_token(
            user_id=user_id,
            role=role,
            session_id=session_id,
            scopes=scopes,
            language=language,
            user_profile=user_data if role == "user" else None,
            vendor_profile=user_data if role == "vendor" else None,
        )

        new_refresh_token = await generate_refresh_token(
            user_id=user_id,
            role=role,
            session_id=session_id,
        )

        # ️ Update session info
        await hset(f"sessions:{user_id}:{session_id}", mapping={
            "ip": client_ip,
            "last_refreshed": datetime.now(timezone.utc).isoformat()
        }, redis=redis)
        await expire(f"sessions:{user_id}:{session_id}", 86400, redis=redis)

        log_info("Tokens refreshed via service", extra={
            "user_id": user_id,
            "role": role,
            "session_id": session_id,
            "ip": client_ip
        })

        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "message": get_message("token.refreshed", language),
            "status": "refreshed"
        }

    except HTTPException:
        raise
    except Exception as e:
        log_error("Refresh token service failed", extra={"error": str(e), "ip": client_ip}, exc_info=True)
        raise HTTPException(status_code=500, detail=get_message("server.error", language))
