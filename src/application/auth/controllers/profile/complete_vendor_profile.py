# File: application/auth/controllers/profile/complete_vendor_profile.py
from fastapi import APIRouter, Request, HTTPException, status, Depends
from redis.asyncio import Redis

from common.translations.messages import get_message
from domain.auth.auth_services.auth_service.complete_profile import complete_profile_service
from domain.auth.entities.auth_models import CompleteVendorProfile
from infrastructure.database.redis.redis_client import get_redis_client

router = APIRouter()

@router.post("/complete-vendor-profile", status_code=status.HTTP_200_OK)
async def complete_vendor_profile(
    data: CompleteVendorProfile,
    request: Request,
    redis: Redis = Depends(get_redis_client),
):
    """
    Complete a vendor's profile using provided data.

    Args:
        data (CompleteVendorProfile): Vendor profile data.
        request (Request): FastAPI request object.
        redis (Redis): Redis client instance.

    Returns:
        dict: Response with access token, status, and message.
    """
    try:
        return await complete_profile_service(
            temporary_token=data.temporary_token,
            business_name=data.business_name,
            first_name=data.first_name,
            last_name=data.last_name,
            city=data.city,
            province=data.province,
            location=data.location.model_dump() if data.location else None,
            address=data.address,
            business_category_ids=data.business_category_ids,
            visibility=data.visibility,
            vendor_type=data.vendor_type,
            languages=data.preferred_languages,
            client_ip=request.client.host,
            language=data.response_language,
            redis=redis,
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_message("server.error", data.response_language),
        )