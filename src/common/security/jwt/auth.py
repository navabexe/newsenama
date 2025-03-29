from fastapi import Request, HTTPException, Depends
from redis.asyncio import Redis
from bson import ObjectId

from common.logging.logger import log_info, log_error
from domain.auth.entities.token_entity import TokenPayload
from infrastructure.database.mongodb.mongo_client import find_one
from infrastructure.database.redis.redis_client import get_redis_client
from common.security.jwt.decode import decode_token


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
        payload_dict = await decode_token(token, token_type="access", redis=redis)

        # 🧠 Validate payload structure with TokenPayload
        try:
            token_data = TokenPayload(**payload_dict)
        except Exception as e:
            log_error("Invalid token structure", extra={"error": str(e)})
            raise HTTPException(status_code=401, detail="Invalid token structure")

        # 🧾 دریافت اطلاعات کاربر از DB
        collection = (
            "admins" if token_data.role == "admin"
            else "vendors" if token_data.role == "vendor"
            else "users"
        )

        user = await find_one(
            collection,
            {"_id": ObjectId(token_data.sub) if ObjectId.is_valid(token_data.sub) else token_data.sub}
        )

        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        if user.get("status") != "active":
            raise HTTPException(
                status_code=403,
                detail=f"Account not active (status: {user.get('status')})"
            )

        log_info("User authorized", extra={
            "user_id": token_data.sub,
            "role": token_data.role,
            "session_id": token_data.session_id
        })

        return {
            "user_id": token_data.sub,
            "role": token_data.role,
            "session_id": token_data.session_id
        }

    except HTTPException:
        raise
    except Exception as e:
        log_error("Token authentication failed", extra={"error": str(e)})
        raise HTTPException(status_code=401, detail="Authentication failed")
