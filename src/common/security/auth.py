from fastapi import HTTPException, Request
from jose import JWTError, jwt

from common.config.settings import settings
from common.logging.logger import log_warning, log_error, log_info
from infrastructure.database.redis.operations.delete import delete
from infrastructure.database.redis.operations.expire import expire
from infrastructure.database.redis.operations.get import get
from infrastructure.database.redis.operations.incr import incr
from infrastructure.database.redis.operations.keys import keys

ACCESS_SECRET = settings.ACCESS_SECRET
ALGORITHM = settings.ALGORITHM

RATE_LIMIT_CONFIG = [
    {"limit": 3, "window": 60},      # 3 requests per minute
    {"limit": 5, "window": 600},     # 5 requests per 10 minutes
    {"limit": 10, "window": 3600}    # 10 requests per hour
]

MAX_REFRESH_TOKENS = 5

def decode_jwt(token: str):
    try:
        payload = jwt.decode(token, ACCESS_SECRET, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        log_warning("JWT decode failed", extra={"error": str(e)})
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def get_token_from_header(request: Request) -> str:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header missing or invalid")
    return auth_header.split(" ")[1]

async def get_current_user(request: Request) -> dict:
    token = get_token_from_header(request)
    payload = decode_jwt(token)

    jti = payload.get("jti")
    user_id = payload.get("sub")
    role = payload.get("role")
    session_id = payload.get("session_id")

    if not user_id or not role or not session_id:
        raise HTTPException(status_code=401, detail="Token payload invalid")

    if jti and await get(f"token:blacklist:{jti}"):
        raise HTTPException(status_code=401, detail="Token is blacklisted")

    if await get(f"token:blacklist:user:{user_id}"):
        raise HTTPException(status_code=401, detail="User sessions are revoked")

    session_key = f"sessions:{user_id}:{session_id}"
    if not await get(session_key):
        log_error("Invalid session", extra={"user_id": user_id, "session_id": session_id})
        raise HTTPException(status_code=401, detail="Session is no longer valid")

    return payload


async def check_rate_limits(key_prefix: str):
    for cfg in RATE_LIMIT_CONFIG:
        key = f"{key_prefix}:{cfg['window']}"
        attempts = await get(key)
        if attempts and int(attempts) >= cfg["limit"]:
            raise HTTPException(
                status_code=429,
                detail=f"Too many requests. Try again later."
            )
        await incr(key)
        await expire(key, cfg["window"])


async def enforce_refresh_token_limit(user_id: str):
    try:
        all_keys = await keys(f"refresh_tokens:{user_id}:*")
        if len(all_keys) > MAX_REFRESH_TOKENS:
            oldest_keys = sorted(all_keys)[:-MAX_REFRESH_TOKENS]
            for key in oldest_keys:
                await delete(key)
                log_info("Old refresh token removed", extra={"user_id": user_id, "key": key})
    except Exception as e:
        log_error("Failed to enforce refresh token limit", extra={"user_id": user_id, "error": str(e)})