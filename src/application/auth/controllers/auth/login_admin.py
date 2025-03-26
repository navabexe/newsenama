from fastapi import APIRouter, Request, HTTPException, status
from pydantic import BaseModel, Field
from domain.auth.auth_services.auth_service.login_admin import login_admin_service

router = APIRouter(tags=["Authentication"])

class LoginAdminRequest(BaseModel):
    username: str = Field(
        min_length=3,
        max_length=50,
        description="Admin username (e.g., navabexe)"
    )
    password: str = Field(
        min_length=8,
        max_length=128,
        description="Admin password"
    )

    model_config = {
        "str_strip_whitespace": True,
        "extra": "forbid"
    }

@router.post("/login-admin", status_code=status.HTTP_200_OK)
async def login_admin(data: LoginAdminRequest, request: Request):
    """Login admin with username and password."""
    try:
        return await login_admin_service(data.username, data.password, request.client.host)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to login admin")