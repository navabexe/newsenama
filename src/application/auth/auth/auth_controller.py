# src/application/auth/controllers/auth_controller.py
from fastapi import APIRouter

from application.auth.auth import (
    request_account_deletion,
    sessions,
    login
)
from application.auth.auth import refresh_token, approve_vendor, logout, force_logout
from application.auth.profile import complete_user_profile, complete_vendor_profile
from application.auth.otp import request_otp, verify_otp

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    responses={
        404: {"description": "Route not found"},
        401: {"description": "Unauthorized"},
        400: {"description": "Bad request"}
    }
)

auth_routers = [
    request_otp.router,
    verify_otp.router,
    complete_user_profile.router,
    complete_vendor_profile.router,
    refresh_token.router,
    logout.router,
    force_logout.router,
    request_account_deletion.router,
    sessions.router,
    approve_vendor.router,
    login.router
]

for auth_router in auth_routers:
    router.include_router(auth_router)
