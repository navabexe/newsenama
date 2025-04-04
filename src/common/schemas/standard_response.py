# File: common/schemas/standard_response.py

from typing import Any, Optional, Literal
from pydantic import BaseModel, Field


class MetaData(BaseModel):
    message: Optional[str] = Field(None, examples=["Operation completed successfully."])
    status: Literal["success", "error"] = Field(..., examples=["success"])


class StandardResponse(BaseModel):
    data: Optional[Any] = Field(None, description="Payload or result")
    meta: MetaData = Field(..., description="Standard metadata with status and message")


class ErrorResponse(BaseModel):
    detail: str = Field(..., examples=["Invalid credentials."])
    error_code: Optional[str] = Field(None, examples=["AUTH_001"])
    status: Literal["error"] = "error"
