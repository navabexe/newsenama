# File: application/auth/controllers/auth/request_account_deletion.py

from fastapi import APIRouter, Request, Depends
from common.security.jwt_handler import get_current_user
from domain.auth.auth_services.auth_service.request_account_deletion import request_account_deletion_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/request-account-deletion", status_code=200)
async def request_account_deletion(request: Request, current_user: dict = Depends(get_current_user)):
    """Request account deletion for the current user."""
    return await request_account_deletion_service(current_user["user_id"], request.client.host)