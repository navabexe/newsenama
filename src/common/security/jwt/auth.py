from fastapi import Request, HTTPException, Depends
from redis.asyncio import Redis
from bson import ObjectId

from common.logging.logger import log_info, log_error
from infrastructure.database.mongodb.mongo_client import find_one
from infrastructure.database.redis.operations.get import get
from infrastructure.database.redis.redis_client import get_redis_client
from .decode import decode_token


def get_token_from_header(request: Request) -> str:
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header missing or invalid")
    return auth.split(" ")[1]


async def get_current_user(
    request: Request,
    redis: Redis = Depends(get_redis_client)
) -> dict:
    token = get_token_from_header(request)

    try:
        payload = await decode_token(token, token_type="access", redis=redis)

        user_id = payload.get("sub")
        role = payload.get("role")
        session_id = payload.get("session_id")
        jti = payload.get("jti")

        if not all([user_id, role, session_id, jti]):
            log_error("Incomplete JWT payload", extra={"payload": payload})
            raise HTTPException(status_code=401, detail="Invalid token structure")

        # ✅ بررسی کلید blacklist
        blacklist_key = f"blacklist:{jti}"
        key_type = await redis.type(blacklist_key)
        if key_type not in [b'string', b'none']:
            await redis.delete(blacklist_key)
        if await get(blacklist_key, redis):
            log_error("Revoked token used", extra={"jti": jti, "user_id": user_id})
            raise HTTPException(status_code=401, detail="Token is revoked")

        # ✅ بررسی session key دقیق‌تر
        session_key = f"sessions:{user_id}:{session_id}"
        key_type = await redis.type(session_key)
        key_type_str = key_type.decode() if isinstance(key_type, bytes) else str(key_type)

        if key_type_str == "none":
            log_info("Session key not found", extra={"key": session_key})
            raise HTTPException(status_code=401, detail="Session not found")

        if key_type_str != "hash":
            await redis.delete(session_key)
            log_error("Invalid session key type", extra={"key": session_key, "type": key_type_str})
            raise HTTPException(status_code=401, detail="Invalid session type")

        session_data = await redis.hgetall(session_key)
        if not session_data:
            log_error("Empty session", extra={"key": session_key})
            raise HTTPException(status_code=401, detail="Session is empty or expired")

        # 🧾 دریافت اطلاعات کاربر
        collection = (
            "admins" if role == "admin"
            else "vendors" if role == "vendor"
            else "users"
        )

        user = await find_one(collection, {"_id": ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        if user.get("status") != "active":
            raise HTTPException(
                status_code=403,
                detail=f"Account not active (status: {user.get('status')})"
            )

        log_info("User authorized", extra={"user_id": user_id, "role": role, "session_id": session_id})

        return {
            "user_id": user_id,
            "role": role,
            "session_id": session_id
        }

    except HTTPException:
        raise
    except Exception as e:
        log_error("Token authentication failed", extra={"error": str(e)})
        raise HTTPException(status_code=401, detail="Authentication failed")
