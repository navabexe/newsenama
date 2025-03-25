# File: application/auth/controllers/auth/force_logout.py

from fastapi import APIRouter, Request, Depends
from pydantic import BaseModel, Field
from common.security.jwt_handler import get_current_user
from domain.auth.auth_services.auth_service.force_logout import force_logout_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

class ForceLogoutRequest(BaseModel):
    target_user_id: str = Field(..., description="ID of the user to force logout")

@router.post("/force-logout", status_code=200)
async def force_logout(data: ForceLogoutRequest, request: Request, current_user: dict = Depends(get_current_user)):
    """Force logout a specific user (admin only)."""
    return await force_logout_service(current_user, data.target_user_id, request.client.host)