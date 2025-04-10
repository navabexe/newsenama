# File: src/common/utils/log_utils.py
from datetime import datetime, timezone
from common.config.settings import settings

def create_log_data(
    entity_type: str,
    entity_id: str,
    action: str,
    ip: str,
    request_id: str = None,
    client_version: str = None,
    device_fingerprint: str = None,
    extra_data: dict = None
) -> dict:
    log_data = {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "action": action,
        "ip": ip,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": request_id,
        "client_version": client_version,
        "device_fingerprint": device_fingerprint
    }
    if extra_data:
        log_data.update(extra_data)
    if settings.ENVIRONMENT == "development" and extra_data:
        log_data["raw_data"] = extra_data
    return log_data