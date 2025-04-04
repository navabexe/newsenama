# File: Root/src/domain/notification/entities/notification_entity.py

from datetime import datetime, UTC
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class NotificationChannel(str, Enum):
    """Notification delivery channels."""
    PUSH = "push"
    SMS = "sms"
    EMAIL = "email"
    INAPP = "inapp"


class NotificationStatus(str, Enum):
    """Status of the notification lifecycle."""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    READ = "read"


class Notification(BaseModel):
    """Core notification model used for delivery and storage."""
    id: Optional[str] = None
    receiver_id: str  # ID of the target user/vendor/admin
    receiver_type: str  # "user", "vendor", or "admin"
    title: str  # Short headline of the notification
    body: str  # Detailed message content
    channel: NotificationChannel  # Delivery channel
    status: NotificationStatus = NotificationStatus.PENDING  # Default status
    reference_type: Optional[str] = None  # e.g., "product", "order"
    reference_id: Optional[str] = None  # ID of the referenced entity

    sent_at: Optional[str] = None  # Timestamp of when notification was sent
    read_at: Optional[str] = None  # Timestamp of when notification was read
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())  # Creation timestamp
