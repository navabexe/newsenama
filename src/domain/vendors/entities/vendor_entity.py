from pydantic.v1 import BaseModel, Field
from typing import List, Optional
from datetime import datetime, UTC
from enum import Enum


class VendorVisibility(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    COLLABORATIVE = "collaborative"
    TEMPORARILY_CLOSED = "temporarily_closed"


class VendorStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"


class Location(BaseModel):
    lat: float
    lng: float


class Branch(BaseModel):
    label: str
    city: str
    province: str
    address: str
    location: Location
    phones: List[str] = Field(default_factory=list)
    emails: List[str] = Field(default_factory=list)


class BusinessDetail(BaseModel):
    type: str
    values: List[str] = Field(default_factory=list)


class SocialLink(BaseModel):
    platform: str
    url: str


class MessengerLink(BaseModel):
    platform: str
    url: str


class VendorName(BaseModel):
    language_code: str
    name: str


class VendorDescription(BaseModel):
    language_code: str
    description: str


class Vendor(BaseModel):
    id: Optional[str] = None
    username: str
    names: List[VendorName]
    owner_name: str
    owner_phone: str
    address: str
    location: Location
    city: str
    province: str
    logo_urls: List[str] = Field(default_factory=list)
    banner_urls: List[str] = Field(default_factory=list)
    short_descriptions: List[VendorDescription] = Field(default_factory=list)
    about_us: List[VendorDescription] = Field(default_factory=list)
    branches: List[Branch] = Field(default_factory=list)
    business_details: List[BusinessDetail] = Field(default_factory=list)
    visibility: VendorVisibility = VendorVisibility.PUBLIC
    status: VendorStatus = VendorStatus.PENDING
    attached_vendor_ids: List[str] = Field(default_factory=list)
    blocked_vendor_ids: List[str] = Field(default_factory=list)
    account_types: List[str] = Field(default_factory=lambda: ["free"])
    vendor_type: Optional[str] = Field(default="basic")
    social_links: List[SocialLink] = Field(default_factory=list)
    messenger_links: List[MessengerLink] = Field(default_factory=list)
    show_followers_publicly: bool = True  # if False → followers hidden from other vendors

    terms_version: Optional[str] = "v1.0"
    accepted_terms_at: Optional[str] = None

    # Counters
    products_count: int = 0
    followers_count: int = 0
    following_count: int = 0
    likes_count: int = 0
    orders_count: int = 0
    attached_products_count: int = 0
    products_attached_from_others_count: int = 0

    business_category_ids: List[str] = Field(default_factory=list)
    created_by: str
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_by: Optional[str] = None
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
