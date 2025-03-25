# File: application/auth/controllers/auth/complete_vendor_profile.py

from fastapi import APIRouter, Request
from domain.auth.entities.auth_models import CompleteVendorProfile  # Import from auth_models
from domain.auth.auth_services.auth_service.complete_vendor_profile import complete_vendor_profile_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/complete-vendor-profile", status_code=200)
async def complete_vendor_profile(data: CompleteVendorProfile, request: Request):
    """Complete a vendor's profile incrementally after OTP verification."""
    return await complete_vendor_profile_service(
        data.temporary_token,
        data.business_name,
        data.owner_name,
        data.city,
        data.province,
        data.location,
        data.address,
        data.business_category_ids,
        request.client.host
    )