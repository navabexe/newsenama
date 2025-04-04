from jose import jwt, ExpiredSignatureError, JWTError as JoseJWTError
from fastapi import HTTPException, Depends
from redis.asyncio import Redis
from pydantic import ValidationError

from common.config.settings import settings
from common.logging.logger import log_info, log_error
from infrastructure.database.redis.operations.get import get
from infrastructure.database.redis.redis_client import get_redis_client
from .errors import JWTError, TokenRevokedError, TokenTypeMismatchError
from .revoke import revoke_all_user_tokens
from domain.auth.entities.token_entity import TokenPayload

async def get_redis(redis: Redis = Depends(get_redis_client)) -> Redis:
    """Dependency to provide Redis client."""
    log_info("Redis client dependency resolved")
    return redis

AUDIENCE_MAP = {
    "access": "api",
    "refresh": "auth-service",
    "temp": "auth-temp",
}

async def validate_token_blacklist(jti: str, redis: Redis) -> None:
    """Check if the token is blacklisted in Redis."""
    blacklist_key = f"blacklist:{jti}"
    blacklist_value = await get(blacklist_key, redis)
    log_info("Checking token blacklist", extra={"key": blacklist_key, "value": blacklist_value})
    if blacklist_value:
        log_error("Token revoked", extra={"jti": jti})
        raise TokenRevokedError(jti)

async def check_refresh_token_reuse(user_id: str, jti: str, redis: Redis) -> None:
    """Detect reuse of refresh tokens and revoke all tokens if detected."""
    redis_key = f"refresh_tokens:{user_id}:{jti}"
    redis_value = await get(redis_key, redis)
    log_info("Checking refresh token reuse", extra={"key": redis_key, "value": redis_value})
    if not redis_value:
        log_error("Refresh token reuse detected", extra={"user_id": user_id, "jti": jti})
        await revoke_all_user_tokens(user_id, redis)
        raise HTTPException(status_code=401, detail="Refresh token reuse detected")

async def decode_token(
    token: str,
    token_type: str = "access",
    redis: Redis = Depends(get_redis),
) -> dict:
    """
    Decode and validate a JWT token based on its type and blacklist status.
    """
    log_info("Starting token decode", extra={"token_type": token_type, "token_prefix": token[:10] + "..."})

    try:
        # Determine secret and audience
        secret = settings.ACCESS_SECRET if token_type in ["access", "temp"] else settings.REFRESH_SECRET
        expected_aud = AUDIENCE_MAP.get(token_type)
        log_info("Using secret and audience", extra={
            "secret": secret[:10] + "...",
            "audience": expected_aud
        })

        # Decode JWT
        payload = jwt.decode(
            token,
            secret,
            algorithms=[settings.ALGORITHM],
            audience=expected_aud,
        )
        log_info("JWT decoded", extra={"payload": payload})

        # Validate token structure
        TokenPayload(**payload)
        log_info("Token payload validated with TokenPayload model")

        # Check token type
        actual_type = payload.get("token_type")
        if actual_type != token_type:
            log_error("Token type mismatch", extra={"expected": token_type, "actual": actual_type})
            raise TokenTypeMismatchError(expected=token_type, actual=actual_type)

        # Check required claims
        jti = payload.get("jti")
        if not jti:
            log_error("Missing JTI in token")
            raise JWTError("Token missing required 'jti' claim")

        # Validate blacklist
        await validate_token_blacklist(jti, redis)

        # Check refresh token reuse
        if token_type == "refresh":
            user_id = payload.get("sub")
            log_info("Checking refresh token reuse for user", extra={"user_id": user_id})
            await check_refresh_token_reuse(user_id, jti, redis)

        log_info("Token decoded successfully", extra={"jti": jti, "type": token_type})
        return payload

    except ExpiredSignatureError:
        log_error("Token expired", extra={"token_type": token_type})
        raise HTTPException(status_code=401, detail="Token expired")
    except JoseJWTError as e:
        log_error("Invalid token", extra={"token_type": token_type, "error": str(e)})
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except ValidationError as ve:
        log_error("Invalid JWT payload structure", extra={"errors": ve.errors()})
        raise HTTPException(status_code=401, detail="Invalid token payload structure")
    except Exception as e:
        log_error("Decode failed", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to decode token")