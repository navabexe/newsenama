from pydantic import BaseModel, Field, model_validator
from typing import Optional, List

class Location(BaseModel):
    lat: float = Field(ge=-90, le=90, description="Latitude between -90 and 90")
    lng: float = Field(ge=-180, le=180, description="Longitude between -180 and 180")

class CompleteVendorProfile(BaseModel):
    temporary_token: str = Field(..., min_length=1, description="Temporary token from verify-otp")
    business_name: Optional[str] = Field(None, min_length=3, max_length=100, description="Vendor's business name")
    owner_name: Optional[str] = Field(None, min_length=2, max_length=100, description="Owner's name")
    city: Optional[str] = Field(None, min_length=2, max_length=50, description="City")
    province: Optional[str] = Field(None, min_length=2, max_length=50, description="Province")
    location: Optional[Location] = Field(None, description="Geographic location (lat, lng)")
    address: Optional[str] = Field(None, min_length=5, max_length=200, description="Business address")
    business_category_ids: Optional[List[str]] = Field(None, description="List of business category IDs")

    @model_validator(mode="after")
    def validate_not_empty(self) -> "CompleteVendorProfile":
        for field in ["business_name", "owner_name", "city", "province", "address"]:
            value = getattr(self, field)
            if value is not None and not value.strip():
                raise ValueError(f"{field} cannot be empty or whitespace")
            if value is not None:
                setattr(self, field, value.strip())

        if self.business_category_ids is not None and not self.business_category_ids:
            raise ValueError("business_category_ids list cannot be empty")

        return self

    model_config = {
        "str_strip_whitespace": True,
        "extra": "forbid"
    }