from typing import Optional, List

from pydantic.v1 import BaseModel, Field

class UserProfile(BaseModel):
    first_name: Optional[str]
    last_name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    business_name: Optional[str]
    address: Optional[str]
    location: Optional[dict]
    status: Optional[str]
    business_category_ids: Optional[List[str]]
    profile_picture: Optional[str]

class TokenPayload(BaseModel):
    sub: str
    role: str
    scopes: List[str] = Field(default_factory=list)
    status: Optional[str] = None
    vendor_id: Optional[str] = None
    active_role: Optional[str] = None
    phone_verified: Optional[bool] = None
    account_verified: Optional[bool] = None
    jti: Optional[str] = None
    iat: Optional[int] = None
    exp: int
    session_id: Optional[str] = None
    language: Optional[str] = None
    user_profile: Optional[UserProfile] = None

