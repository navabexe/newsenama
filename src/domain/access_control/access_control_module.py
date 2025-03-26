# File: domain/access_control/access_control_module.py

from typing import List, Optional, Union
from pydantic import BaseModel, Field
from uuid import uuid4
from datetime import datetime
import yaml
from pathlib import Path

# ============================
# Entities: Role & Permission
# ============================

class Permission(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: Optional[str] = None


class Role(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ============================
# Scope Resolution Logic
# ============================

_permissions_map_cache = None


def load_permissions_map() -> dict:
    global _permissions_map_cache
    if _permissions_map_cache is not None:
        return _permissions_map_cache

    path = Path("common/security/permissions_map.yaml")
    if not path.exists():
        raise FileNotFoundError("permissions_map.yaml not found")

    with path.open("r", encoding="utf-8") as f:
        _permissions_map_cache = yaml.safe_load(f)
    return _permissions_map_cache


def get_default_scopes_for(role_name: str, vendor_status: Optional[str] = None) -> List[str]:
    permissions_map = load_permissions_map()

    if role_name == "vendor":
        vendor_roles = permissions_map.get("vendor", {})
        return vendor_roles.get(vendor_status or "pending", [])

    return permissions_map.get(role_name, [])


# ============================
# Permission Evaluation
# ============================

class AccessControlService:
    def __init__(self, user_role: str, user_scopes: List[str], vendor_status: Optional[str] = None):
        self.role = user_role
        self.scopes = set(user_scopes)
        self.vendor_status = vendor_status

    def has_scope(self, required: Union[str, List[str]]) -> bool:
        if "*" in self.scopes:
            return True
        if isinstance(required, str):
            return required in self.scopes
        return all(r in self.scopes for r in required)

    def assert_scope(self, required: Union[str, List[str]]):
        if not self.has_scope(required):
            raise AccessDeniedError(detail=f"Missing required scope(s): {required}")

    def assert_vendor_status(self, allowed_statuses: List[str]):
        if self.role != "vendor":
            raise AccessDeniedError(detail="Only vendor accounts allowed for this action")
        if self.vendor_status not in allowed_statuses:
            raise AccessDeniedError(detail=f"Vendor status '{self.vendor_status}' not allowed")


# ============================
# Exceptions
# ============================

class AccessDeniedError(Exception):
    def __init__(self, detail: str):
        self.detail = detail
        self.code = "access_denied"
        super().__init__(self.detail)

    def to_dict(self):
        return {"error": self.code, "detail": self.detail}
