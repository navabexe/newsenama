from pydantic.v1 import BaseModel, Field
from typing import Optional
from datetime import datetime, UTC

class Follower(BaseModel):
    id: Optional[str] = None
    follower_user_id: str
    followed_vendor_id: str

    followed_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    class Config:
        indexes = [
            {"fields": ["follower_user_id", "followed_vendor_id"], "unique": True}
        ]
