# File: common/security/jwt/auth.py
from fastapi import Request, HTTPException, Depends
from redis.asyncio import Redis
from bson import ObjectId

from common.logging.logger import log_info, log_error
from domain.auth.entities.token_entity import TokenPayload
from infrastructure.database.mongodb.mongo_client import find_one
from infrastructure.database.redis.redis_client import get_redis_client
from common.security.jwt.decode import decode_token

async def get_redis(redis: Redis = Depends(get_redis_client)) -> Redis:
    return redis

def get_token_from_header(request: Request) -> str:
    """Extract and validate the Bearer token from the Authorization header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    return auth_header.split(" ")[1]

async def fetch_user_from_db(collection: str, user_id: str) -> dict:
    """Fetch user data from MongoDB based on collection and user ID."""
    query_id = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
    user = await find_one(collection, {"_id": query_id})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if user.get("status") != "active":
        raise HTTPException(
            status_code=403,
            detail=f"Account not active (status: {user.get('status')})"
        )
    return user

async def get_current_user(
    request: Request,
    redis: Redis = Depends(get_redis),
) -> dict:
    """Authenticate and return the current user based on the provided token."""
    token = get_token_from_header(request)

    try:
        payload_dict = await decode_token(token, token_type="access", redis=redis)
        token_data = TokenPayload(**payload_dict)

        collection_map = {
            "admin": "admins",
            "vendor": "vendors",
        }
        collection = collection_map.get(token_data.role, "users")

        await fetch_user_from_db(collection, token_data.sub)

        log_info("User authorized", extra={
            "user_id": token_data.sub,
            "role": token_data.role,
            "session_id": token_data.session_id,
        })

        return {
            "user_id": token_data.sub,
            "role": token_data.role,
            "session_id": token_data.session_id,
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        log_error("Token authentication failed", extra={"error": str(e)})
        raise HTTPException(status_code=401, detail="Authentication failed")