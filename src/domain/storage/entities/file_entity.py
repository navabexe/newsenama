from pydantic.v1 import BaseModel, Field
from typing import Optional
from datetime import datetime, UTC
from enum import Enum

class FileType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    OTHER = "other"

class StorageFile(BaseModel):
    id: Optional[str] = None
    url: str
    filename: str
    file_type: FileType
    extension: Optional[str] = None
    size_bytes: Optional[int] = None

    uploaded_by: Optional[str] = None
    uploaded_for: Optional[str] = None  # e.g. product_id, vendor_id
    tag: Optional[str] = None  # e.g. "product_main_image"

    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
