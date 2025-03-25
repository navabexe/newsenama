# File: application/auth/controllers/auth/logout_all.py

from fastapi import APIRouter, Request, Depends
from common.security.jwt_handler import get_current_user
from domain.auth.auth_services.auth_service.logout_all import logout_all_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/logout-all", status_code=200)
async def logout_all(request: Request, current_user: dict = Depends(get_current_user)):
    """Log out from all active sessions."""
    return await logout_all_service(current_user["user_id"], request.client.host)