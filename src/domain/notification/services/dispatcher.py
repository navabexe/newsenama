# File: domain/notification/services/dispatch_notification.py
from datetime import datetime, UTC

from common.exceptions.base_exception import DatabaseConnectionException
from common.logging.logger import log_info, log_error
from domain.notification.entities.notification_entity import Notification, NotificationChannel
from domain.notification.services.notification_service import notification_service
from infrastructure.database.mongodb.mongo_client import insert_one


async def dispatch_notification(
    receiver_id: str,
    receiver_type: str,
    title: str,
    body: str,
    channel: NotificationChannel = NotificationChannel.INAPP,
    reference_type: str = None,
    reference_id: str = None,
    created_by: str = "system"
) -> str:
    if channel != NotificationChannel.INAPP:
        raise ValueError(f"Channel {channel} not yet supported")

    try:
        notification = Notification(
            receiver_id=receiver_id,
            receiver_type=receiver_type,
            created_by=created_by,
            title=title,
            body=body,
            channel=channel,
            reference_type=reference_type,
            reference_id=reference_id,
            status="sent",
            sent_at=datetime.now(UTC).isoformat()
        )

        notification_id = await insert_one("notifications", notification.model_dump(exclude_none=True))
        if not notification_id:
            raise DatabaseConnectionException(db_type="MongoDB", detail="Failed to insert notification")
        notification.id = str(notification_id)

        audit_id = await insert_one("audit_logs", {
            "action": "notification_sent",
            "timestamp": datetime.now(UTC).isoformat(),
            "details": {
                "notification_id": notification_id,
                "receiver_id": receiver_id,
                "receiver_type": receiver_type,
                "created_by": created_by,
                "channel": channel.value
            }
        })
        if not audit_id:
            raise DatabaseConnectionException(db_type="MongoDB", detail="Failed to insert audit log")

        log_info("Notification dispatched", extra={
            "notification_id": notification_id,
            "receiver_id": receiver_id,
            "receiver_type": receiver_type,
            "channel": channel.value,
            "title": title,
            "created_by": created_by
        })
        return notification_id

    except DatabaseConnectionException as db_exc:
        log_error("Database error in dispatch", extra={
            "receiver_id": receiver_id,
            "error": str(db_exc)
        }, exc_info=True)
        await notification_service.send(
            receiver_id="admin",
            receiver_type="admin",
            template_key="notification_failed",
            variables={"receiver_id": receiver_id, "error": str(db_exc), "type": "database"},
            reference_type="system",
            reference_id=receiver_id
        )
        raise

    except Exception as e:
        log_error("Failed to dispatch notification", extra={
            "receiver_id": receiver_id,
            "error": str(e)
        }, exc_info=True)
        await notification_service.send(
            receiver_id="admin",
            receiver_type="admin",
            template_key="notification_failed",
            variables={"receiver_id": receiver_id, "error": str(e), "type": "general"},
            reference_type="system",
            reference_id=receiver_id
        )
        raise Exception(f"Failed to dispatch notification: {str(e)}")