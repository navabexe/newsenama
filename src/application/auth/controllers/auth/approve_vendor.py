from fastapi import APIRouter, Request, Depends, HTTPException, status
from redis.asyncio import Redis
from pydantic import BaseModel, Field, ConfigDict

from common.security.jwt_handler import get_current_user
from common.translations.messages import get_message
from domain.auth.auth_services.auth_service.approve_vendor import approve_vendor_service
from infrastructure.database.redis.redis_client import get_redis_client

router = APIRouter()


class ApproveVendorRequest(BaseModel):
    vendor_id: str = Field(..., description="ID of the vendor to approve or reject")
    action: str = Field(
        ...,
        pattern=r"^(approve|reject)$",
        description="Action to take: approve or reject"
    )
    language: str = Field(default="fa", description="Response language (fa/en)")

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid"
    )


@router.post("/approve-vendor", status_code=status.HTTP_200_OK)
async def approve_vendor(
    request: Request,
    data: ApproveVendorRequest,
    current_user: dict = Depends(get_current_user),
    redis: Redis = Depends(get_redis_client)
):
    """
    Admin endpoint to approve or reject vendor profiles.
    """
    try:
        return await approve_vendor_service(
            current_user=current_user,
            vendor_id=data.vendor_id,
            action=data.action,
            client_ip=request.client.host,
            language=data.language,
            redis=redis
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_message("server.error", data.language)
        )
