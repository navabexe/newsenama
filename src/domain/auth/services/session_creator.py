from datetime import datetime
from datetime import timezone
from uuid import uuid4

from redis.asyncio import Redis

from common.config.settings import settings
from common.logging.logger import log_info
from common.security.jwt_handler import generate_access_token, generate_refresh_token
from common.utils.ip_utils import get_location_from_ip
from common.utils.string_utils import safe_json_dumps
from domain.auth.entities.token_entity import VendorJWTProfile


def stringify_session_data(data: dict) -> dict:
    """Convert all values in session_data to byte-safe strings.
    JSON-dump any dict, list, tuple values.
    """
    result = {}
    for k, v in data.items():
        if v is None:
            continue
        key_encoded = k.encode()
        if isinstance(v, (dict, list, tuple)):
            result[key_encoded] = safe_json_dumps(v).encode()
        else:
            result[key_encoded] = str(v).encode()
    return result


async def create_user_session(
    *,
    user_id: str,
    phone: str,
    role: str,
    user: dict,
    redis: Redis,
    client_ip: str,
    user_agent: str,
    language: str,
    now: datetime
) -> dict:
    session_id = str(uuid4())
    profile_data = VendorJWTProfile(**user).model_dump() if role == "vendor" else None
    location = await get_location_from_ip(client_ip) if client_ip else "Unknown"
    now = now or datetime.now(timezone.utc)

    session_data = {
        "ip": client_ip,
        "created_at": now.isoformat(),
        "last_seen_at": now.isoformat(),
        "device_name": "Unknown Device",
        "device_type": "Desktop",
        "os": "Windows",
        "browser": "Chrome",
        "user_agent": user_agent,
        "location": location,
        "status": "active",
        "jti": session_id,
        "vendor_profile": profile_data if profile_data else None
    }

    session_data_cleaned = stringify_session_data(session_data)

    # 🔍 Log full content for debugging
    log_info("🧪 Session data to be stored in Redis", extra={"cleaned_data": session_data_cleaned})

    session_key = f"sessions:{user_id}:{session_id}"
    await redis.hset(name=session_key, mapping=session_data_cleaned)
    await redis.expire(session_key, settings.SESSION_EXPIRY)

    access_token = await generate_access_token(
        user_id=user_id,
        role=role,
        session_id=session_id,
        vendor_profile=profile_data,
        language=language,
        status="active",
        phone_verified=True
    )

    refresh_token, refresh_jti = await generate_refresh_token(
        user_id=user_id,
        role=role,
        session_id=session_id,
        status="active",
        language=language,
        return_jti=True
    )

    await redis.setex(
        f"refresh_tokens:{user_id}:{refresh_jti}",
        settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        "active"
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "status": "active",
        "message": "otp.valid",
        "phone": phone
    }
