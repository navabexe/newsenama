from pydantic.v1 import BaseModel, Field
from typing import Optional
from datetime import datetime, UTC
from enum import Enum

class LikeTargetType(str, Enum):
    PRODUCT = "product"
    VENDOR = "vendor"
    STORY = "story"
    ADVERTISEMENT = "advertisement"

class Like(BaseModel):
    id: Optional[str] = None
    user_id: str
    target_id: str  # ID of the liked entity (product, vendor, ...)
    target_type: LikeTargetType

    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    class Config:
        indexes = [
            {"fields": ["user_id", "target_id", "target_type"], "unique": True}
        ]
