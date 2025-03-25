from fastapi import APIRouter, Request, HTTPException, status
from pydantic import BaseModel, Field, model_validator  # اضافه کردن model_validator
import phonenumbers
from domain.auth.auth_services.otp_service.request import request_otp_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

class RequestOTP(BaseModel):
    phone: str = Field(
        description="User's phone number in international format (e.g., +989123456789)"
    )
    role: str = Field(
        pattern=r"^(user|vendor)$",
        description="User role: 'user' or 'vendor'"
    )
    purpose: str = Field(
        pattern=r"^(login|signup)$",
        description="Purpose: 'login' or 'signup'"
    )

    @model_validator(mode="after")
    def validate_phone(self) -> "RequestOTP":
        try:
            parsed = phonenumbers.parse(self.phone)
            if not phonenumbers.is_valid_number(parsed):
                raise ValueError("Invalid phone number")
            self.phone = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
            return self
        except phonenumbers.NumberParseException:
            raise ValueError("Phone number must be in international format (e.g., +989123456789)")

    model_config = {
        "str_strip_whitespace": True,
        "extra": "forbid"
    }

@router.post("/request-otp", status_code=status.HTTP_200_OK)
async def request_otp(data: RequestOTP, request: Request):
    """Request an OTP for login or signup."""
    try:
        return await request_otp_service(data.phone, data.role, data.purpose, request.client.host)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to request OTP")