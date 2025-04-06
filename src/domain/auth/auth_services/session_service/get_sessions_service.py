# File: domain/auth/auth_services/session_service/get_sessions_service.py

from datetime import datetime, timezone
from fastapi import HTTPException, status, Depends
from redis.asyncio import Redis
from typing import Optional

from common.logging.logger import log_info, log_error
from common.translations.messages import get_message
from infrastructure.database.mongodb.mongo_client import insert_one
from infrastructure.database.redis.operations.hgetall import hgetall
from infrastructure.database.redis.operations.scan import scan_keys
from infrastructure.database.redis.operations.ttl import ttl as redis_ttl
from infrastructure.database.redis.redis_client import get_redis_client
from domain.notification.notification_services.builder import build_notification_content
from domain.notification.notification_services.dispatcher import dispatch_notification
from domain.notification.entities.notification_entity import NotificationChannel
from domain.auth.entities.session_entity import Session

async def log_audit(action: str, details: dict):
    await insert_one("audit_logs", {
        "action": action,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": details
    })

def decode_value(value):
    """Decode bytes to str if necessary, otherwise return as-is."""
    if isinstance(value, bytes):
        return value.decode()
    return value  # Return str or None as-is

async def send_session_notification(
    user_id: str,
    role: str,
    client_ip: str,
    sessions: list,
    language: str,
    is_admin_action: bool = False
):
    """Send notifications to user and admin based on session retrieval."""
    try:
        session_count = len(sessions)
        if sessions:
            latest_session = max(sessions, key=lambda s: s.get("last_seen_at", s["created_at"]))
            time = latest_session.get("last_seen_at", latest_session["created_at"])
            device = latest_session.get("device", "unknown")
        else:
            time = datetime.now(timezone.utc).isoformat()
            device = "unknown"

        user_content = await build_notification_content(
            template_key="sessions.checked",
            language=language,
            variables={
                "ip": client_ip,
                "time": time,
                "count": session_count,
                "device": device
            }
        )
        await dispatch_notification(
            receiver_id=user_id,
            receiver_type=role,
            title=user_content["title"],
            body=user_content["body"],
            channel=NotificationChannel.INAPP,
            reference_type="session",
            reference_id=user_id
        )

        ip_count = len(set(s["ip_address"] for s in sessions)) if sessions else 0
        if session_count > 5 or ip_count > 3:
            admin_content = await build_notification_content(
                template_key="sessions.danger",
                language=language,
                variables={
                    "user_id": user_id,
                    "ip": client_ip,
                    "count": session_count,
                    "ip_count": ip_count
                }
            )
            await dispatch_notification(
                receiver_id="admin",
                receiver_type="admin",
                title=admin_content["title"],
                body=admin_content["body"],
                channel=NotificationChannel.INAPP,
                reference_type="session",
                reference_id=user_id
            )
        return True
    except Exception as e:
        log_error("Session notification failed", extra={"error": str(e), "user_id": user_id, "ip": client_ip})
        return False

async def get_sessions_service(
    user_id: str,
    client_ip: str,
    status_filter: str = "active",  # "active", "all"
    language: str = "fa",
    requester_role: str = "user",
    redis: Redis = Depends(get_redis_client)
) -> dict:
    try:
        session_keys = await scan_keys(redis, f"sessions:{user_id}:*")
        sessions = []

        for key in session_keys:
            key_type = await redis.type(key)
            key_type_str = key_type.decode() if isinstance(key_type, bytes) else str(key_type)

            if key_type_str != "hash":
                log_info("Skipping non-hash key during session read", extra={
                    "key": key,
                    "type": key_type_str,
                    "user_id": user_id,
                    "ip": client_ip
                })
                continue

            session_data = await hgetall(key, redis)
            session_id = key.decode().split(":")[-1] if isinstance(key, bytes) else key.split(":")[-1]
            raw_status = session_data.get(b"status") or session_data.get("status", b"unknown")
            is_active = decode_value(raw_status) == "active"

            log_info("Processing session", extra={
                "key": key,
                "session_id": session_id,
                "raw_status": raw_status,
                "is_active": is_active,
                "status_filter": status_filter,
                "user_id": user_id,
                "ip": client_ip
            })

            if status_filter == "active" and not is_active:
                log_info("Session filtered out due to inactive status", extra={
                    "session_id": session_id,
                    "user_id": user_id,
                    "ip": client_ip
                })
                continue

            session_ttl = await redis_ttl(key, redis)
            log_info("Session TTL checked", extra={
                "session_id": session_id,
                "ttl": session_ttl,
                "user_id": user_id,
                "ip": client_ip
            })
            if session_ttl == -2:
                log_info("Session skipped due to expired key", extra={
                    "session_id": session_id,
                    "user_id": user_id,
                    "ip": client_ip
                })
                continue
            ttl_label = "no-expiry" if session_ttl == -1 else f"{session_ttl} seconds"

            sessions.append({
                "session_id": session_id,
                "user_id": user_id,
                "device_name": decode_value(session_data.get(b"device_name") or session_data.get("device_name", None)),
                "device_type": decode_value(session_data.get(b"device_type") or session_data.get("device_type", None)),
                "os": decode_value(session_data.get(b"os") or session_data.get("os", None)),
                "browser": decode_value(session_data.get(b"browser") or session_data.get("browser", None)),
                "user_agent": decode_value(session_data.get(b"user_agent") or session_data.get("user_agent", None)),
                "ip_address": decode_value(session_data.get(b"ip") or session_data.get("ip", b"unknown")),
                "location": decode_value(session_data.get(b"location") or session_data.get("location", None)),
                "is_active": is_active,
                "created_at": decode_value(session_data.get(b"created_at") or session_data.get("created_at", b"unknown")),
                "last_seen_at": decode_value(session_data.get(b"last_seen_at") or session_data.get("last_seen_at", None)),
                "ttl": ttl_label
            })

        log_info("Sessions retrieved successfully", extra={
            "user_id": user_id,
            "session_count": len(sessions),
            "status_filter": status_filter,
            "ip": client_ip,  # اینجا از client_ip استفاده می‌کنیم که str هست
            "requester_role": requester_role,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        await log_audit("sessions_retrieved", {
            "user_id": user_id,
            "session_count": len(sessions),
            "status_filter": status_filter,
            "ip": client_ip,  # اینجا هم str هست
            "requester_role": requester_role,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        notification_sent = await send_session_notification(
            user_id=user_id,
            role=requester_role if requester_role == "admin" else "vendor",
            client_ip=client_ip,
            sessions=sessions,
            language=language,
            is_admin_action=(requester_role == "admin")
        )

        message_key = "sessions.active_retrieved" if status_filter == "active" else "sessions.all_retrieved"
        return {
            "sessions": sessions,
            "notification_sent": notification_sent,
            "message": get_message(message_key, language)
        }

    except Exception as e:
        log_error("Session retrieval failed", extra={
            "user_id": user_id,
            "error": str(e),
            "ip": client_ip,  # اینجا هم str هست
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=get_message("server.error", language))