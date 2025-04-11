from typing import List, Optional

from common.logging.logger import log_info, log_error
from domain.access_control.entities.access_control_module import get_default_scopes_for
from domain.access_control.entities.permission_entity import Permission
from domain.access_control.entities.role_entity import Role
from infrastructure.database.mongodb.repositories.access_control_repository import MongoAccessControlRepository

access_control_repo: Optional[MongoAccessControlRepository] = None

def set_access_control_repo(repo: MongoAccessControlRepository):
    """
    Set the global access control repository instance.
    """
    global access_control_repo
    access_control_repo = repo


async def initialize_default_roles():
    """
    Initialize default roles and permissions if they do not already exist.
    """
    if await access_control_repo.get_role_by_name("admin"):
        log_info("Default roles already exist")
        return

    try:
        perms = [
            Permission(name="read:products", description="Read product listings"),
            Permission(name="write:products", description="Create or update products"),
            Permission(name="read:orders", description="Access order data"),
            Permission(name="manage:ads", description="Manage advertisements"),
            Permission(name="approve:vendors", description="Approve vendor applications")
        ]
        perm_ids = []
        for p in perms:
            pid = await access_control_repo.create_permission(p)
            perm_ids.append(pid)

        await access_control_repo.create_role(Role(name="admin", permissions=perm_ids, description="System administrator"))
        await access_control_repo.create_role(Role(name="vendor", permissions=perm_ids[:3], description="Vendor user"))
        await access_control_repo.create_role(Role(name="user", permissions=perm_ids[:1], description="Basic user"))

        log_info("Default roles and permissions created successfully")

    except Exception as e:
        log_error("Failed to initialize default roles", extra={"error": str(e)}, exc_info=True)
        raise


async def assign_role_to_user(user_id: str, role_name: str):
    """
    Assign a role to a user using the access control repository.
    """
    role = await access_control_repo.get_role_by_name(role_name)
    if not role:
        log_error("Role not found", extra={"role_name": role_name})
        raise ValueError(f"Role '{role_name}' not found")

    await access_control_repo.assign_role_to_user(user_id, role.name)
    log_info("Role assigned to user", extra={"user_id": user_id, "role": role.name})
    return {
        "user_id": user_id,
        "role": role.name,
        "permissions": role.permissions,
        "scope": get_default_scopes_for(role.name)
    }


async def get_user_permissions(role_name: str, vendor_status: Optional[str] = None) -> List[str]:
    """
    Retrieve default scopes for a given role and optional vendor status.
    """
    log_info("Fetching default scopes", extra={"role": role_name, "vendor_status": vendor_status})
    return get_default_scopes_for(role_name, vendor_status)
