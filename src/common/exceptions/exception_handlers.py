# File: common/exceptions/exception_handlers.py

from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from common.logging.logger import log_error

def register_exception_handlers(app: FastAPI):
    """
    Register global exception handlers for various error types.
    """

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """
        Handles Pydantic validation errors (e.g., missing fields, wrong types, etc.)
        We gather all validation errors and provide a combined message.
        """
        errors = exc.errors()  # list of dicts with details about each error
        details = []
        for err in errors:
            # example err:
            # {
            #   "loc": ("body", "phone"),
            #   "msg": "field required",
            #   "type": "value_error.missing",
            # }
            loc = err.get("loc", [])
            msg = err.get("msg", "Invalid input.")
            if len(loc) > 1:
                # typically loc = ["body", "field_name"]
                field_name = loc[1]
                details.append(f"{field_name}: {msg}")
            else:
                details.append(msg)

        # join all messages into a single string
        error_message = "; ".join(details) if details else "Invalid input."

        # log the first or combined error
        log_error("Validation error", extra={
            "path": request.url.path,
            "method": request.method,
            "error": error_message
        })

        return JSONResponse(
            status_code=400,
            content={"detail": error_message},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """
        Handles FastAPI's HTTPException (including custom ones like UnauthorizedException, BadRequestException, etc.)
        We return the same status code and detail that was originally raised.
        """
        log_error("Handled HTTPException", extra={
            "path": request.url.path,
            "method": request.method,
            "status_code": exc.status_code,
            "error": str(exc.detail)
        })
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": str(exc.detail)},
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """
        Handles any other unhandled exception (unexpected errors).
        Returns 500 Internal Server Error.
        """
        log_error("Unhandled exception", extra={
            "path": request.url.path,
            "method": request.method,
            "error": str(exc)
        }, exc_info=True)

        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )
