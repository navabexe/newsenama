from datetime import datetime, UTC
from enum import Enum
from typing import List, Optional

from pydantic.v1 import BaseModel, Field


class OrderStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    SHIPPED = "shipped"
    DELIVERED = "delivered"

class PriceDetails(BaseModel):
    total_amount: float
    currency: str  # e.g., "USD", "EUR"
    discounts: Optional[float] = 0
    final_amount: float

class OrderItem(BaseModel):
    product_id: str
    vendor_id: str
    variant_name: Optional[str] = None  # e.g., "8 seats"
    quantity: int
    unit_price: float
    total_price: float
    currency: str

class ShippingDetails(BaseModel):
    receiver_name: str
    address: str
    city: str
    province: str
    country: str
    postal_code: str
    phone_number: str
    additional_notes: Optional[str] = None

class Order(BaseModel):
    id: Optional[str] = None
    customer_id: str
    items: List[OrderItem]
    shipping_details: ShippingDetails
    price_details: PriceDetails
    status: OrderStatus = OrderStatus.PENDING
    placed_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    approved_at: Optional[str] = None
    shipped_at: Optional[str] = None
    delivered_at: Optional[str] = None
    cancelled_at: Optional[str] = None

    # Counters & Metrics
    total_items_count: int = Field(default=0)
    total_vendors_count: int = Field(default=0)

    created_by: str  # User who created order
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_by: Optional[str] = None
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
