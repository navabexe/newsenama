# File: application/auth/controllers/auth/sessions.py

from fastapi import APIRouter, Request, Depends
from common.security.jwt_handler import get_current_user
from domain.auth.auth_services.session_service.read import get_sessions_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.get("/sessions", status_code=200)
async def get_sessions(request: Request, current_user: dict = Depends(get_current_user)):
    """Retrieve all active sessions for the current user."""
    return await get_sessions_service(current_user["user_id"], request.client.host)