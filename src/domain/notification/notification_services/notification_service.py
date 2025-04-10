# File: src/domain/notification/notification_services/notification_service.py
from typing import List, Dict, Union
from domain.notification.entities.notification_entity import NotificationChannel, Notification
from domain.notification.notification_services.builder import build_notification_content
from infrastructure.database.mongodb.mongo_client import insert_one  # مستقیم وارد شده
from common.logging.logger import log_error, log_info
from common.exceptions.base_exception import DatabaseConnectionException
from datetime import datetime, timezone

class NotificationService:
    async def _dispatch_notification(
        self,
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
                sent_at=datetime.now(timezone.utc).isoformat()
            )

            notification_id = await insert_one("notifications", notification.model_dump(exclude_none=True))
            if not notification_id:
                raise DatabaseConnectionException(db_type="MongoDB", detail="Failed to insert notification")
            notification.id = str(notification_id)

            audit_id = await insert_one("audit_logs", {
                "action": "notification_sent",
                "timestamp": datetime.now(timezone.utc).isoformat(),
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
            raise  # به لایه بالاتر ارسال می‌شه
        except Exception as e:
            raise Exception(f"Failed to dispatch notification: {str(e)}")

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
        return_bool: bool = False,
        additional_receivers: List[Dict[str, str]] = None
    ) -> Union[str, bool]:
        try:
            content = await build_notification_content(
                template_key,
                language=language,
                variables=variables or {}
            )
            notification_id = await self._dispatch_notification(
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

            for receiver in additional_receivers or []:
                await self.send(
                    receiver_id=receiver["id"],
                    receiver_type=receiver["type"],
                    template_key=template_key,
                    channel=channel,
                    variables=variables,
                    reference_type=reference_type,
                    reference_id=reference_id,
                    created_by=created_by,
                    language=language
                )

            return True if return_bool else notification_id

        except ValueError as ve:
            log_error("Invalid template in notification", extra={
                "receiver_id": receiver_id,
                "template_key": template_key,
                "error": str(ve)
            })
            await self.send(
                receiver_id="admin",
                receiver_type="admin",
                template_key="notification_failed",
                variables={"receiver_id": receiver_id, "error": str(ve), "type": "template"},
                reference_type="system",
                reference_id=receiver_id,
                language=language
            )
            if return_bool:
                return False
            raise

        except DatabaseConnectionException as db_exc:
            log_error("Database error in notification service", extra={
                "receiver_id": receiver_id,
                "template_key": template_key,
                "error": str(db_exc)
            })
            await self.send(
                receiver_id="admin",
                receiver_type="admin",
                template_key="notification_failed",
                variables={"receiver_id": receiver_id, "error": str(db_exc), "type": "database"},
                reference_type="system",
                reference_id=receiver_id,
                language=language
            )
            if return_bool:
                return False
            raise

        except Exception as e:
            log_error("Notification service failed", extra={
                "receiver_id": receiver_id,
                "template_key": template_key,
                "error": str(e)
            })
            await self.send(
                receiver_id="admin",
                receiver_type="admin",
                template_key="notification_failed",
                variables={"receiver_id": receiver_id, "error": str(e), "type": "general"},
                reference_type="system",
                reference_id=receiver_id,
                language=language
            )
            if return_bool:
                return False
            raise

    async def send_otp_verified(self, phone: str, role: str, language: str) -> bool:
        return await self.send(
            receiver_id=phone,
            receiver_type=role,
            template_key="otp_verified",
            variables={"phone": phone, "role": role},
            reference_type="otp",
            reference_id=phone,
            language=language,
            return_bool=True,
            additional_receivers=[{"id": "admin", "type": "admin"}]
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
            await self._dispatch_notification(
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
                await self._dispatch_notification(
                    receiver_id="admin",
                    receiver_type="admin",
                    title=admin_content["title"],
                    body=admin_content["body"],
                    channel=NotificationChannel.INAPP,
                    reference_type="session",
                    reference_id=user_id
                )
            return True

        except DatabaseConnectionException as db_exc:
            log_error("Database error in session notification", extra={
                "user_id": user_id,
                "ip": client_ip,
                "error": str(db_exc)
            })
            await self.send(
                receiver_id="admin",
                receiver_type="admin",
                template_key="notification_failed",
                variables={"user_id": user_id, "error": str(db_exc), "type": "database"},
                reference_type="session",
                reference_id=user_id
            )
            return False

        except Exception as e:
            log_error("Session notification failed", extra={
                "user_id": user_id,
                "ip": client_ip,
                "error": str(e)
            })
            await self.send(
                receiver_id="admin",
                receiver_type="admin",
                template_key="notification_failed",
                variables={"user_id": user_id, "error": str(e), "type": "general"},
                reference_type="session",
                reference_id=user_id
            )
            return False

notification_service = NotificationService()