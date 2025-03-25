from pydantic.v1 import BaseModel, Field
from typing import Optional
from datetime import datetime, UTC
from enum import Enum

class BlockedEntityType(str, Enum):
    USER = "user"
    VENDOR = "vendor"

class Block(BaseModel):
    id: Optional[str] = None
    blocker_id: str
    blocker_type: BlockedEntityType  # who blocked
    blocked_id: str
    blocked_type: BlockedEntityType  # who was blocked

    reason: Optional[str] = None
    is_permanent: bool = True
    expires_at: Optional[str] = None

    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
