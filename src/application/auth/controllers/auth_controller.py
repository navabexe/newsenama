from fastapi import APIRouter
from .auth.request_otp import router as request_otp_router
from .auth.verify_otp import router as verify_otp_router
from .auth.complete_user_profile import router as complete_user_profile_router
from .auth.complete_vendor_profile import router as complete_vendor_profile_router
from .auth.refresh_token import router as refresh_token_router
from .auth.logout import router as logout_router
from .auth.logout_all import router as logout_all_router
from .auth.force_logout import router as force_logout_router
from .auth.login_password import router as login_password_router
from .auth.request_account_deletion import router as request_account_deletion_router
from .auth.send_otp import router as send_otp_router
from .auth.sessions import router as sessions_router
from .auth.login_vendor import router as login_vendor_router
from .auth.approve_vendor import router as approve_vendor_router
from .auth.login_admin import router as login_admin_router
router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    responses={404: {"description": "Route not found"}}
)

# Include all auth-related routers
router.include_router(request_otp_router)
router.include_router(verify_otp_router)
router.include_router(complete_user_profile_router)
router.include_router(complete_vendor_profile_router)
router.include_router(refresh_token_router)
router.include_router(logout_router)
router.include_router(logout_all_router)
router.include_router(force_logout_router)
router.include_router(login_password_router)
router.include_router(request_account_deletion_router)
router.include_router(send_otp_router)
router.include_router(sessions_router)
router.include_router(login_vendor_router)
router.include_router(approve_vendor_router)
router.include_router(login_admin_router)