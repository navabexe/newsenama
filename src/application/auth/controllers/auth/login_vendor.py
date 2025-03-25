from fastapi import APIRouter, Request, HTTPException, status
from pydantic import BaseModel, Field
from domain.auth.auth_services.auth_service.login_vendor import login_vendor_service

router = APIRouter(tags=["Authentication"])

class LoginVendorRequest(BaseModel):
    phone: str = Field(min_length=10, pattern=r"^\+?\d+$", description="Vendor's phone number")
    password: str = Field(min_length=8, description="Vendor's password")

@router.post("/login-vendor", status_code=status.HTTP_200_OK)
async def login_vendor(request: Request, data: LoginVendorRequest):
    try:
        return await login_vendor_service(data.phone, data.password, request.client.host)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Login failed")