# File: src/routers/auth/complete_vendor_profile.py
from typing import Annotated

from fastapi import APIRouter, Request, status, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis

from common.config.settings import settings
from common.exceptions.base_exception import InternalServerErrorException
from common.logging.logger import log_info, log_error
from common.schemas.standard_response import StandardResponse
from common.translations.messages import get_message
from common.utils.ip_utils import extract_client_ip
from domain.auth.services.complete_profile_service import complete_profile_service
from domain.auth.entities.auth_models import CompleteVendorProfile
from infrastructure.database.mongodb.connection import get_mongo_db
from infrastructure.database.redis.redis_client import get_redis_client

router = APIRouter()

def log_endpoint_error(error: str | Exception, client_ip: str, data: CompleteVendorProfile, endpoint: str = settings.COMPLETE_VENDOR_PROFILE_PATH):
    log_error(f"Handled error in {endpoint}", extra={
        "error": str(error),
        "ip": client_ip,
        "endpoint": endpoint,
        "request_id": data.request_id,
        "client_version": data.client_version,
        "device_fingerprint": data.device_fingerprint
    })

@router.post(
    settings.COMPLETE_VENDOR_PROFILE_PATH,
    status_code=status.HTTP_200_OK,
    response_model=StandardResponse,
    summary="Complete vendor profile",
    tags=[settings.AUTH_TAG]
)
async def complete_vendor_profile(
    data: CompleteVendorProfile,
    request: Request,
    redis: Annotated[Redis, Depends(get_redis_client)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_mongo_db)]
):
    client_ip = await extract_client_ip(request)
    language = data.response_language

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
            language=language,
            redis=redis,
            db=db
        )

        log_info("Vendor profile completed", extra={
            "vendor": data.business_name,
            "ip": client_ip,
            "endpoint": settings.COMPLETE_VENDOR_PROFILE_PATH,
            "request_id": data.request_id,
            "client_version": data.client_version,
            "device_fingerprint": data.device_fingerprint
        })

        return StandardResponse(
            meta=result["meta"],
            data=result["data"]
        )

    except HTTPException as http_exc:
        log_endpoint_error(http_exc.detail, client_ip, data)
        raise http_exc

    except Exception as e:
        log_endpoint_error(e, client_ip, data, exc_info=True)
        raise InternalServerErrorException(detail=get_message("server.error", language))