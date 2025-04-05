# File: src/application/auth/admin/approve_vendor.py

from fastapi import APIRouter, Request, Depends, HTTPException, status
from redis.asyncio import Redis
from typing import Annotated
from pydantic import Field, field_validator, ConfigDict

from common.schemas.request_base import BaseRequestModel
from common.schemas.standard_response import StandardResponse
from common.security.jwt_handler import get_current_user
from common.translations.messages import get_message
from domain.auth.auth_services.admin.approve_vendor_service import approve_vendor_service
from infrastructure.database.redis.redis_client import get_redis_client
from common.logging.logger import log_info, log_error
from common.exceptions.base_exception import ForbiddenException, BadRequestException, InternalServerErrorException
from common.utils.ip_utils import extract_client_ip

router = APIRouter()

class ApproveVendorRequest(BaseRequestModel):
    """Request model for approving or rejecting a vendor profile."""
    vendor_id: Annotated[str, Field(description="ID of the vendor to approve or reject", examples=["vendor_123"])]
    action: Annotated[str, Field(description="Action to take: approve or reject", examples=["approve", "reject"])]
    device_fingerprint: Annotated[str | None, Field(default=None, max_length=100, description="Device fingerprint")]

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid"
    )

    @field_validator("action")
    @classmethod
    def validate_action(cls, v):
        if v not in {"approve", "reject"}:
            raise ValueError("Action must be either 'approve' or 'reject'")
        return v

@router.post(
    "/approve-vendor",
    status_code=status.HTTP_200_OK,
    response_model=StandardResponse,
    summary="Approve or reject a vendor profile",
    description="Admin endpoint to approve or reject vendor profiles.",
    tags=["Admin"],
    responses={
        200: {"description": "Vendor action processed successfully."},
        400: {"description": "Invalid request payload."},
        401: {"description": "Unauthorized."},
        403: {"description": "Forbidden."},
        500: {"description": "Internal server error."}
    }
)
async def approve_vendor(
    request: Request,
    data: ApproveVendorRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    redis: Annotated[Redis, Depends(get_redis_client)]
):
    client_ip = extract_client_ip(request)
    language = data.response_language

    try:
        # Check user role (redundant but kept for clarity)
        if current_user.get("role") != "admin":
            log_error("Unauthorized access attempt",
                      extra={"user_id": current_user.get("user_id"), "ip": client_ip})
            raise ForbiddenException(detail=get_message("auth.forbidden", language))

        result = await approve_vendor_service(
            current_user=current_user,
            vendor_id=data.vendor_id,
            action=data.action,
            client_ip=client_ip,
            language=language,
            redis=redis
        )

        log_info("Vendor action successful",
                 extra={
                     "user_id": current_user.get("user_id"),
                     "action": data.action,
                     "vendor_id": data.vendor_id,
                     "ip": client_ip,
                     "endpoint": "/approve-vendor",
                     "request_id": data.request_id,
                     "client_version": data.client_version,
                     "device_fingerprint": data.device_fingerprint
                 })

        return StandardResponse(
            meta=result["meta"],
            data=result["data"]
        )

    except HTTPException as e:
        log_error("Vendor approval HTTPException", extra={
            "detail": str(e.detail),
            "ip": client_ip,
            "endpoint": "/approve-vendor",
            "request_id": data.request_id,
            "client_version": data.client_version,
            "device_fingerprint": data.device_fingerprint
        }, exc_info=True)
        raise

    except ValueError as e:
        log_error("Vendor approval validation error", extra={
            "error": str(e),
            "ip": client_ip,
            "endpoint": "/approve-vendor",
            "request_id": data.request_id,
            "client_version": data.client_version,
            "device_fingerprint": data.device_fingerprint
        }, exc_info=True)
        raise BadRequestException(detail=str(e))

    except Exception as e:
        log_error("Unexpected error in vendor approval", extra={
            "error": str(e),
            "ip": client_ip,
            "endpoint": "/approve-vendor",
            "request_id": data.request_id,
            "client_version": data.client_version,
            "device_fingerprint": data.device_fingerprint
        }, exc_info=True)
        raise InternalServerErrorException(detail=get_message("server.error", language))