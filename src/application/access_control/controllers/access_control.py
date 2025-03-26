# File: application/access_control/controllers/access_control.py

from fastapi import APIRouter, Depends
from application.access_control.access_control_app import access_control_repo, assign_role_to_user, get_user_permissions
from common.security.access_guard import require_scope, require_role

router = APIRouter(prefix="/access-control", tags=["Access Control"])


@router.get("/roles", dependencies=[Depends(require_role(["admin"]))])
def list_roles():
    return access_control_repo.list_roles()


@router.get("/permissions", dependencies=[Depends(require_role(["admin"]))])
def list_permissions():
    return access_control_repo.list_permissions()


@router.post("/assign-role", dependencies=[Depends(require_role(["admin"]))])
def assign_role(user_id: str, role_name: str):
    return assign_role_to_user(user_id, role_name)


@router.get("/me/scopes", dependencies=[Depends(require_scope("read:profile"))])
def get_my_scopes(role: str, status: str):
    return {"scopes": get_user_permissions(role, status)}
