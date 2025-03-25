from fastapi import APIRouter, Request, Depends, HTTPException, status
from pydantic import BaseModel, Field
from common.security.jwt_handler import get_current_user
from domain.auth.auth_services.auth_service.approve_vendor import approve_vendor_service

router = APIRouter(tags=["Authentication"])

class ApproveVendorRequest(BaseModel):
    vendor_id: str = Field(description="ID of the vendor to approve or reject")
    action: str = Field(pattern=r"^(approve|reject)$", description="Action: approve or reject")

@router.post("/approve-vendor", status_code=status.HTTP_200_OK)
async def approve_vendor(
    request: Request,
    data: ApproveVendorRequest,
    current_user: dict = Depends(get_current_user)
):
    try:
        return await approve_vendor_service(current_user, data.vendor_id, data.action, request.client.host)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to process approval")