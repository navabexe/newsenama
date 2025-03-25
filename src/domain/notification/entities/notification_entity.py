from pydantic.v1 import BaseModel, Field
from typing import Optional, List
from datetime import datetime, UTC
from enum import Enum

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
    id: Optional[str] = None
    receiver_id: str
    receiver_type: str  # user / vendor / admin
    title: str
    body: str
    channel: NotificationChannel
    status: NotificationStatus = NotificationStatus.PENDING
    reference_type: Optional[str] = None  # e.g. product, order
    reference_id: Optional[str] = None

    sent_at: Optional[str] = None
    read_at: Optional[str] = None

    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
