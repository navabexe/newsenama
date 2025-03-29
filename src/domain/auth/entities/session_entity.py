from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, UTC


class Session(BaseModel):
    id: Optional[str] = None
    user_id: str

    # Device Info
    device_name: Optional[str] = None
    device_type: Optional[str] = None
    os: Optional[str] = None
    browser: Optional[str] = None
    user_agent: Optional[str] = None

    # Security Info
    ip_address: Optional[str] = None
    location: Optional[str] = None

    # Status
    is_active: bool = True

    # Timestamps
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    last_seen_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())