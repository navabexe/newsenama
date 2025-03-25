from pydantic.v1 import BaseModel, Field
from typing import Optional
from datetime import datetime, UTC

class OTP(BaseModel):
    phone: str
    code: str
    purpose: str = "login"
    attempts: int = 0
    channel: Optional[str] = "sms"
    ip_address: Optional[str] = None
    device_fingerprint: Optional[str] = None
    expires_at: str
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
