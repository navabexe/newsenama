# File: domain/auth/entities/auth_models.py

from pydantic import BaseModel, Field, field_validator, EmailStr
from typing import Optional, List
import phonenumbers

class Location(BaseModel):
    lat: float = Field(ge=-90, le=90, description="Latitude")
    lng: float = Field(ge=-180, le=180, description="Longitude")

class CompleteUserProfile(BaseModel):
    temporary_token: str = Field(..., min_length=1, description="Temporary token from verify-otp")
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    email: EmailStr = Field(..., description="Valid email address")

class CompleteVendorProfile(BaseModel):
    temporary_token: str = Field(..., description="Temporary token from verify-otp")
    business_name: Optional[str] = Field(None, min_length=3, max_length=100)
    owner_name: Optional[str] = Field(None, min_length=2, max_length=100)
    city: Optional[str] = Field(None, min_length=2, max_length=50)
    province: Optional[str] = Field(None, min_length=2, max_length=50)
    location: Optional[Location] = Field(None)
    address: Optional[str] = Field(None, min_length=5, max_length=200)
    business_category_ids: Optional[List[str]] = Field(None)

    @field_validator("business_name", "owner_name", "city", "province", "address")
    @classmethod
    def validate_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip() if v else None

    @field_validator("business_category_ids")
    @classmethod
    def validate_category_ids(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None and not v:
            raise ValueError("Business category IDs list cannot be empty")
        return v

    model_config = {
        "str_strip_whitespace": True,
        "extra": "forbid"
    }
