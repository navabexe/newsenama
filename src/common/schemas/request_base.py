# File: common/schemas/request_base.py

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal


class BaseRequestModel(BaseModel):
    """Base request model with common fields for all API requests."""

    response_language: Literal["fa", "en"] = Field(
        default="fa",
        description="Language code for API response messages (e.g., 'fa' for Persian, 'en' for English')"
    )

    request_id: Optional[str] = Field(
        default=None,
        description="Optional unique ID for tracing the request across services"
    )

    client_version: Optional[str] = Field(
        default=None,
        description="Client version (e.g., 'v1.2.3')"
    )

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_by_name=True,
    )
