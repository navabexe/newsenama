# File: application/auth/controllers/auth/send_otp.py

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from domain.auth.auth_services.otp_service.send import send_otp_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

class SendOTP(BaseModel):
    phone: str = Field(..., min_length=10, pattern=r"^\d+$", description="User's phone number")

@router.post("/send-otp", status_code=200)
async def send_otp(data: SendOTP, request: Request):
    """Send an OTP to the user's phone."""
    return await send_otp_service(data.phone, request.client.host)