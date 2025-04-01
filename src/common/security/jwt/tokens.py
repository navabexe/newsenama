from datetime import datetime, timedelta, timezone
from uuid import uuid4
from jose import jwt
from typing import Optional, List, Union, Tuple

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
    amr: Optional[List[str]] = None,
    status: Optional[str] = None,
    phone_verified: Optional[bool] = None,
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
    status = status if status is not None else base_profile.get("status") if base_profile else None
    phone = base_profile.get("phone") if base_profile else None
    phone_verified = phone_verified if phone_verified is not None else base_profile.get("phone_verified") if base_profile else None

    log_info("Resolved parameters", extra={
        "status": status,
        "phone": phone,
        "phone_verified": phone_verified,
        "base_profile": base_profile
    })

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
    language: str = "fa",
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
    """
    Generate refresh token.

    Args:
        return_jti (bool): If True, returns (token, jti) tuple. Otherwise, returns only token.

    Returns:
        Union[str, Tuple[str, str]]
    """
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

    if return_jti:
        return token, payload["jti"]
    return token
