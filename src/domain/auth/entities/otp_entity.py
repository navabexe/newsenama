# File: domain/auth/entities/otp_entity.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone


class OTP(BaseModel):
    """Model representing an OTP (One-Time Password) entity."""

    phone: str = Field(..., description="Phone number associated with the OTP")
    code: str = Field(..., description="Generated OTP code")
    purpose: str = Field(default="login", description="Purpose of the OTP (e.g., login, signup)")
    attempts: int = Field(default=0, ge=0, description="Number of verification attempts")
    channel: Optional[str] = Field(default="sms", description="Delivery channel (e.g., sms, email)")
    ip_address: Optional[str] = Field(default=None, description="IP address of the request")
    device_fingerprint: Optional[str] = Field(default=None, description="Device fingerprint for security")
    expires_at: datetime = Field(..., description="Expiration time of the OTP")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation time of the OTP"
    )

    class Config:
        """Pydantic configuration for the OTP model."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }