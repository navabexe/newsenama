# File: application/auth/controllers/profile/complete_vendor_profile.py

from fastapi import APIRouter, Request, HTTPException, status, Depends
from redis.asyncio import Redis
from typing import Annotated

from common.translations.messages import get_message
from domain.auth.auth_services.auth_service.complete_profile import complete_profile_service
from domain.auth.entities.auth_models import CompleteVendorProfile
from infrastructure.database.redis.redis_client import get_redis_client
from common.logging.logger import log_info, log_error

router = APIRouter()


@router.post(
    "/complete-vendor-profile",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Vendor profile completed successfully."},
        400: {"description": "Validation failed."},
        500: {"description": "Internal server error."}
    }
)
async def complete_vendor_profile(
    data: CompleteVendorProfile,
    request: Request,
    redis: Annotated[Redis, Depends(get_redis_client)]
):
    """
    Complete a vendor's profile using provided data.
    """
    try:
        result = await complete_profile_service(
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
        log_info("Vendor profile completed", extra={"ip": request.client.host, "vendor": data.business_name})
        return result

    except HTTPException as e:
        log_error("Complete vendor profile HTTPException", extra={"detail": str(e.detail)})
        raise

    except Exception as e:
        log_error("Unexpected error in vendor profile completion", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_message("server.error", data.response_language),
        )