from datetime import datetime, UTC
from domain.notification.entities.notification_entity import Notification, NotificationChannel
from infrastructure.database.mongodb.mongo_client import insert_one
from common.logging.logger import log_info, log_error

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
        notification.id = str(notification_id)

        await insert_one("audit_logs", {
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

        log_info("Notification dispatched", extra={
            "notification_id": notification_id,
            "receiver_id": receiver_id,
            "receiver_type": receiver_type,
            "channel": channel.value,
            "title": title,
            "created_by": created_by
        })
        return notification_id

    except Exception as e:
        log_error("Failed to dispatch notification", extra={
            "receiver_id": receiver_id,
            "error": str(e)
        }, exc_info=True)
        raise Exception(f"Failed to dispatch notification: {str(e)}")