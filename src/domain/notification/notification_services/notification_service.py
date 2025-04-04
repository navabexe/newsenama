# File: Root/src/domain/notification/notification_services/notification_service.py

from datetime import datetime, UTC
from typing import Optional

from domain.notification.entities.notification_entity import Notification, NotificationChannel, NotificationStatus
from common.logging.logger import log_info, log_error
from infrastructure.database.mongodb.mongo_client import insert_one


async def send_notification(
    receiver_id: str,
    receiver_type: str,
    title: str,
    body: str,
    channel: NotificationChannel = NotificationChannel.INAPP,
    reference_type: Optional[str] = None,
    reference_id: Optional[str] = None
) -> Notification:
    """
    Send a notification to the specified user, vendor, or admin.

    Args:
        receiver_id: ID of the recipient
        receiver_type: Type of recipient (user, vendor, admin)
        title: Short title of the notification
        body: Main message content
        channel: Notification channel (default is in-app)
        reference_type: Optional type of related entity (order, product)
        reference_id: Optional ID of related entity

    Returns:
        Notification object with metadata
    """
    try:
        notification = Notification(
            receiver_id=receiver_id,
            receiver_type=receiver_type,
            title=title,
            body=body,
            channel=channel,
            reference_type=reference_type,
            reference_id=reference_id,
            status=NotificationStatus.SENT,
            sent_at=datetime.now(UTC).isoformat()
        )

        # Insert into MongoDB collection "notifications"
        notification_dict = notification.dict()
        notification_id = await insert_one("notifications", notification_dict)
        notification.id = str(notification_id)

        log_info("Notification sent", extra={
            "receiver_id": receiver_id,
            "receiver_type": receiver_type,
            "channel": channel,
            "title": title
        })

        return notification

    except Exception as e:
        log_error("Notification failed", extra={"error": str(e)})
        raise
