from datetime import datetime, timezone
from typing import Optional, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator

from common.validators.phone import validate_and_format_phone
from common.translations.messages import get_message


class RequestOTPInput(BaseModel):
    """Request model for requesting an OTP code."""

    phone: str = Field(..., min_length=10, description="Phone number in international format (e.g., +989123456789)")
    role: Literal["user", "vendor"] = Field(..., description="Role requesting OTP")
    purpose: Literal["login", "signup", "password_reset"] = Field(default="login", description="Purpose of the OTP")
    response_language: str = Field(default="fa", description="Preferred response language")
    request_id: Optional[str] = Field(default=None, description="Request identifier for tracing")
    client_version: Optional[str] = Field(default=None, description="Version of the client app")
    device_fingerprint: Optional[str] = Field(default=None, description="Unique device fingerprint (optional)")

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        try:
            return validate_and_format_phone(v)
        except ValueError as e:
            raise ValueError(get_message("phone.invalid"))

    @field_validator("response_language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        allowed = ["fa", "en", "ar"]
        if v not in allowed:
            raise ValueError(get_message("language.unsupported", v))
        return v

    @field_validator("request_id")
    @classmethod
    def validate_request_id(cls, v: Optional[str]) -> Optional[str]:
        if v and len(v) > 36:
            raise ValueError(get_message("request_id.too_long"))
        return v

    @field_validator("client_version")
    @classmethod
    def validate_client_version(cls, v: Optional[str]) -> Optional[str]:
        if v and len(v) > 15:
            raise ValueError(get_message("client_version.too_long"))
        return v


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
