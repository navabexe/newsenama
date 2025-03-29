from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from common.schemas.request_base import BaseRequestModel

class Location(BaseModel):
    lat: float = Field(ge=-90, le=90, description="Latitude")
    lng: float = Field(ge=-180, le=180, description="Longitude")


# CompleteVendorProfile و CompleteUserProfile در auth_models.py

class CompleteUserProfile(BaseRequestModel):
    temporary_token: str = Field(min_length=1, description="Temporary token from verify-otp")
    first_name: str = Field(min_length=2, max_length=50)
    last_name: str = Field(min_length=2, max_length=50)
    email: EmailStr = Field(description="Valid email address")
    bio: Optional[str] = Field(default=None, max_length=500)
    avatar_urls: Optional[List[str]] = Field(default_factory=list)
    additional_phones: Optional[List[str]] = Field(default_factory=list)
    birthdate: Optional[str] = Field(default=None, description="ISO format date string")
    gender: Optional[str] = Field(default=None)
    languages: Optional[List[str]] = Field(default_factory=list)
    preferred_locale: Optional[str] = Field(default="fa", description="Preferred language for messages")

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid"
    )


class CompleteVendorProfile(BaseRequestModel):
    temporary_token: str = Field(description="Temporary token from verify-otp")
    business_name: Optional[str] = Field(default=None, min_length=3, max_length=100)
    first_name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    last_name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    city: Optional[str] = Field(default=None, min_length=2, max_length=50)
    province: Optional[str] = Field(default=None, min_length=2, max_length=50)
    location: Optional[Location] = Field(default=None)
    address: Optional[str] = Field(default=None, min_length=5, max_length=200)
    business_category_ids: Optional[List[str]] = Field(default=None)
    visibility: Optional[str] = Field(default="COLLABORATIVE")
    vendor_type: Optional[str] = Field(default=None)
    languages: Optional[List[str]] = Field(default_factory=list)
    preferred_locale: Optional[str] = Field(default="fa", description="Preferred language for messages")

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid"
    )
