from pydantic.v1 import BaseModel, Field
from typing import Optional, List
from datetime import datetime, UTC

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
    session_id: Optional[str] = None
    exp: int
