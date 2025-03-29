from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime, UTC
from enum import Enum


class UserStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNDISCLOSED = "undisclosed"


class User(BaseModel):
    id: Optional[str] = None
    phone: str
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    password: Optional[str] = None  # hashed password

    roles: List[str] = Field(default_factory=lambda: ["user"])
    status: UserStatus = UserStatus.PENDING

    bio: Optional[str] = None
    avatar_urls: List[str] = Field(default_factory=list)
    additional_phones: List[str] = Field(default_factory=list)
    birthdate: Optional[str] = None
    gender: Gender = Gender.UNDISCLOSED
    languages: List[str] = Field(default_factory=list)

    # Counters
    orders_count: int = 0
    likes_count: int = 0
    following_count: int = 0
    followers_count: int = 0
    reports_count: int = 0

    created_by: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_by: Optional[str] = None
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
