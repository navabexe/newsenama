from datetime import datetime, timezone
from fastapi import HTTPException, Request
from redis.asyncio import Redis
from common.security.jwt_handler import decode_token, generate_access_token, generate_refresh_token, revoke_token
from common.translations.messages import get_message
from common.logging.logger import log_info, log_error
from infrastructure.database.mongodb.repository import MongoRepository
from common.config.settings import settings
from infrastructure.database.redis.operations.redis_operations import get, delete, hset, expire


async def refresh_tokens(
    request: Request,
    refresh_token: str,
    redis: Redis,
    users_repo: MongoRepository,
    vendors_repo: MongoRepository,
    language: str = "fa"
):
    client_ip = request.client.host

    payload = await decode_token(token=refresh_token, token_type="refresh", redis=redis)

    user_id = payload.get("sub")
    role = payload.get("role")
    old_jti = payload.get("jti")
    session_id = payload.get("session_id")
    scopes = payload.get("scopes", [])
    language = language or payload.get("language", "fa")

    if not all([user_id, role, old_jti, session_id]):
        log_error("Malformed refresh token", extra={"payload": payload, "ip": client_ip})
        raise HTTPException(status_code=400, detail=get_message("token.invalid", language))

    redis_key = f"refresh_tokens:{user_id}:{old_jti}"
    redis_value = await get(redis_key, redis=redis)
    if not redis_value:
        log_error("Refresh token not found or reused", extra={"user_id": user_id, "jti": old_jti, "ip": client_ip})
        raise HTTPException(status_code=401, detail=get_message("token.expired", language))

    # Revoke old token
    await delete(redis_key, redis=redis)
    await revoke_token(old_jti, ttl=7 * 24 * 60 * 60, redis=redis)

    # Get user info
    status = None
    phone_verified = None
    user_profile = None
    vendor_profile = None

    if role == "vendor":
        vendor = await vendors_repo.find_one({"_id": user_id})
        if vendor:
            status = vendor.get("status")
            phone_verified = vendor.get("phone_verified", False)
            vendor_profile = vendor
    elif role == "user":
        user = await users_repo.find_one({"_id": user_id})
        if user:
            status = user.get("status")
            phone_verified = user.get("phone_verified", False)
            user_profile = user

    # Generate new tokens
    access_token = await generate_access_token(
        user_id=user_id,
        role=role,
        session_id=session_id,
        scopes=scopes,
        status=status,
        phone_verified=phone_verified,
        user_profile=user_profile,
        vendor_profile=vendor_profile,
        language=language
    )

    refresh_token, new_jti = await generate_refresh_token(
        user_id=user_id,
        role=role,
        session_id=session_id,
        status=status,
        language=language,
        return_jti=True
    )

    # Save new refresh token in Redis
    refresh_key = f"refresh_tokens:{user_id}:{new_jti}"
    await redis.setex(refresh_key, settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60, "active")
    log_info("Stored new refresh token in Redis", extra={"key": refresh_key})

    # Update session info
    session_key = f"sessions:{user_id}:{session_id}"
    session_data = {
        "ip": client_ip,
        "last_refreshed": datetime.now(timezone.utc).isoformat()
    }
    await hset(session_key, mapping=session_data, redis=redis)
    await expire(session_key, 86400, redis=redis)

    log_info("Tokens refreshed successfully", extra={"user_id": user_id, "session_id": session_id, "role": role, "ip": client_ip})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "message": get_message("token.refreshed", language),
        "status": "refreshed"
    }
