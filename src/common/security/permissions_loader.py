from functools import lru_cache
from pathlib import Path
from typing import Optional, List

import yaml

from common.logging.logger import log_error, log_info

PERMISSIONS_PATH = Path("common/security/permissions_map.yaml")


@lru_cache()
def load_permissions_map() -> dict:
    """
    Load permissions map from YAML file and cache it.

    Returns:
        dict: Permissions map loaded from YAML.

    Raises:
        FileNotFoundError: If permissions file is not found.
    """
    if not PERMISSIONS_PATH.exists():
        log_error("Permissions file not found", extra={"path": str(PERMISSIONS_PATH)})
        raise FileNotFoundError(f"Permissions file not found at: {PERMISSIONS_PATH}")

    try:
        with PERMISSIONS_PATH.open("r", encoding="utf-8") as f:
            permissions = yaml.safe_load(f)
            if not isinstance(permissions, dict):
                log_error("Invalid permissions file format", extra={"path": str(PERMISSIONS_PATH)})
                return {}
            log_info("Permissions map loaded", extra={"path": str(PERMISSIONS_PATH)})
            return permissions
    except Exception as e:
        log_error("Failed to load permissions map", extra={"path": str(PERMISSIONS_PATH), "error": str(e)})
        return {}


def get_scopes_for_role(role: str, vendor_status: Optional[str] = None) -> List[str]:
    """
    Get scopes for a given role and optional vendor status.

    Args:
        role (str): User role (e.g., "user", "vendor", "admin").
        vendor_status (Optional[str]): Vendor status (e.g., "pending", "public").

    Returns:
        List[str]: List of scopes associated with the role and status.
    """
    permissions = load_permissions_map()

    if role == "vendor":
        vendor_perms = permissions.get("vendor", {})
        if not isinstance(vendor_perms, dict):
            log_error("Invalid vendor permissions format", extra={"role": role})
            return []
        scopes = vendor_perms.get(vendor_status or "pending", [])
    else:
        scopes = permissions.get(role, [])

    if not isinstance(scopes, list):
        log_error("Scopes not in list format", extra={"role": role, "vendor_status": vendor_status})
        return []

    return scopes