from pydantic.v1 import BaseModel, Field
from typing import List, Optional
from datetime import datetime, UTC
from enum import Enum

class AdvertisementStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    EXPIRED = "expired"

class AdvertisementType(str, Enum):
    BANNER = "banner"
    PRODUCT = "product"
    STORE = "store"

class TargetAudience(BaseModel):
    locations: List[str] = Field(default_factory=list)
    genders: List[str] = Field(default_factory=list)  # e.g., ["male", "female"]
    age_ranges: List[str] = Field(default_factory=list)  # e.g., ["18-24", "25-34"]

class Advertisement(BaseModel):
    id: Optional[str] = None
    vendor_id: str
    title: str
    description: Optional[str] = None
    image_urls: List[str] = Field(default_factory=list)
    type: AdvertisementType
    status: AdvertisementStatus = AdvertisementStatus.PENDING
    target_audience: Optional[TargetAudience] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

    # Counters & Metrics
    views_count: int = 0
    clicks_count: int = 0

    created_by: str
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_by: Optional[str] = None
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

class Story(BaseModel):
    id: Optional[str] = None
    vendor_id: str
    media_url: str
    caption: Optional[str] = None
    expires_at: str

    # Counters & Metrics
    views_count: int = 0
    interactions_count: int = 0

    created_by: str
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_by: Optional[str] = None
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
