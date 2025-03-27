# File: application/access_control/access_control_app.py

from typing import List, Optional
from domain.access_control.access_control_module import Role, Permission, get_default_scopes_for


class AccessControlRepository:
    """
    Temporary in-memory role/permission store. Replace with actual DB/repo later.
    """
    def __init__(self):
        self.roles = {}
        self.permissions = {}

    def create_permission(self, name: str, description: Optional[str] = None) -> Permission:
        perm = Permission(name=name, description=description)
        self.permissions[perm.id] = perm
        return perm

    def create_role(self, name: str, permissions: List[str], description: Optional[str] = None) -> Role:
        role = Role(name=name, permissions=permissions, description=description)
        self.roles[role.id] = role
        return role

    def get_role_by_name(self, name: str) -> Optional[Role]:
        for r in self.roles.values():
            if r.name == name:
                return r
        return None

    def list_roles(self) -> List[Role]:
        return list(self.roles.values())

    def list_permissions(self) -> List[Permission]:
        return list(self.permissions.values())


# Initialize repo instance
access_control_repo = AccessControlRepository()


def initialize_default_roles():
    if access_control_repo.get_role_by_name("admin"):
        return  # Already initialized

    # Define some example permissions
    perms = [
        access_control_repo.create_permission("read:products"),
        access_control_repo.create_permission("write:products"),
        access_control_repo.create_permission("read:orders"),
        access_control_repo.create_permission("manage:ads"),
        access_control_repo.create_permission("approve:vendors"),
    ]

    perm_ids = [p.id for p in perms]
    access_control_repo.create_role("admin", permissions=perm_ids, description="Full system admin")
    access_control_repo.create_role("vendor", permissions=perm_ids[:3], description="Standard vendor")
    access_control_repo.create_role("user", permissions=perm_ids[:1], description="Regular user")


initialize_default_roles()


def assign_role_to_user(user_id: str, role_name: str):
    role = access_control_repo.get_role_by_name(role_name)
    if not role:
        raise ValueError(f"Role '{role_name}' not found")
    # Placeholder for actual DB logic to store mapping
    return {
        "user_id": user_id,
        "role": role.name,
        "permissions": role.permissions,
        "scope": get_default_scopes_for(role.name)
    }


def get_user_permissions(role_name: str, vendor_status: Optional[str] = None) -> List[str]:
    return get_default_scopes_for(role_name, vendor_status)
