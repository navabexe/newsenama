from pydantic import BaseModel, Field
from typing import Optional, List


class UserJWTProfile(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    avatar_urls: Optional[List[str]] = []
    additional_phones: Optional[List[str]] = []
    birthdate: Optional[str] = None
    gender: Optional[str] = None
    preferred_languages: Optional[List[str]] = []
    status: Optional[str] = None


class VendorJWTProfile(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    location: Optional[dict] = None
    city: Optional[str] = None
    province: Optional[str] = None
    logo_urls: Optional[List[str]] = []
    banner_urls: Optional[List[str]] = []
    visibility: Optional[str] = None
    status: Optional[str] = None
    business_category_ids: Optional[List[str]] = []
    preferred_languages: Optional[List[str]] = []
    vendor_type: Optional[str] = None
    account_types: Optional[List[str]] = []
    show_followers_publicly: Optional[bool] = True
    profile_picture: Optional[str] = None


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
    preferred_locale: Optional[str] = None
    user_profile: Optional[UserJWTProfile] = None
    vendor_profile: Optional[VendorJWTProfile] = None
