from datetime import datetime, timedelta, timezone
from uuid import uuid4
import jwt
from common.config.settings import settings
from common.logging.logger import log_info, log_error
from infrastructure.database.redis.redis_client import setex, get, delete, keys
from infrastructure.database.mongodb.mongo_client import find_one
from .errors import JWTError

def generate_temp_token(phone: str, role: str, jti: str = None, phone_verified: bool = False) -> str:
    jti = jti or str(uuid4())
    payload = {
        "sub": phone,
        "role": role,
        "jti": jti,
        "phone_verified": phone_verified,
        "exp": datetime.now(timezone.utc) + timedelta(seconds=settings.TEMP_TOKEN_TTL),
        "iat": int(datetime.now(timezone.utc).timestamp())
    }
    try:
        token = jwt.encode(payload, settings.ACCESS_SECRET, algorithm=settings.ALGORITHM)
        log_info("Temp token generated", extra={"phone": phone, "role": role, "jti": jti})
        return token
    except Exception as e:
        log_error("Temp token generation failed", extra={"phone": phone, "error": str(e)})
        raise JWTError(f"Failed to generate temp token: {str(e)}")


def generate_access_token(user_id: str, role: str, session_id: str, scopes: list[str] = None) -> str:
    jti = str(uuid4())
    collection = "admins" if role == "admin" else "vendors" if role == "vendor" else "users"
    user_data = find_one(collection, {"_id": user_id})
    if not user_data:
        log_error("User not found for token", extra={"user_id": user_id, "role": role})
        raise JWTError(f"No {role} found with ID: {user_id}")

    payload = {
        "sub": user_id,
        "role": role,
        "jti": jti,
        "session_id": session_id,
        "exp": datetime.now(timezone.utc) + timedelta(seconds=settings.ACCESS_TTL),
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "scopes": scopes or (
            ["admin:read", "admin:write"] if role == "admin" else
            ["vendor:read", "vendor:write"] if role == "vendor" else
            ["read"]
        ),
        "status": user_data.get("status", "unknown"),
        "vendor_id": user_id if role == "vendor" else None,
        "phone": user_data.get("phone"),
        "phone_verified": user_data.get("phone_verified", False),
        "account_verified": user_data.get("account_verified", False)
    }
    try:
        token = jwt.encode(payload, settings.ACCESS_SECRET, algorithm=settings.ALGORITHM)
        log_info("Access token generated", extra={"user_id": user_id, "jti": jti})
        return token
    except Exception as e:
        log_error("Access token generation failed", extra={"user_id": user_id, "error": str(e)})
        raise JWTError(f"Failed to generate access token: {str(e)}")


def generate_refresh_token(user_id: str, role: str, session_id: str) -> str:
    jti = str(uuid4())
    payload = {
        "sub": user_id,
        "role": role,
        "jti": jti,
        "session_id": session_id,
        "exp": datetime.now(timezone.utc) + timedelta(seconds=settings.REFRESH_TTL),
        "iat": int(datetime.now(timezone.utc).timestamp())
    }
    try:
        token = jwt.encode(payload, settings.REFRESH_SECRET, algorithm=settings.ALGORITHM)
        redis_key = f"refresh_tokens:{user_id}:{jti}"
        setex(redis_key, settings.REFRESH_TTL, "valid")

        # Limit refresh tokens to 5
        all_keys = keys(f"refresh_tokens:{user_id}:*")
        if len(all_keys) > 5:
            sorted_keys = sorted(all_keys, key=lambda k: get(k) or "")
            for old_key in sorted_keys[:-5]:
                delete(old_key)
                old_jti = old_key.split(":")[-1]
                setex(f"blacklist:{old_jti}", settings.REFRESH_TTL, "revoked")
                log_info("Old refresh token removed", extra={"user_id": user_id, "key": old_key})

        log_info("Refresh token generated", extra={"user_id": user_id, "jti": jti})
        return token

    except Exception as e:
        log_error("Refresh token generation failed", extra={"user_id": user_id, "error": str(e)})
        raise JWTError(f"Failed to generate refresh token: {str(e)}")
