# File: domain/notification/notification_services/dispatcher.py

from datetime import datetime, timezone
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
    reference_id: str = None
):
    """
    Dispatch a notification (currently INAPP) by saving to database.

    Args:
        receiver_id (str): User/vendor/admin ID
        receiver_type (str): 'user', 'vendor', or 'admin'
        title (str): Notification title
        body (str): Notification body
        channel (NotificationChannel): Channel (default: inapp)
        reference_type (str): Optional reference type (e.g., 'otp')
        reference_id (str): Optional reference ID (e.g., phone)

    Returns:
        None
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
            status="sent",
            sent_at=datetime.now(timezone.utc).isoformat()
        )

        result = await insert_one("notifications", notification.dict(exclude_none=True))
        log_info("Notification sent", extra={
            "receiver_id": receiver_id,
            "receiver_type": receiver_type,
            "channel": channel,
            "title": title
        })

    except Exception as e:
        log_error("Failed to send notification", extra={"error": str(e)}, exc_info=True)
