from fastapi import APIRouter, Depends, status, Query
from pydantic import BaseModel, Field, ConfigDict

from domain.access_control.access_control_app import (
    access_control_repo,
    assign_role_to_user,
    get_user_permissions,
)
from common.security.access_guard import require_scope, require_role
from common.logging.logger import log_info, log_error
from common.exceptions.base_exception import (
    BadRequestException,
    InternalServerErrorException
)


router = APIRouter(prefix="/access-control", tags=["Access Control"])


class AssignRoleInput(BaseModel):
    user_id: str = Field(..., description="User ID to assign role to")
    role_name: str = Field(..., description="Role to assign (e.g. admin, user, vendor)")

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid"
    )


@router.get("/roles", status_code=status.HTTP_200_OK)
async def list_roles(_: bool = Depends(require_role(["admin"]))):
    """
    List all roles (admin only)
    """
    try:
        roles = access_control_repo.list_roles()
        log_info("Listed roles", extra={"count": len(roles)})
        return roles
    except Exception as e:
        log_error("Failed to list roles", extra={"error": str(e)}, exc_info=True)
        raise InternalServerErrorException(detail="Unable to fetch roles")


@router.get("/permissions", status_code=status.HTTP_200_OK)
async def list_permissions(_: bool = Depends(require_role(["admin"]))):
    """
    List all permissions (admin only)
    """
    try:
        perms = access_control_repo.list_permissions()
        log_info("Listed permissions", extra={"count": len(perms)})
        return perms
    except Exception as e:
        log_error("Failed to list permissions", extra={"error": str(e)}, exc_info=True)
        raise InternalServerErrorException(detail="Unable to fetch permissions")


@router.post("/assign-role", status_code=status.HTTP_200_OK)
async def assign_role(
    payload: AssignRoleInput,
    _: bool = Depends(require_role(["admin"]))
):
    """
    Assign a role to a specific user (admin only)
    """
    try:
        result = await assign_role_to_user(payload.user_id, payload.role_name)
        log_info("Role assigned", extra={"user_id": payload.user_id, "role": payload.role_name})
        return result
    except ValueError as e:
        log_error("Role assignment failed - bad request", extra={"error": str(e)})
        raise BadRequestException(detail=str(e))
    except Exception as e:
        log_error("Failed to assign role", extra={"error": str(e)}, exc_info=True)
        raise InternalServerErrorException(detail="Unable to assign role")


@router.get("/me/scopes", status_code=status.HTTP_200_OK)
async def get_my_scopes(
    role: str = Query(..., description="Current user role (user/vendor/admin)"),
    status: str = Query(..., description="Vendor status (e.g. pending/approved)"),
    _: bool = Depends(require_scope("read:profile"))
):
    """
    Retrieve scopes for the current user (requires read:profile scope).
    """
    try:
        scopes = await get_user_permissions(role, status)
        log_info("Scopes fetched", extra={"role": role, "status": status, "count": len(scopes)})
        return {"scopes": scopes}
    except Exception as e:
        log_error("Failed to get user scopes", extra={"error": str(e)}, exc_info=True)
        raise InternalServerErrorException(detail="Unable to retrieve scopes")
