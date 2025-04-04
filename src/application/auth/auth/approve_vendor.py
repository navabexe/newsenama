from fastapi import APIRouter, Request, Depends, HTTPException, status
from redis.asyncio import Redis
from typing import Annotated
from pydantic import BaseModel, Field, field_validator, ConfigDict

from common.schemas.request_base import BaseRequestModel
from common.security.jwt_handler import get_current_user
from common.translations.messages import get_message
from domain.auth.auth_services.auth_service.approve_vendor import approve_vendor_service
from infrastructure.database.redis.redis_client import get_redis_client
from common.logging.logger import log_info, log_error
from common.exceptions.base_exception import ForbiddenException, BadRequestException, InternalServerErrorException

router = APIRouter()


class ApproveVendorRequest(BaseRequestModel):
    """Request model for approving or rejecting a vendor profile."""

    vendor_id: Annotated[str, Field(description="ID of the vendor to approve or reject", examples=["vendor_123"])]
    action: Annotated[str, Field(description="Action to take: approve or reject", examples=["approve", "reject"])]

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
    responses={
        200: {"description": "Vendor action processed successfully."},
        400: {"description": "Invalid request payload."},
        401: {"description": "Unauthorized."},
        500: {"description": "Internal server error."}
    }
)
async def approve_vendor(
        request: Request,
        data: ApproveVendorRequest,
        current_user: Annotated[dict, Depends(get_current_user)],
        redis: Annotated[Redis, Depends(get_redis_client)]
):
    """
    Admin endpoint to approve or reject vendor profiles.
    """
    try:
        # Check user role and access
        if current_user.get("role") != "admin":
            log_error("Unauthorized access attempt",
                      extra={"user_id": current_user.get("id"), "ip": request.client.host})
            raise ForbiddenException(detail=get_message("auth.forbidden", data.response_language))

        result = await approve_vendor_service(
            current_user=current_user,
            vendor_id=data.vendor_id,
            action=data.action,
            client_ip=request.client.host,
            language=data.response_language,
            redis=redis
        )

        log_info("Vendor action successful",
                 extra={"user": current_user.get("id"), "action": data.action, "vendor_id": data.vendor_id})
        return result

    except HTTPException as e:
        log_error("Vendor approval HTTPException", extra={"detail": str(e.detail)}, exc_info=True)
        raise

    except ValueError as e:
        log_error("Vendor approval validation error", extra={"error": str(e)}, exc_info=True)
        raise BadRequestException(detail=str(e))

    except Exception as e:
        log_error("Unexpected error in vendor approval", extra={"error": str(e)}, exc_info=True)
        raise InternalServerErrorException(detail=get_message("server.error", data.response_language))
