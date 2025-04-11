from datetime import datetime, UTC
from enum import Enum
from typing import Optional

from pydantic.v1 import BaseModel, Field


class AdminRole(str, Enum):
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

class Admin(BaseModel):
    id: Optional[str] = None
    phone: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: AdminRole = AdminRole.ADMIN
    is_active: bool = True
    is_2fa_enabled: bool = False

    password_hash: str
    failed_attempts: int = 0
    locked_until: Optional[str] = None

    last_login_ip: Optional[str] = None
    last_login_at: Optional[str] = None

    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
