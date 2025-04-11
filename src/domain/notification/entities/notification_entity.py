from datetime import datetime, UTC
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class NotificationChannel(str, Enum):
    PUSH = "push"
    SMS = "sms"
    EMAIL = "email"
    INAPP = "inapp"

class NotificationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    READ = "read"

class Notification(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")  # MongoDB ID
    receiver_id: str  # ID of the target user/vendor/admin
    receiver_type: str  # "user", "vendor", or "admin"
    created_by: Optional[str] = None  # ID of the sender (e.g., system or admin)
    title: str
    body: str
    channel: NotificationChannel = NotificationChannel.INAPP
    status: NotificationStatus = NotificationStatus.PENDING
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    sent_at: Optional[str] = None
    read_at: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    class Config:
        populate_by_name = True  # Allow using 'id' instead of '_id'