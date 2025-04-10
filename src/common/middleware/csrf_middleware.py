# File: src/common/middleware/csrf_middleware.py

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from redis.asyncio import Redis
import json

from common.logging.logger import log_error
from infrastructure.database.redis.redis_client import get_redis_client
from common.csrf_service import CSRFService
from common.translations.messages import get_message


async def extract_language(request: Request) -> str:
    lang = request.headers.get("X-Language")
    if lang:
        return lang
    try:
        body = await request.body()
        if body:
            parsed = json.loads(body)
            return parsed.get("response_language", "fa")
    except Exception:
        pass
    return "fa"


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method in ["POST", "PUT", "DELETE"]:
            redis: Redis = await get_redis_client()
            csrf_service = CSRFService(redis)

            user_id = request.headers.get("X-User-ID", "anonymous")
            csrf_token = request.headers.get("X-CSRF-Token")
            language = await extract_language(request)

            if not csrf_token:
                log_error("Missing CSRF token", extra={"path": request.url.path, "method": request.method})
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": "CSRF token missing",
                        "message": get_message("csrf.missing", lang=language),
                        "error_code": "CSRF_001",
                        "status": "error"
                    }
                )

            is_valid = await csrf_service.validate_csrf_token(user_id, csrf_token)
            if not is_valid:
                log_error("Invalid CSRF token", extra={"path": request.url.path, "method": request.method, "token": csrf_token})
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": "Invalid CSRF token",
                        "message": get_message("csrf.invalid", lang=language),
                        "error_code": "CSRF_002",
                        "status": "error"
                    }
                )

        return await call_next(request)
