# 📄 File: domain/auth/entities/auth_models.py

from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr
from common.schemas.request_base import BaseRequestModel


# 📍 Location used in vendor profiles and tokens
class Location(BaseModel):
    lat: float = Field(ge=-90, le=90, description="Latitude")
    lng: float = Field(ge=-180, le=180, description="Longitude")


# 📍 Used in complete user profile request
class CompleteUserProfile(BaseRequestModel):
    temporary_token: str = Field(..., min_length=1, description="Temporary token from verify-otp")
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    email: EmailStr = Field(..., description="Valid email address")


# 📍 Used in complete vendor profile request
class CompleteVendorProfile(BaseRequestModel):
    temporary_token: str = Field(..., description="Temporary token from verify-otp")
    business_name: Optional[str] = Field(None, min_length=3, max_length=100)
    owner_name: Optional[str] = Field(None, min_length=2, max_length=100)
    city: Optional[str] = Field(None, min_length=2, max_length=50)
    province: Optional[str] = Field(None, min_length=2, max_length=50)
    location: Optional[Location] = Field(None)
    address: Optional[str] = Field(None, min_length=5, max_length=200)
    business_category_ids: Optional[List[str]] = Field(None)

    @classmethod
    def validate_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip() if v else None

    @classmethod
    def validate_category_ids(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None and not v:
            raise ValueError("Business category IDs list cannot be empty")
        return v

    model_config = {
        "str_strip_whitespace": True,
        "extra": "forbid"
    }


# 📍 Optional profile included in JWT
class UserProfile(BaseModel):
    first_name: Optional[str]
    last_name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    business_name: Optional[str]
    address: Optional[str]
    location: Optional[Location]
    status: Optional[str]
    business_category_ids: Optional[List[str]]
    profile_picture: Optional[str]


# 📍 Payload inside any JWT (access, temp, refresh)
class TokenPayload(BaseModel):
    sub: str
    role: str
    scopes: List[str] = Field(default_factory=list)
    status: Optional[str] = None
    vendor_id: Optional[str] = None
    active_role: Optional[str] = None
    phone_verified: Optional[bool] = None
    account_verified: Optional[bool] = None
    jti: Optional[str] = None
    session_id: Optional[str] = None
    iat: Optional[int] = None
    exp: int
    language: Optional[str] = "fa"
    user_profile: Optional[UserProfile] = None
