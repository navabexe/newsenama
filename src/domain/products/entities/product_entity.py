from pydantic.v1 import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime, UTC

class PriceVariant(BaseModel):
    variant_name: str  # e.g., "8 seats", "5 seats"
    prices: Dict[str, float]  # currency_code: amount (e.g., {"USD": 100, "EUR": 90})

class PricingDetails(BaseModel):
    customer_prices: List[PriceVariant]
    vendor_prices: List[PriceVariant]

class ProductName(BaseModel):
    language_code: str
    name: str

class ProductDescription(BaseModel):
    language_code: str
    description: str

class ColorVariant(BaseModel):
    name: str
    hex_code: Optional[str] = None
    images: List[str] = Field(default_factory=list)

class MediaFile(BaseModel):
    url: str
    media_type: str  # "image", "video", "audio"
    label: Optional[str] = None

class TechnicalSpec(BaseModel):
    key: str
    value: str

class Product(BaseModel):
    id: Optional[str] = None
    vendor_id: str
    names: List[ProductName]
    short_descriptions: List[ProductDescription] = Field(default_factory=list)
    detailed_descriptions: List[ProductDescription] = Field(default_factory=list)
    pricing_details: PricingDetails
    colors: List[ColorVariant] = Field(default_factory=list)
    media_files: List[MediaFile] = Field(default_factory=list)
    technical_specs: List[TechnicalSpec] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    thumbnail_urls: List[str] = Field(default_factory=list)
    suggested_product_ids: List[str] = Field(default_factory=list)
    status: str = Field(default="pending")
    qr_code_url: Optional[str] = None
    category_ids: List[str] = Field(default_factory=list)
    subcategory_ids: List[str] = Field(default_factory=list)

    # Counters
    attachments_count: int = 0
    likes_count: int = 0
    orders_count: int = 0
    views_count: int = 0

    created_by: str
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_by: Optional[str] = None
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
