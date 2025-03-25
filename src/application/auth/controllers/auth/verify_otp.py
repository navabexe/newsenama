from fastapi import APIRouter, Request, HTTPException, status
from pydantic import BaseModel, Field
from domain.auth.auth_services.otp_service.verify import verify_otp_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

class VerifyOTP(BaseModel):
    otp: str = Field(
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="6-digit one-time password"
    )
    temporary_token: str = Field(
        min_length=1,
        description="Temporary token from request-otp"
    )

    model_config = {
        "str_strip_whitespace": True,
        "extra": "forbid"
    }

@router.post("/verify-otp", status_code=status.HTTP_200_OK)
async def verify_otp(data: VerifyOTP, request: Request):
    """Verify OTP and return tokens or instructions for next step."""
    try:
        return await verify_otp_service(data.otp, data.temporary_token, request.client.host)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to verify OTP")