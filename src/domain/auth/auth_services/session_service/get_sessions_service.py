# File: src/domain/auth/services/session_service/get_sessions_service.py
from datetime import datetime, timezone
from fastapi import HTTPException, status
from redis.asyncio import Redis
from motor.motor_asyncio import AsyncIOMotorDatabase

from common.logging.logger import log_error, log_info
from common.translations.messages import get_message
from common.config.settings import settings
from infrastructure.database.mongodb.repositories.auth_repository import AuthRepository
from domain.auth.services.session_service import get_session_service
from domain.notification.notification_services.notification_service import notification_service
from infrastructure.database.redis.redis_client import get_redis_client
from infrastructure.database.mongodb.connection import get_mongo_db

async def get_sessions_service(
    user_id: str,
    client_ip: str,
    status_filter: str = "active",
    language: str = "fa",
    requester_role: str = "user",
    redis: Redis = None,
    db: AsyncIOMotorDatabase = None
) -> dict:
    session_service = get_session_service(redis)
    if db is None:
        db = await get_mongo_db()
    auth_repo = AuthRepository(db)

    try:
        sessions = await session_service.get_sessions(user_id, client_ip, status_filter)

        await auth_repo.log_audit("sessions_retrieved", {
            "user_id": user_id,
            "session_count": len(sessions),
            "status_filter": status_filter,
            "ip": client_ip,
            "requester_role": requester_role,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        notification_sent = await notification_service.send_session_notification(
            user_id=user_id,
            role=requester_role if requester_role == "admin" else "vendor",
            client_ip=client_ip,
            sessions=sessions,
            language=language,
            is_admin_action=(requester_role == "admin")
        )

        message_key = "sessions.active_retrieved" if status_filter == "active" else "sessions.all_retrieved"
        log_info("Sessions retrieved and processed successfully", extra={
            "user_id": user_id,
            "session_count": len(sessions),
            "ip": client_ip
        })
        return {
            "sessions": sessions,
            "notification_sent": notification_sent,
            "message": get_message(message_key, language)
        }

    except Exception as e:
        log_error("Session retrieval failed", extra={
            "user_id": user_id,
            "error": str(e),
            "ip": client_ip,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=get_message("server.error", language))