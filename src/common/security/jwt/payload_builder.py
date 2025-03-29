from datetime import datetime, timezone
from uuid import uuid4
from typing import Optional, List

from domain.auth.entities.token_entity import (
    UserJWTProfile,
    VendorJWTProfile,
)


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
    expires_in: int = 3600,
    issuer: str = "senama-auth",
    audience: Optional[List[str]] = None,
    amr: Optional[List[str]] = None,
    jti: Optional[str] = None,
    language: Optional[str] = "fa",
) -> dict:
    now = int(datetime.now(timezone.utc).timestamp())
    exp = now + expires_in

    # Determine effective language from profile
    profile_lang = (
        (user_data.get("languages")[0] if user_data and user_data.get("languages") else None)
        if role == "user"
        else (vendor_data.get("languages")[0] if vendor_data and vendor_data.get("languages") else None)
    )

    payload = {
        "iss": issuer,
        "aud": audience or default_audience(token_type, role),
        "sub": subject_id,
        "jti": jti or str(uuid4()),
        "role": role,
        "token_type": token_type,
        "iat": now,
        "exp": exp,
        "language": profile_lang or language,
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
    if token_type == "access":
        if role == "vendor":
            return ["api", "vendor-panel"]
        return ["api"]
    return ["auth-temp"]
