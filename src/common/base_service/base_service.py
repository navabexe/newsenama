# File: src/domain/common/base_service.py
from abc import ABC
from typing import Dict, Any

import sentry_sdk
from fastapi import HTTPException

from common.exceptions.base_exception import DatabaseConnectionException, InternalServerErrorException
from common.exceptions.error_handlers import handle_db_error, handle_general_error
from common.logging.logger import log_info, log_error


class BaseService(ABC):
    def __init__(self):
        self.default_language = "fa"

    # File: src/domain/common/base_service.py
    async def execute(self, operation: callable, context: Dict[str, Any], language: str = "fa"):
        try:
            result = await operation()
            log_info(f"{context.get('action', 'Operation')} executed successfully", extra=context)
            return result
        except HTTPException as http_exc:
            log_error(f"HTTP exception in {context.get('endpoint', 'service')}",
                      extra={**context, "error": str(http_exc.detail)})
            log_info("Sending HTTP exception to Sentry", extra={"error": str(http_exc.detail)})  # اضافه کن
            sentry_sdk.capture_exception(http_exc)
            raise http_exc
        except DatabaseConnectionException as db_exc:
            await handle_db_error(db_exc, context, language)
            raise
        except Exception as e:
            await handle_general_error(e, context, language)
            raise InternalServerErrorException(detail="Internal server error")