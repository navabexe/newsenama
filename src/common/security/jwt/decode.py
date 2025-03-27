from jose import jwt, ExpiredSignatureError, JWTError as JoseJWTError
from fastapi import HTTPException
from redis.asyncio import Redis

from common.config.settings import settings
from common.logging.logger import log_error, log_info
from infrastructure.database.redis.operations.get import get
from .errors import JWTError
from .revoke import revoke_all_user_tokens


AUDIENCE_MAP = {
    "access": "api",
    "refresh": "auth-service",
    "temp": "auth-temp"
}


async def decode_token(
    token: str,
    token_type: str = "access",
    redis: Redis = None
) -> dict:
    """
    Decode and validate a JWT token based on its type and Redis blacklist.

    Returns:
        dict: Decoded payload

    Raises:
        HTTPException: On token error or revocation.
    """
    try:
        if redis is None:
            from infrastructure.database.redis.redis_client import get_redis_client
            redis = await get_redis_client()

        secret = settings.ACCESS_SECRET if token_type in ["access", "temp"] else settings.REFRESH_SECRET
        expected_aud = AUDIENCE_MAP.get(token_type)

        payload = jwt.decode(
            token,
            secret,
            algorithms=[settings.ALGORITHM],
            audience=expected_aud
        )

        # Validate type from inside token
        actual_type = payload.get("token_type")
        if actual_type != token_type:
            log_error("Token type mismatch", extra={"expected": token_type, "actual": actual_type})
            raise HTTPException(status_code=401, detail="Token type mismatch")

        jti = payload.get("jti")
        if not jti:
            raise JWTError("Token missing jti")

        # Check blacklist
        if await get(f"blacklist:{jti}", redis):
            log_error("Token revoked", extra={"jti": jti, "type": token_type})
            raise HTTPException(status_code=401, detail="Token revoked")

        # Refresh token reuse detection
        if token_type == "refresh":
            user_id = payload.get("sub")
            redis_key = f"refresh_tokens:{user_id}:{jti}"
            if not await get(redis_key, redis):
                await revoke_all_user_tokens(user_id, redis)
                log_error("Refresh token reuse detected", extra={"user_id": user_id, "jti": jti})
                raise HTTPException(status_code=401, detail="Refresh token reuse detected")

        log_info("Token decoded", extra={"jti": jti, "type": token_type})
        return payload

    except ExpiredSignatureError:
        log_error("Token expired", extra={"token_type": token_type})
        raise HTTPException(status_code=401, detail="Token expired")

    except JoseJWTError as e:
        log_error("Invalid token", extra={"token_type": token_type, "error": str(e)})
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

    except Exception as e:
        log_error("Decode failed", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to decode token")
