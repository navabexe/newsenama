from pydantic.v1 import BaseModel, Field
from typing import Optional
from datetime import datetime, UTC
from enum import Enum

class ReportTargetType(str, Enum):
    PRODUCT = "product"
    VENDOR = "vendor"
    USER = "user"
    MESSAGE = "message"
    STORY = "story"
    ADVERTISEMENT = "advertisement"

class ReportReason(str, Enum):
    SPAM = "spam"
    INAPPROPRIATE = "inappropriate"
    FAKE = "fake"
    COPYRIGHT = "copyright"
    OTHER = "other"

class Report(BaseModel):
    id: Optional[str] = None
    reporter_id: str  # who submitted the report
    target_id: str
    target_type: ReportTargetType
    reason: ReportReason
    message: Optional[str] = None  # custom explanation by reporter
    is_resolved: bool = False
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None

    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
