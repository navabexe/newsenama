# File: common/schemas/request_base.py
from pydantic import BaseModel, Field, ConfigDict


class BaseRequestModel(BaseModel):
    """Base request model with common fields for all API requests."""

    response_language: str = Field(
        default="fa",
        description="Language code for API response messages (e.g., 'fa' for Persian, 'en' for English)",
        pattern="^(fa|en)$"  # Restrict to supported languages
    )

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_by_name=True,
    )