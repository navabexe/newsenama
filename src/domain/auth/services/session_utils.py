# File: domain/auth/auth_services/session_service/session_utils.py

from datetime import datetime, timezone
from typing import List

from redis.asyncio import Redis

from common.logging.logger import log_warning, log_info
from domain.auth.entities.session_entity import Session


def get_session_ttl(expiry_ts: int) -> str:
    now_ts = int(datetime.now(tz=timezone.utc).timestamp())
    ttl = expiry_ts - now_ts
    return f"{ttl} seconds" if ttl > 0 else "expired"


async def fetch_sessions_from_redis(redis: Redis, user_id: str, status_filter: str = "active") -> List[dict]:
    pattern = f"sessions:{user_id}:*"
    session_keys = [key async for key in redis.scan_iter(match=pattern)]

    log_info("Scanning session keys", extra={"pattern": pattern, "key_count": len(session_keys)})

    sessions = []
    for key in session_keys:
        session_data = await redis.hgetall(key)
        session_id = session_data.get("jti")
        raw_status = session_data.get("status")
        is_active = raw_status == "active"

        if status_filter == "active" and not is_active:
            continue

        try:
            session = Session(
                id=session_id,
                user_id=user_id,
                device_name=session_data.get("device_name"),
                device_type=session_data.get("device_type"),
                os=session_data.get("os"),
                browser=session_data.get("browser"),
                user_agent=session_data.get("user_agent"),
                ip_address=session_data.get("ip"),
                location=session_data.get("location"),
                is_active=is_active,
                created_at=session_data.get("created_at"),
                last_seen_at=session_data.get("last_seen_at"),
            )
            session_dict = session.model_dump()
            session_dict["ttl"] = get_session_ttl(int(session_data.get("exp", "0")))
            sessions.append(session_dict)
        except Exception as e:
            log_warning("Skipping invalid session entry", extra={"key": key, "error": str(e)})

    return sessions
