# File: common/security/jwt/tokens.py
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from jose import jwt
from typing import Optional, List

from common.config.settings import settings
from common.logging.logger import log_info
from .payload_builder import build_jwt_payload

def generate_jti() -> str:
    """Generate a unique JWT identifier (jti)."""
    return str(uuid4())

def get_timestamps(expires_in_minutes: int = 0, expires_in_days: int = 0) -> tuple[int, int]:
    """Calculate issued-at (iat) and expiration (exp) timestamps."""
    now = datetime.now(timezone.utc)
    iat = int(now.timestamp())
    exp = int((now + timedelta(minutes=expires_in_minutes, days=expires_in_days)).timestamp())
    return iat, exp

async def generate_access_token(
    user_id: str,
    role: str,
    session_id: str,
    user_profile: Optional[dict] = None,
    vendor_profile: Optional[dict] = None,
    scopes: Optional[List[str]] = None,
    language: str = "fa",
    vendor_id: Optional[str] = None,
) -> str:
    """
    Generate a structured access token with user identity payload.

    Args:
        user_id (str): Unique identifier of the user.
        role (str): User role (e.g., "user", "vendor", "admin").
        session_id (str): Session identifier.
        user_profile (Optional[dict]): User profile data for "user" role.
        vendor_profile (Optional[dict]): Vendor profile data for "vendor" role.
        scopes (Optional[List[str]]): List of access scopes.
        language (str): Preferred language (default: "fa").
        vendor_id (Optional[str]): Vendor identifier if applicable.

    Returns:
        str: Encoded JWT access token.
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
    language: str = "fa",
) -> str:
    """
    Generate a temporary token for OTP verification steps (login/signup).

    Args:
        phone (str): Phone number used as subject identifier.
        role (str): User role (e.g., "user", "vendor").
        jti (str): Unique token identifier.
        status (str): Account status (default: "incomplete").
        phone_verified (bool): Whether the phone is verified (default: False).
        language (str): Preferred language (default: "fa").

    Returns:
        str: Encoded JWT temporary token.
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
        expires_in=settings.TEMP_TOKEN_EXPIRE_MINUTES * 60,
    )

    token = jwt.encode(payload, settings.ACCESS_SECRET, algorithm=settings.ALGORITHM)
    log_info("Temporary token generated", extra={"jti": jti, "phone": phone})
    return token

async def generate_refresh_token(
    user_id: str,
    role: str,
    session_id: str,
) -> str:
    """
    Generate a refresh token with minimal payload.

    Args:
        user_id (str): Unique identifier of the user.
        role (str): User role (e.g., "user", "vendor", "admin").
        session_id (str): Session identifier.

    Returns:
        str: Encoded JWT refresh token.
    """
    payload = build_jwt_payload(
        token_type="refresh",
        role=role,
        subject_id=user_id,
        session_id=session_id,
        expires_in=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )

    token = jwt.encode(payload, settings.REFRESH_SECRET, algorithm=settings.ALGORITHM)
    log_info("Refresh token generated", extra={"jti": payload["jti"], "user_id": user_id})
    return token