# File: domain/auth/entities/session_entity.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
from uuid import uuid4


class Session(BaseModel):
    """Model representing a user session."""

    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique session identifier")
    user_id: str = Field(..., description="Identifier of the user owning the session")

    # Device Info
    device_name: Optional[str] = Field(default=None, description="Name of the device")
    device_type: Optional[str] = Field(default=None, description="Type of device (e.g., mobile, desktop)")
    os: Optional[str] = Field(default=None, description="Operating system")
    browser: Optional[str] = Field(default=None, description="Browser name")
    user_agent: Optional[str] = Field(default=None, description="Full user agent string")

    # Security Info
    ip_address: Optional[str] = Field(default=None, description="IP address of the session")
    location: Optional[str] = Field(default=None, description="Approximate location")

    # Status
    is_active: bool = Field(default=True, description="Whether the session is active")

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Session creation time"
    )
    last_seen_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last activity time"
    )

    class Config:
        """Pydantic configuration for the Session model."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }