from pydantic.v1 import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime, UTC

class Event(BaseModel):
    id: Optional[str] = None
    actor_id: Optional[str] = None
    actor_type: Optional[str] = None
    action: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    is_sensitive: bool = False
    metadata: Optional[Dict] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
