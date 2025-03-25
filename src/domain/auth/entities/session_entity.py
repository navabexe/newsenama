from pydantic.v1 import BaseModel, Field
from typing import Optional
from datetime import datetime, UTC

class Session(BaseModel):
    id: Optional[str] = None
    user_id: str

    # Device Info
    device_name: Optional[str] = None         # Friendly name shown to user
    device_type: Optional[str] = None         # e.g. "mobile", "desktop", "tablet"
    os: Optional[str] = None                  # e.g. "iOS", "Windows", "Android"
    browser: Optional[str] = None             # e.g. "Chrome", "Safari"
    user_agent: Optional[str] = None

    # Security Info
    ip_address: Optional[str] = None
    location: Optional[str] = None            # Extracted from IP (e.g. "Tehran, Iran")

    # Status
    is_active: bool = True

    # Timestamps
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    last_seen_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
