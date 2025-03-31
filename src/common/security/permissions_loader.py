# File: src/common/security/permissions_loader.py
from functools import lru_cache
from typing import Optional, List, Dict
import yaml
from pathlib import Path

from common.logging.logger import log_error, log_info
from common.config.settings import settings

PERMISSIONS_PATH = settings.BASE_DIR / "src" / "common" / "security" / "permissions_map.yaml"

@lru_cache()
def load_permissions_map() -> Dict[str, dict]:
    """
    Load and cache the permissions map from a YAML file.

    Returns:
        dict: Permissions map loaded from the YAML file, structured as {role: {status: [scopes]}} or {role: [scopes]}.

    Raises:
        FileNotFoundError: If the permissions file is not found.
        ValueError: If the YAML content is invalid.
    """
    if not PERMISSIONS_PATH.exists():
        log_error("Permissions file not found", extra={"path": str(PERMISSIONS_PATH)})
        raise FileNotFoundError(f"Permissions file not found at: {PERMISSIONS_PATH}")

    try:
        with PERMISSIONS_PATH.open("r", encoding="utf-8") as f:
            permissions = yaml.safe_load(f)
            if not isinstance(permissions, dict):
                log_error("Invalid permissions file format", extra={"path": str(PERMISSIONS_PATH)})
                raise ValueError("Permissions file must contain a valid dictionary")
            log_info("Permissions map loaded", extra={"path": str(PERMISSIONS_PATH)})
            return permissions
    except yaml.YAMLError as e:
        log_error("Failed to parse permissions map", extra={"path": str(PERMISSIONS_PATH), "error": str(e)})
        raise ValueError(f"Failed to parse permissions YAML: {str(e)}")
    except Exception as e:
        log_error("Failed to load permissions map", extra={"path": str(PERMISSIONS_PATH), "error": str(e)})
        raise

def get_scopes_for_role(role: str, vendor_status: Optional[str] = None) -> List[str]:
    """
    Retrieve scopes for a given role and optional vendor status.

    Args:
        role (str): User role (e.g., "user", "vendor", "admin", "guest").
        vendor_status (Optional[str]): Vendor status (e.g., "pending", "public"), only applicable for "vendor" role.

    Returns:
        List[str]: List of scopes associated with the role and status. Returns empty list if invalid or not found.

    Raises:
        FileNotFoundError: If permissions map file is missing.
        ValueError: If permissions map is malformed.
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