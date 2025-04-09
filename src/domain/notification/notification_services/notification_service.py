# File: src/domain/notification/notification_services/notification_service.py
from domain.notification.entities.notification_entity import NotificationChannel
from domain.notification.notification_services.builder import build_notification_content
from domain.notification.notification_services.dispatcher import dispatch_notification
from common.logging.logger import log_error, log_info
from datetime import datetime, timezone

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
        language: str = "fa",
        return_bool: bool = False
    ) -> str | bool:
        try:
            content = await build_notification_content(
                template_key,
                language=language,
                variables=variables or {}
            )
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
            log_info("Notification sent successfully", extra={
                "receiver_id": receiver_id,
                "template_key": template_key,
                "notification_id": notification_id
            })
            return True if return_bool else notification_id
        except Exception as e:
            log_error("Notification service failed", extra={
                "receiver_id": receiver_id,
                "template_key": template_key,
                "error": str(e)
            })
            if return_bool:
                return False
            raise Exception(f"Notification service failed: {str(e)}")

    async def send_otp_verified(self, phone: str, role: str, language: str) -> bool:
        return await self.send(
            receiver_id=phone,
            receiver_type=role,
            template_key="otp_verified",
            variables={"phone": phone, "role": role},
            reference_type="otp",
            reference_id=phone,
            language=language,
            return_bool=True
        )

    async def send_session_notification(
        self,
        user_id: str,
        role: str,
        client_ip: str,
        sessions: list,
        language: str,
        is_admin_action: bool = False
    ) -> bool:
        try:
            session_count = len(sessions)
            if sessions:
                latest_session = max(sessions, key=lambda s: s.get("last_seen_at", s["created_at"]))
                time = latest_session.get("last_seen_at", latest_session["created_at"])
                device = latest_session.get("device_name", "unknown")
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

notification_service = NotificationService()