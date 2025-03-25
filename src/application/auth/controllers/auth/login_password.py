from fastapi import APIRouter, Request, HTTPException, status
from pydantic import BaseModel, Field
from domain.auth.auth_services.auth_service.login_password import login_password_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

class LoginPasswordRequest(BaseModel):
    phone: str = Field(
        min_length=10,
        pattern=r"^\+?\d+$",
        description="User's phone number (e.g., +989123456789)"
    )
    password: str = Field(
        min_length=8,
        max_length=128,
        description="User's password"
    )

    model_config = {
        "str_strip_whitespace": True,
        "extra": "forbid"
    }

@router.post("/login-password", status_code=status.HTTP_200_OK)
async def login_password(data: LoginPasswordRequest, request: Request):
    """Login user with phone and password."""
    try:
        return await login_password_service(data.phone, data.password, request.client.host)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to login")