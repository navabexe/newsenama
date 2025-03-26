# File: common/security/permissions_loader.py

import yaml
from pathlib import Path
from functools import lru_cache
from typing import Optional, List

PERMISSIONS_PATH = Path("common/security/permissions_map.yaml")


@lru_cache()
def load_permissions_map() -> dict:
    if not PERMISSIONS_PATH.exists():
        raise FileNotFoundError(f"Permissions file not found at: {PERMISSIONS_PATH}")

    with PERMISSIONS_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_scopes_for_role(role: str, vendor_status: Optional[str] = None) -> List[str]:
    permissions = load_permissions_map()

    if role == "vendor":
        vendor_perms = permissions.get("vendor", {})
        return vendor_perms.get(vendor_status or "pending", [])

    return permissions.get(role, [])
