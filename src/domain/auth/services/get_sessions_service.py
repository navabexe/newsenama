# File: domain/auth/auth_services/session_service/get_sessions_service.py

from typing import Literal

from redis.asyncio import Redis

from common.logging.logger import log_info, log_error
from domain.auth.services.session_utils import fetch_sessions_from_redis
from domain.notification.services.notification_service import NotificationService


async def get_sessions_service(
    user_id: str,
    redis: Redis,
    status_filter: Literal["active", "all"] = "active",
    language: str = "fa",
    requester_role: str = "vendor",
    client_ip: str = "unknown",
) -> dict:
    """
    Retrieve user sessions from Redis with optional status filtering.
    Also sends a notification to admin if sessions were accessed.
    """
    sessions = await fetch_sessions_from_redis(redis=redis, user_id=user_id, status_filter=status_filter)

    notification_sent = False
    if requester_role == "admin":
        try:
            notification_sent = await NotificationService().send_session_notification(
                user_id=user_id,
                sessions=sessions,
                ip=client_ip,
                language=language
            )
        except Exception as e:
            log_error("Session notification failed", extra={
                "user_id": user_id,
                "ip": client_ip,
                "error": str(e)
            })

    log_info("Sessions retrieved successfully", extra={
        "user_id": user_id,
        "session_count": len(sessions),
        "status_filter": status_filter
    })

    return {
        "sessions": sessions,
        "notification_sent": notification_sent
    }
