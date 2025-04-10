# File: src/common/middleware/error_middleware.py

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi.exceptions import HTTPException
from common.logging.logger import log_error, log_info
import sentry_sdk


class ErrorLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            return await call_next(request)

        except HTTPException as http_exc:
            log_error("Handled HTTP exception in endpoint", extra={
                "path": request.url.path,
                "method": request.method,
                "error": str(http_exc.detail),
                "status_code": http_exc.status_code,
                "client_ip": request.client.host if request.client else "unknown",
                "headers": dict(request.headers),
            })
            raise http_exc

        except Exception as e:
            error_context = {
                "path": request.url.path,
                "method": request.method,
                "error": str(e),
                "client_ip": request.client.host if request.client else "unknown",
                "headers": dict(request.headers),
            }
            log_error("Unhandled error in endpoint", extra=error_context, exc_info=True)
            log_info("Sending error to Sentry", extra={"error": str(e), "path": request.url.path})
            sentry_sdk.capture_exception(e)
            raise
