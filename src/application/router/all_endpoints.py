# File: application/router/all_endpoints.py

from fastapi import APIRouter

# Auth modules
from application.auth.auth import login, refresh_token, logout, force_logout
from application.auth.sessions import sessions
from application.auth.admin import approve_vendor
from application.auth.profile import complete_user_profile, complete_vendor_profile
from application.auth.otp import request_otp, verify_otp

# Utility & Notifications
from application.notification.send_notification import router as send_notification_router
from application.router.utility_routes import router as utility_router

# Main router
all_routers = APIRouter()

# Include routers
all_routers.include_router(login.router)
all_routers.include_router(refresh_token.router)
all_routers.include_router(logout.router)
all_routers.include_router(force_logout.router)

all_routers.include_router(sessions.router)
all_routers.include_router(approve_vendor.router)

all_routers.include_router(complete_user_profile.router)
all_routers.include_router(complete_vendor_profile.router)

all_routers.include_router(request_otp.router)
all_routers.include_router(verify_otp.router)

all_routers.include_router(send_notification_router)
all_routers.include_router(utility_router)
