# File: domain/auth/entities/vendor_profile.py

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List

class Location(BaseModel):
    lat: float = Field(..., description="Latitude")
    lng: float = Field(..., description="Longitude")

class CompleteVendorProfile(BaseModel):
    temporary_token: str = Field(..., description="Temporary token from verify-otp")
    business_name: Optional[str] = Field(None, min_length=3, description="Vendor's business name")
    owner_name: Optional[str] = Field(None, min_length=2, description="Owner's name")
    city: Optional[str] = Field(None, min_length=2, description="City")
    province: Optional[str] = Field(None, min_length=2, description="Province")
    location: Optional[Location] = Field(None, description="Geographic location (lat, lng)")
    address: Optional[str] = Field(None, min_length=5, description="Business address")
    business_category_ids: Optional[List[str]] = Field(None, description="List of business category IDs")

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