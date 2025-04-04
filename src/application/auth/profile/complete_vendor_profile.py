from fastapi import APIRouter, Request, status, Depends
from redis.asyncio import Redis
from typing import Annotated

from domain.auth.auth_services.auth_service.complete_profile_service import complete_profile_service
from domain.auth.entities.auth_models import CompleteVendorProfile
from infrastructure.database.redis.redis_client import get_redis_client

from common.schemas.standard_response import StandardResponse, Meta
from common.translations.messages import get_message
from common.exceptions.base_exception import BadRequestException, InternalServerErrorException
from common.logging.logger import log_info, log_error
from common.utils.ip_utils import extract_client_ip

router = APIRouter()


@router.post(
    "/complete-vendor-profile",
    status_code=status.HTTP_200_OK,
    response_model=StandardResponse,
    summary="Complete vendor profile",
    tags=["Authentication"]
)
async def complete_vendor_profile(
    data: CompleteVendorProfile,
    request: Request,
    redis: Annotated[Redis, Depends(get_redis_client)]
):
    client_ip = extract_client_ip(request)

    try:
        result = await complete_profile_service(
            temporary_token=data.temporary_token,
            first_name=data.first_name,
            last_name=data.last_name,
            business_name=data.business_name,
            city=data.city,
            province=data.province,
            location=data.location.model_dump() if data.location else None,
            address=data.address,
            business_category_ids=data.business_category_ids,
            visibility=data.visibility,
            vendor_type=data.vendor_type,
            languages=data.preferred_languages,
            request=request,
            language=data.response_language,
            redis=redis
        )

        log_info("Vendor profile completed", extra={
            "vendor": data.business_name,
            "ip": client_ip,
            "endpoint": "/complete-vendor-profile"
        })

        return StandardResponse(**result)

    except BadRequestException as e:
        log_error("Validation error in vendor profile", extra={
            "error": str(e.detail),
            "ip": client_ip,
            "endpoint": "/complete-vendor-profile"
        })
        raise

    except Exception as e:
        log_error("Unexpected error in vendor profile", extra={
            "error": str(e),
            "ip": client_ip,
            "endpoint": "/complete-vendor-profile"
        }, exc_info=True)
        raise InternalServerErrorException(detail=get_message("server.error", data.response_language))
