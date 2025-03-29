# common/security/jwt/tokens.py

from datetime import datetime, timedelta, timezone
from uuid import uuid4
from jose import jwt

from common.config.settings import settings

# Constants
JWT_SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS
TEMP_TOKEN_EXPIRE_MINUTES = settings.TEMP_TOKEN_EXPIRE_MINUTES


def new_jti() -> str:
    return str(uuid4())


def timestamp(minutes: int = 0, days: int = 0) -> tuple[int, int]:
    iat = int(datetime.now(timezone.utc).timestamp())
    exp = int((datetime.now(timezone.utc) + timedelta(minutes=minutes, days=days)).timestamp())
    return iat, exp


from common.security.jwt.payload_builder import build_jwt_payload

# ...

async def generate_access_token(
    user_id: str,
    role: str,
    session_id: str,
    user_profile: dict = None,
    vendor_profile: dict = None,
    scopes: list = None,
    language: str = "fa",
    vendor_id: str = None,
) -> str:
    """
    Generate a structured access token with user identity payload.
    """
    base_profile = user_profile if role == "user" else vendor_profile

    status = base_profile.get("status") if base_profile else None
    phone = base_profile.get("phone") if base_profile else None

    payload = build_jwt_payload(
        token_type="access",
        role=role,
        subject_id=user_id,
        session_id=session_id,
        scopes=scopes or ["read"],
        language=language,
        status=status,
        phone=phone,
        user_data=user_profile if role == "user" else None,
        vendor_data=vendor_profile if role == "vendor" else None,
        vendor_id=vendor_id,
        amr=["otp"],
    )

    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=ALGORITHM)




async def generate_temp_token(
    phone: str,
    role: str,
    jti: str,
    status: str = "incomplete",
    phone_verified: bool = False,
    language: str = "fa",
) -> str:
    """
    Generate temporary token for OTP verification steps (login/signup).
    """
    payload = build_jwt_payload(
        token_type="temp",
        role=role,
        subject_id=phone,
        phone=phone,
        jti=jti,
        language=language,
        status=status,
        phone_verified=phone_verified,
        expires_in=TEMP_TOKEN_EXPIRE_MINUTES * 60,
    )

    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=ALGORITHM)


async def generate_refresh_token(
    user_id: str,
    role: str,
    session_id: str,
) -> str:
    """
    Generate refresh token with minimal payload.
    """
    payload = build_jwt_payload(
        token_type="refresh",
        role=role,
        subject_id=user_id,
        session_id=session_id,
        expires_in=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )

    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=ALGORITHM)

