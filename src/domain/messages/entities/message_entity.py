from pydantic.v1 import BaseModel, Field
from typing import List, Optional
from datetime import datetime, UTC
from enum import Enum

class MessageStatus(str, Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    DELETED = "deleted"

class ParticipantType(str, Enum):
    USER = "user"
    VENDOR = "vendor"
    ADMIN = "admin"

class MessageParticipant(BaseModel):
    participant_id: str
    participant_type: ParticipantType

class MessageThread(BaseModel):
    id: Optional[str] = None
    participants: List[MessageParticipant] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

class Message(BaseModel):
    id: Optional[str] = None
    thread_id: str
    sender: MessageParticipant
    content: str
    status: MessageStatus = MessageStatus.SENT

    # Optional Attachments
    media_urls: List[str] = Field(default_factory=list)

    sent_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    delivered_at: Optional[str] = None
    read_at: Optional[str] = None
    deleted_at: Optional[str] = None

    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
