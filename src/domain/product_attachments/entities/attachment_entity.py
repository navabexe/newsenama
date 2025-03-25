from pydantic.v1 import BaseModel, Field
from typing import Optional
from datetime import datetime, UTC
from enum import Enum

class AttachmentStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

class AttachmentType(str, Enum):
    AUTO = "auto"
    OPEN = "open"
    REQUEST_BASED = "request_based"

class PriceDetails(BaseModel):
    original_price: float
    attached_price: float
    currency: str  # e.g., "USD", "EUR"

class ProductAttachment(BaseModel):
    id: Optional[str] = Field(default=None)
    owner_vendor_id: str = Field(...)
    attached_vendor_id: str = Field(...)
    product_id: str = Field(...)
    attachment_type: AttachmentType = Field(...)
    status: AttachmentStatus = Field(default=AttachmentStatus.PENDING)
    price_details: PriceDetails = Field(...)
    requested_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    approved_at: Optional[str] = Field(default=None)
    rejected_at: Optional[str] = Field(default=None)
    cancelled_at: Optional[str] = Field(default=None)

    created_by: str
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_by: Optional[str] = None
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

class ProductAutoAttachment(BaseModel):
    id: Optional[str] = Field(default=None)
    owner_vendor_id: str = Field(...)
    attached_vendor_id: str = Field(...)
    status: AttachmentStatus = Field(default=AttachmentStatus.PENDING)
    auto_sync: bool = Field(default=True)
    requested_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    approved_at: Optional[str] = Field(default=None)
    rejected_at: Optional[str] = Field(default=None)
    cancelled_at: Optional[str] = Field(default=None)

    created_by: str
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_by: Optional[str] = None
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
