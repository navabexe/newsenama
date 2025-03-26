# File: application/auth/controllers/auth/complete_user_profile.py

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from domain.auth.auth_services.auth_service.complete_user_profile import complete_user_profile_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

class CompleteUserProfile(BaseModel):
    temporary_token: str = Field(..., description="Temporary token from verify-otp")
    first_name: str = Field(..., min_length=2, description="User's first name")
    last_name: str = Field(..., min_length=2, description="User's last name")
    email: str = Field(..., description="User's email address")

    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v or "." not in v:
            raise ValueError("Invalid email format")
        return v

@router.post("/complete-user-profile", status_code=200)
async def complete_user_profile(data: CompleteUserProfile, request: Request):
    """Complete a user's profile after OTP verification."""
    return await complete_user_profile_service(
        data.temporary_token, data.first_name, data.last_name, data.email, request.client.host
    )