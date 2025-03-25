from pydantic.v1 import BaseModel, Field
from typing import List, Optional
from datetime import datetime, UTC

class Permission(BaseModel):
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    created_by: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_by: Optional[str] = None
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

class Role(BaseModel):
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)  # permission IDs

    # Counters
    users_count: int = 0

    created_by: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_by: Optional[str] = None
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
