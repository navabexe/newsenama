# File: src/routers/auth/login.py

from typing import Optional, Annotated

from fastapi import APIRouter, Request, status, Depends, HTTPException
from pydantic import Field, ConfigDict, model_validator
from redis.asyncio import Redis

from common.exceptions.base_exception import (
    BadRequestException,
    InternalServerErrorException
)
from common.logging.logger import log_info, log_error
from common.schemas.request_base import BaseRequestModel
from common.schemas.standard_response import StandardResponse, Meta
from common.translations.messages import get_message
from common.utils.ip_utils import extract_client_ip
from domain.auth.services.login_service import login_service
from infrastructure.database.redis.redis_client import get_redis_client

router = APIRouter()


class LoginRequest(BaseRequestModel):
    """
    Login request body: phone or username with password.
    Added request_id, client_version, device_fingerprint for consistent logging.
    """

    phone: Optional[str] = Field(
        default=None,
        min_length=10,
        pattern=r"^\+?\d+$",
        description="User/Vendor phone number (e.g. +989123456789)",
        examples=["+989123456789"]
    )
    username: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=50,
        description="Admin username (e.g. navabexe)",
        examples=["navabexe"]
    )
    password: str = Field(
        min_length=8,
        max_length=128,
        description="User/Admin/Vendor password",
        examples=["P@ssword123"]
    )

    request_id: Optional[str] = Field(default=None, max_length=36, description="Request identifier for tracing")
    client_version: Optional[str] = Field(default=None, max_length=15, description="Version of the client app")
    device_fingerprint: Optional[str] = Field(default=None, max_length=100, description="Device fingerprint")

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid"
    )

    @model_validator(mode="before")
    @classmethod
    def at_least_one_identifier(cls, values):
        # چک می‌کنیم حداقل یکی از phone یا username وجود داشته باشد
        if not values.get("phone") and not values.get("username"):
            raise ValueError("Either phone or username must be provided.")
        return values


@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    response_model=StandardResponse,
    summary="Login for users, vendors, and admins",
    tags=["Authentication"],
    responses={
        200: {"description": "Login successful, tokens returned."},
        400: {"description": "Invalid login request."},
        401: {"description": "Unauthorized."},
        403: {"description": "Forbidden."},
        429: {"description": "Too many requests."},
        500: {"description": "Internal server error."}
    }
)
async def login(
    data: LoginRequest,
    request: Request,
    redis: Annotated[Redis, Depends(get_redis_client)]
):
    """
    Unified login endpoint for users, vendors, and admins.
    Accepts either `username` or `phone` with `password` and returns access/refresh tokens.
    """
    client_ip = await extract_client_ip(request)  # اضافه کردن await برای دریافت مقدار واقعی IP
    try:
        result = await login_service(
            phone=data.phone,
            username=data.username,
            password=data.password,
            client_ip=client_ip,
            language=data.response_language,
            redis=redis
        )

        log_info("Login successful", extra={
            "ip": client_ip,
            "user": data.username or data.phone,
            "endpoint": "/login",
            "request_id": data.request_id,
            "client_version": data.client_version,
            "device_fingerprint": data.device_fingerprint
        })

        return StandardResponse(
            meta=Meta(
                message=get_message("auth.login.success", data.response_language),
                status="success",
                code=200
            ),
            data=result
        )

    except HTTPException as http_exc:
        log_error("Handled HTTPException in /login", extra={
            "error": str(http_exc.detail),
            "ip": client_ip,
            "user": data.username or data.phone,
            "endpoint": "/login",
            "request_id": data.request_id,
            "client_version": data.client_version,
            "device_fingerprint": data.device_fingerprint
        })
        raise http_exc

    except ValueError as e:
        log_error("Login validation error", extra={
            "error": str(e),
            "ip": client_ip,
            "user": data.username or data.phone,
            "endpoint": "/login",
            "request_id": data.request_id,
            "client_version": data.client_version,
            "device_fingerprint": data.device_fingerprint
        })
        raise BadRequestException(detail=get_message("auth.login.invalid", data.response_language))

    except Exception as e:
        log_error("Unexpected login error", extra={
            "error": str(e),
            "ip": client_ip,
            "user": data.username or data.phone,
            "endpoint": "/login",
            "request_id": data.request_id,
            "client_version": data.client_version,
            "device_fingerprint": data.device_fingerprint
        }, exc_info=True)
        raise InternalServerErrorException(
            detail=get_message("server.error", data.response_language)
        )