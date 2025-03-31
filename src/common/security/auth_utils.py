# File: common/security/auth_utils.py
from fastapi import HTTPException, Request, Depends
from jose import JWTError, jwt
from redis.asyncio import Redis
from typing import Dict

from common.config.settings import settings
from common.logging.logger import log_warning, log_error, log_info
from infrastructure.database.redis.redis_client import get_redis_client
from infrastructure.database.redis.operations.delete import delete
from infrastructure.database.redis.operations.expire import expire
from infrastructure.database.redis.operations.get import get
from infrastructure.database.redis.operations.incr import incr
from infrastructure.database.redis.operations.keys import keys

RATE_LIMIT_CONFIG = [
    {"limit": 3, "window": 60},    # 3 requests per minute
    {"limit": 5, "window": 600},   # 5 requests per 10 minutes
    {"limit": 10, "window": 3600}, # 10 requests per hour
]
MAX_REFRESH_TOKENS = 5

async def get_redis(redis: Redis = Depends(get_redis_client)) -> Redis:
    """Dependency to provide Redis client."""
    return redis

def decode_jwt(token: str) -> Dict:
    """
    Decode a JWT token using the access secret.

    Args:
        token (str): JWT token to decode.

    Returns:
        Dict: Decoded token payload.

    Raises:
        HTTPException: If token is invalid or expired.
    """
    try:
        payload = jwt.decode(token, settings.ACCESS_SECRET, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as e:
        log_warning("JWT decode failed", extra={"error": str(e)})
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def get_token_from_header(request: Request) -> str:
    """
    Extract the Bearer token from the Authorization header.

    Args:
        request (Request): FastAPI request object.

    Returns:
        str: Extracted token.

    Raises:
        HTTPException: If header is missing or invalid.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header missing or invalid")
    return auth_header.split(" ")[1]

async def get_current_user(request: Request, redis: Redis = Depends(get_redis)) -> Dict:
    """
    Retrieve the current user's payload from the request token.

    Args:
        request (Request): FastAPI request object.
        redis (Redis): Redis client instance.

    Returns:
        Dict: Decoded token payload.

    Raises:
        HTTPException: If token or session is invalid or revoked.
    """
    token = get_token_from_header(request)
    payload = decode_jwt(token)

    jti = payload.get("jti")
    user_id = payload.get("sub")
    role = payload.get("role")
    session_id = payload.get("session_id")

    if not all([user_id, role, session_id]):
        raise HTTPException(status_code=401, detail="Token payload missing required fields")

    if jti and await get(f"token:blacklist:{jti}", redis):
        raise HTTPException(status_code=401, detail="Token is blacklisted")
    if await get(f"token:blacklist:user:{user_id}", redis):
        raise HTTPException(status_code=401, detail="User sessions are revoked")

    session_key = f"sessions:{user_id}:{session_id}"
    if not await get(session_key, redis):
        log_error("Invalid session", extra={"user_id": user_id, "session_id": session_id})
        raise HTTPException(status_code=401, detail="Session is no longer valid")

    return payload

async def check_rate_limits(key_prefix: str, redis: Redis = Depends(get_redis)) -> None:
    """
    Enforce rate limiting based on predefined configurations.

    Args:
        key_prefix (str): Prefix for the rate limit key (e.g., user ID or IP).
        redis (Redis): Redis client instance.

    Raises:
        HTTPException: If rate limit is exceeded.
    """
    for cfg in RATE_LIMIT_CONFIG:
        key = f"ratelimit:{key_prefix}:{cfg['window']}"
        attempts = await get(key, redis)
        if attempts and int(attempts) >= cfg["limit"]:
            raise HTTPException(status_code=429, detail="Too many requests. Try again later.")
        await incr(key, redis)
        await expire(key, cfg["window"], redis)

async def enforce_refresh_token_limit(user_id: str, redis: Redis = Depends(get_redis)) -> None:
    """
    Limit the number of active refresh tokens for a user.

    Args:
        user_id (str): User identifier.
        redis (Redis): Redis client instance.
    """
    try:
        all_keys = await keys(f"refresh_tokens:{user_id}:*", redis)
        if len(all_keys) > MAX_REFRESH_TOKENS:
            oldest_keys = sorted(all_keys)[:-MAX_REFRESH_TOKENS]
            for key in oldest_keys:
                await delete(key, redis)
                log_info("Old refresh token removed", extra={"user_id": user_id, "key": key})
    except Exception as e:
        log_error("Failed to enforce refresh token limit", extra={"user_id": user_id, "error": str(e)})