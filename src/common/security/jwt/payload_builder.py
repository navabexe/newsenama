# File: common/security/jwt/payload_builder.py
from datetime import datetime, timezone
from uuid import uuid4
from typing import Optional, List

from common.config.settings import settings
from domain.auth.entities.token_entity import UserJWTProfile, VendorJWTProfile

ALLOWED_LANGUAGES = ["fa", "en", "ar"]

def get_profile_language(role: str, user_data: Optional[dict], vendor_data: Optional[dict]) -> str:
    """Extract the preferred language from user or vendor profile, defaulting to 'fa'."""
    profile_data = user_data if role == "user" else vendor_data
    if profile_data and "languages" in profile_data and profile_data["languages"]:
        lang = profile_data["languages"][0]
        return lang if lang in ALLOWED_LANGUAGES else "fa"
    return "fa"

def build_jwt_payload(
    *,
    token_type: str,
    role: str,
    subject_id: str,
    phone: Optional[str] = None,
    status: Optional[str] = None,
    phone_verified: Optional[bool] = None,
    scopes: Optional[List[str]] = None,
    session_id: Optional[str] = None,
    user_data: Optional[dict] = None,
    vendor_data: Optional[dict] = None,
    vendor_id: Optional[str] = None,
    expires_in: int = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    issuer: str = "senama-auth",
    audience: Optional[List[str]] = None,
    amr: Optional[List[str]] = None,
    jti: Optional[str] = None,
    language: Optional[str] = "fa",
) -> dict:
    """Build a standardized JWT payload with the provided claims."""
    now = int(datetime.now(timezone.utc).timestamp())
    exp = now + expires_in

    effective_language = get_profile_language(role, user_data, vendor_data) or language

    payload = {
        "iss": issuer,
        "aud": audience or default_audience(token_type, role),
        "sub": subject_id,
        "jti": jti or str(uuid4()),
        "role": role,
        "token_type": token_type,
        "iat": now,
        "exp": exp,
        "language": effective_language,
    }

    if phone:
        payload["phone"] = phone
    if session_id:
        payload["session_id"] = session_id
    if status is not None:
        payload["status"] = status
    if phone_verified is not None:
        payload["phone_verified"] = phone_verified
    if scopes:
        payload["scopes"] = scopes
    if amr:
        payload["amr"] = amr
    if vendor_id:
        payload["vendor_id"] = vendor_id

    if token_type == "access":
        if role == "user" and user_data:
            payload["user_profile"] = UserJWTProfile(**user_data).model_dump()
        elif role == "vendor" and vendor_data:
            payload["vendor_profile"] = VendorJWTProfile(**vendor_data).model_dump()

    return payload

def default_audience(token_type: str, role: Optional[str] = None) -> List[str]:
    """Return the default audience based on token type and role."""
    if token_type == "access":
        return ["api", "vendor-panel"] if role == "vendor" else ["api"]
    return ["auth-temp"]