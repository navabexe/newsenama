# File: common/security/jwt/tokens.py

from datetime import datetime, timedelta, timezone
from uuid import uuid4
from jose import jwt
from redis.asyncio import Redis

from common.config.settings import settings

# Constants
JWT_SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS
TEMP_TOKEN_EXPIRE_MINUTES = settings.TEMP_TOKEN_EXPIRE_MINUTES


def new_jti() -> str:
    """Generate a new unique JWT ID"""
    return str(uuid4())


def timestamp(minutes: int = 0, days: int = 0) -> tuple[int, int]:
    """Return (iat, exp) timestamps"""
    iat = int(datetime.now(timezone.utc).timestamp())
    exp = int((datetime.now(timezone.utc) + timedelta(minutes=minutes, days=days)).timestamp())
    return iat, exp


async def generate_access_token(
    user_id: str,
    role: str,
    session_id: str,
    scopes: list[str] = None,
    user_profile: dict = None,
    language: str = "fa",
) -> str:
    """
    Generate a structured access token with user identity payload.
    """
    scopes = scopes or ["read"]
    user_profile = user_profile or {}
    iat, exp = timestamp(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "iss": "senama-auth",
        "aud": ["api", "vendor-panel"],
        "sub": str(user_id),
        "jti": session_id,
        "session_id": session_id,
        "role": role,
        "token_type": "access",
        "status": user_profile.get("status", "active"),
        "scopes": scopes,
        "language": language,
        "amr": ["otp"],
        "user": {
            "first_name": user_profile.get("first_name"),
            "last_name": user_profile.get("last_name"),
            "email": user_profile.get("email"),
            "phone": user_profile.get("phone"),
            "business_name": user_profile.get("business_name"),
            "location": user_profile.get("location"),
            "address": user_profile.get("address"),
            "profile_picture": user_profile.get("profile_picture"),
            "business_category_ids": user_profile.get("business_category_ids", [])
        },
        "iat": iat,
        "exp": exp
    }

    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=ALGORITHM)


async def generate_refresh_token(
    user_id: str,
    role: str,
    session_id: str,
) -> str:
    """
    Generate refresh token with minimal payload, stored in Redis.
    """
    iat, exp = timestamp(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "iss": "senama-auth",
        "aud": ["auth-service"],
        "sub": user_id,
        "jti": session_id,
        "session_id": session_id,
        "role": role,
        "token_type": "refresh",
        "iat": iat,
        "exp": exp
    }

    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=ALGORITHM)


    return token


async def generate_temp_token(
    phone: str,
    role: str,
    jti: str,
    status: str = "incomplete",
    phone_verified: bool = False,
    language: str = "fa",
    redis: Redis = None
) -> str:
    """
    Generate temporary token for OTP verification steps (login/signup).
    """
    iat, exp = timestamp(minutes=TEMP_TOKEN_EXPIRE_MINUTES)
    payload = {
        "iss": "senama-auth",
        "aud": ["auth-temp"],
        "sub": phone,
        "jti": jti,
        "role": role,
        "token_type": "temp",
        "status": status,
        "phone_verified": phone_verified,
        "language": language,
        "iat": iat,
        "exp": exp
    }

    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=ALGORITHM)
