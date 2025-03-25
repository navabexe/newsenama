from pydantic.v1 import BaseModel, Field
from typing import Optional, List
from datetime import datetime, UTC
from enum import Enum

class CategoryType(str, Enum):
    PRODUCT = "product"
    BUSINESS = "business"

class LocalizedField(BaseModel):
    language_code: str  # e.g. "en", "fa"
    value: str

class Category(BaseModel):
    id: Optional[str] = None
    type: CategoryType
    title: List[LocalizedField]
    description: Optional[List[LocalizedField]] = Field(default_factory=list)
    parent_id: Optional[str] = None
    is_active: bool = True
    is_system: bool = False  # cannot be deleted
    is_default_fallback: bool = False  # target fallback category

    image_url: Optional[str] = None
    icon: Optional[str] = None

    # Counters
    products_count: int = 0
    vendors_count: int = 0

    created_by: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_by: Optional[str] = None
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
