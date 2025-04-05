# File: domain/notification/notification_services/notification_service.py

from domain.notification.entities.notification_entity import NotificationChannel
from domain.notification.notification_services.builder import build_notification_content
from domain.notification.notification_services.dispatcher import dispatch_notification

class NotificationService:
    async def send(
        self,
        receiver_id: str,
        receiver_type: str,
        template_key: str,
        channel: NotificationChannel = NotificationChannel.INAPP,
        variables: dict = None,
        reference_type: str = None,
        reference_id: str = None,
        created_by: str = "system",
        language: str = "fa"
    ) -> str:
        try:
            content = await build_notification_content(template_key, language=language, variables=variables or {})
            notification_id = await dispatch_notification(
                receiver_id=receiver_id,
                receiver_type=receiver_type,
                title=content["title"],
                body=content["body"],
                channel=channel,
                reference_type=reference_type,
                reference_id=reference_id,
                created_by=created_by
            )
            return notification_id
        except Exception as e:
            raise Exception(f"Notification service failed: {str(e)}")

notification_service = NotificationService()