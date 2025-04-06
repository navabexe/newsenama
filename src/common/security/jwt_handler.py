"""
JWT Handler Module

This file merges all JWT-related logic: generation, decoding, revocation, authentication, and custom errors.
Useful for centralized import and easier maintenance.
"""

# ========== Imports ==========
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from typing import Optional, List, Union, Tuple
from jose import jwt, ExpiredSignatureError, JWTError as JoseJWTError
from fastapi import Request, HTTPException, Depends
from redis.asyncio import Redis
from pydantic import ValidationError
from bson import ObjectId

from common.config.settings import settings
from common.logging.logger import log_info, log_error
from infrastructure.database.mongodb.mongo_client import find_one
from infrastructure.database.redis.redis_client import get_redis_client
from infrastructure.database.redis.operations.redis_operations import delete, keys, setex, get

from domain.auth.entities.token_entity import TokenPayload

# ========== Error Classes ==========

class JWTError(Exception):
    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class TokenRevokedError(JWTError):
    def __init__(self, jti: str):
        super().__init__(f"Token with jti '{jti}' has been revoked", status_code=401)

class TokenTypeMismatchError(JWTError):
    def __init__(self, expected: str, actual: str):
        super().__init__(f"Token type mismatch: expected '{expected}', got '{actual}'", status_code=401)


# ========== Token Utility Functions ==========

def generate_jti() -> str:
    return str(uuid4())

def get_timestamps(expires_in_minutes: int = 0, expires_in_days: int = 0) -> tuple[int, int]:
    now = datetime.now(timezone.utc)
    iat = int(now.timestamp())
    exp = int((now + timedelta(minutes=expires_in_minutes, days=expires_in_days)).timestamp())
    return iat, exp

# ========== Token Generators ==========

from common.security.jwt.payload_builder import build_jwt_payload

async def generate_access_token(
    user_id: str,
    role: str,
    session_id: str,
    user_profile: Optional[dict] = None,
    vendor_profile: Optional[dict] = None,
    scopes: Optional[List[str]] = None,
    language: str = "fa",
    vendor_id: Optional[str] = None,
    amr: Optional[List[str]] = None,
    status: Optional[str] = None,
    phone_verified: Optional[bool] = None
) -> str:

    log_info("Starting generate_access_token", extra={
        "user_id": user_id,
        "role": role,
        "session_id": session_id,
        "scopes": scopes,
        "language": language,
        "status": status,
        "phone_verified": phone_verified,
        "user_profile": user_profile,
        "vendor_profile": vendor_profile,
        "vendor_id": vendor_id,
        "amr": amr
    })

    base_profile = user_profile if role == "user" else vendor_profile if role == "vendor" else None
    status = status or (base_profile.get("status") if base_profile else None)
    phone = base_profile.get("phone") if base_profile else None
    phone_verified = phone_verified if phone_verified is not None else (base_profile.get("phone_verified") if base_profile else None)

    payload = build_jwt_payload(
        token_type="access",
        role=role,
        subject_id=user_id,
        session_id=session_id,
        scopes=scopes,
        language=language,
        status=status,
        phone=phone,
        phone_verified=phone_verified,
        user_data=user_profile if role == "user" else None,
        vendor_data=vendor_profile if role == "vendor" else None,
        vendor_id=vendor_id,
        amr=amr,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

    token = jwt.encode(payload, settings.ACCESS_SECRET, algorithm=settings.ALGORITHM)
    log_info("Access token generated", extra={"jti": payload["jti"], "user_id": user_id})
    return token


async def generate_temp_token(
    phone: str,
    role: str,
    jti: str,
    status: str = "incomplete",
    phone_verified: bool = False,
    language: str = "fa"
) -> str:
    payload = build_jwt_payload(
        token_type="temp",
        role=role,
        subject_id=phone,
        phone=phone,
        jti=jti,
        language=language,
        status=status,
        phone_verified=phone_verified,
        expires_in=settings.TEMP_TOKEN_EXPIRE_MINUTES * 60,
    )

    token = jwt.encode(payload, settings.ACCESS_SECRET, algorithm=settings.ALGORITHM)
    log_info("Temporary token generated", extra={"jti": jti, "phone": phone})
    return token


async def generate_refresh_token(
    user_id: str,
    role: str,
    session_id: str,
    status: Optional[str] = None,
    language: str = "fa",
    return_jti: bool = False
) -> Union[str, Tuple[str, str]]:
    payload = build_jwt_payload(
        token_type="refresh",
        role=role,
        subject_id=user_id,
        session_id=session_id,
        status=status,
        language=language,
        expires_in=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )

    token = jwt.encode(payload, settings.REFRESH_SECRET, algorithm=settings.ALGORITHM)
    log_info("Refresh token generated", extra={"jti": payload["jti"], "user_id": user_id})

    return (token, payload["jti"]) if return_jti else token


# ========== Revoke Token ==========

async def revoke_token(
    jti: str,
    ttl: int,
    redis: Redis = Depends(get_redis_client)
) -> None:
    """
    Revoke a specific token by adding it to the Redis blacklist.
    """
    try:
        effective_ttl = max(ttl, settings.ACCESS_TTL)
        blacklist_key = f"blacklist:{jti}"
        await setex(blacklist_key, effective_ttl, "revoked", redis)
        log_info("Token revoked", extra={"jti": jti, "ttl": effective_ttl})
    except Exception as e:
        log_error("Token revocation failed", extra={"jti": jti, "error": str(e)})
        raise JWTError(f"Failed to revoke token: {str(e)}")


async def revoke_all_user_tokens(
    user_id: str,
    redis: Redis = Depends(get_redis_client)
) -> None:
    """
    Revoke all tokens and sessions associated with a user.
    """
    try:
        # Revoke all refresh tokens
        refresh_pattern = f"refresh_tokens:{user_id}:*"
        refresh_keys = await keys(refresh_pattern, redis)
        for key in refresh_keys:
            jti = key.split(":")[-1]
            await delete(key, redis)
            await setex(f"blacklist:{jti}", settings.REFRESH_TTL, "revoked", redis)
            log_info("Refresh token revoked", extra={"user_id": user_id, "jti": jti})

        # Remove all sessions
        session_pattern = f"sessions:{user_id}:*"
        session_keys = await keys(session_pattern, redis)
        for key in session_keys:
            await delete(key, redis)
            log_info("Session removed", extra={"user_id": user_id, "key": key})

    except Exception as e:
        log_error("Revoke all tokens failed", extra={"user_id": user_id, "error": str(e)})
        raise JWTError(f"Failed to revoke all tokens: {str(e)}")


# ========== Decode Token ==========

AUDIENCE_MAP = {
    "access": "api",
    "refresh": "auth-service",
    "temp": "auth-temp",
}

async def validate_token_blacklist(jti: str, redis: Redis):
    """Check if the token is blacklisted in Redis."""
    blacklist_key = f"blacklist:{jti}"
    blacklist_value = await get(blacklist_key, redis)
    log_info("Checking token blacklist", extra={"key": blacklist_key, "value": blacklist_value})
    if blacklist_value:
        log_error("Token revoked", extra={"jti": jti})
        raise TokenRevokedError(jti)


async def check_refresh_token_reuse(user_id: str, jti: str, redis: Redis):
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
    redis: Redis = Depends(get_redis_client),
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


# ========== Auth ==========

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
    redis: Redis = Depends(get_redis_client),
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
