# File: src/common/error_handlers.py
from typing import Dict, Any
from common.logging.logger import log_error
from common.exceptions.base_exception import DatabaseConnectionException
from domain.notification.notification_services.notification_service import notification_service
import sentry_sdk

async def handle_general_error(exc: Exception, context: Dict[str, Any], language: str):
    log_error(f"Error in {context.get('endpoint', 'service')}", extra={**context, "error": str(exc)}, exc_info=True)
    sentry_sdk.capture_exception(exc)
    await notification_service.send(
        receiver_id="admin",
        receiver_type="admin",
        template_key="notification_failed",
        variables={"receiver_id": context.get("entity_id", "system"), "error": str(exc), "type": "general"},
        reference_type=context.get("entity_type", "system"),
        reference_id=context.get("entity_id", "unknown"),
        language=language
    )

async def handle_db_error(exc: DatabaseConnectionException, context: Dict[str, Any], language: str):
    log_error(f"Database error in {context.get('endpoint', 'service')}", extra={**context, "error": str(exc)}, exc_info=True)
    sentry_sdk.capture_exception(exc)
    await notification_service.send(
        receiver_id="admin",
        receiver_type="admin",
        template_key="notification_failed",
        variables={"receiver_id": context.get("entity_id", "system"), "error": str(exc), "type": "database"},
        reference_type=context.get("entity_type", "system"),
        reference_id=context.get("entity_id", "unknown"),
        language=language
    )