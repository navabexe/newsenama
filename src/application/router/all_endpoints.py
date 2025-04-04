# application/router/all_endpoints.py
from fastapi import APIRouter

from application.auth.auth import (
    request_account_deletion,
    sessions,
    login,
    refresh_token,
    approve_vendor,
    logout,
    force_logout
)
from application.auth.profile import (
    complete_user_profile,
    complete_vendor_profile
)
from application.auth.otp import (
    request_otp,
    verify_otp
)


all_routers = APIRouter()

# Include your smaller routers in the 'all_routers' APIRouter
all_routers.include_router(request_otp.router)
all_routers.include_router(verify_otp.router)
all_routers.include_router(complete_user_profile.router)
all_routers.include_router(complete_vendor_profile.router)
all_routers.include_router(refresh_token.router)
all_routers.include_router(logout.router)
all_routers.include_router(force_logout.router)
all_routers.include_router(request_account_deletion.router)
all_routers.include_router(sessions.router)
all_routers.include_router(approve_vendor.router)
all_routers.include_router(login.router)
