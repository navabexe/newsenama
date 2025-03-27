# domain/auth/auth_services/session_service/read.py

from datetime import datetime, timezone
from fastapi import HTTPException, status, Depends
from redis.asyncio import Redis

from common.logging.logger import log_info, log_error
from infrastructure.database.redis.operations.hgetall import hgetall
from infrastructure.database.redis.operations.keys import keys
from infrastructure.database.redis.redis_client import get_redis_client


async def get_sessions_service(
    user_id: str,
    client_ip: str,
    redis: Redis = Depends(get_redis_client)
) -> dict:
    try:
        session_keys = await keys(f"sessions:{user_id}:*", redis)
        sessions = []

        for key in session_keys:
            key_type = await redis.type(key)
            key_type_str = key_type.decode() if isinstance(key_type, bytes) else str(key_type)

            if key_type_str != 'hash':
                log_info("Skipping non-hash key during session read", extra={
                    "key": key,
                    "type": key_type_str
                })
                continue

            session_data = await hgetall(key, redis)
            session_id = key.split(":")[-1]

            # اگر فقط سشن‌های فعال بخوایم:
            # if session_data.get("status") != "active":
            #     continue

            sessions.append({
                "session_id": session_id,
                "ip": session_data.get("ip", "unknown"),
                "created_at": session_data.get("created_at", "unknown"),
                "last_refreshed": session_data.get("last_refreshed", None)
            })

        log_info("Sessions retrieved", extra={
            "user_id": user_id,
            "session_count": len(sessions),
            "ip": client_ip,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return {"sessions": sessions, "message": "Active sessions retrieved"}

    except Exception as e:
        log_error("Session retrieval failed", extra={
            "user_id": user_id,
            "error": str(e),
            "ip": client_ip
        })
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve sessions")
