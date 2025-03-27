from fastapi import Request, HTTPException, status, Depends
from redis.asyncio import Redis
from bson import ObjectId

from common.logging.logger import log_info, log_error
from infrastructure.database.mongodb.mongo_client import find_one
from infrastructure.database.redis.operations.get import get
from infrastructure.database.redis.redis_client import get_redis_client
from .decode import decode_token


def get_token_from_header(request: Request) -> str:
    """
    Extracts the Bearer token from the Authorization header.
    """
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header missing or invalid")
    return auth.split(" ")[1]


async def get_current_user(
    request: Request,
    redis: Redis = Depends(get_redis_client)
) -> dict:
    """
    Extract user from access token: validate JWT, session, and user existence.
    """
    token = get_token_from_header(request)

    try:
        # 🔐 Decode the access token
        payload = await decode_token(token, token_type="access", redis=redis)

        user_id = payload.get("sub")
        role = payload.get("role")
        session_id = payload.get("session_id")
        jti = payload.get("jti")

        if not all([user_id, role, session_id, jti]):
            log_error("Incomplete JWT payload", extra={"payload": payload})
            raise HTTPException(status_code=401, detail="Invalid token structure")

        # ❌ Check blacklist
        if await get(f"blacklist:{jti}", redis):
            log_error("Revoked token used", extra={"jti": jti, "user_id": user_id})
            raise HTTPException(status_code=401, detail="Token is revoked")

        # 📦 Validate session
        session_key = f"sessions:{user_id}:{session_id}"
        if not await get(session_key, redis):
            log_error("Missing session", extra={"user_id": user_id, "session_id": session_id})
            raise HTTPException(status_code=401, detail="Session not found or expired")

        # 🧾 Fetch user from database
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
