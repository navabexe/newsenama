# File: application/auth/controllers/login.py

from typing import Optional, Annotated
from fastapi import APIRouter, Request, HTTPException, status, Depends
from pydantic import Field, ConfigDict, model_validator
from redis.asyncio import Redis

from common.schemas.request_base import BaseRequestModel
from common.translations.messages import get_message
from domain.auth.auth_services.auth_service.login import login_service
from infrastructure.database.redis.redis_client import get_redis_client
from common.logging.logger import log_info, log_error

router = APIRouter()


class LoginRequest(BaseRequestModel):
    """Request model for user, vendor, or admin login."""

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

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid"
    )

    @model_validator(mode="before")
    @classmethod
    def at_least_one_identifier(cls, values):
        if not values.get("phone") and not values.get("username"):
            raise ValueError("Either phone or username must be provided.")
        return values


@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Login successful, tokens returned."},
        400: {"description": "Invalid login request."},
        401: {"description": "Unauthorized."},
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
    """
    try:
        result = await login_service(
            phone=data.phone,
            username=data.username,
            password=data.password,
            client_ip=request.client.host,
            language=data.response_language,
            redis=redis
        )
        log_info("Login successful", extra={"ip": request.client.host, "user": data.username or data.phone})
        return result

    except HTTPException as e:
        log_error("Login HTTPException", extra={"detail": str(e.detail)})
        raise

    except ValueError as e:
        log_error("Login validation error", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except Exception as e:
        log_error("Unexpected login error", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_message("server.error", data.response_language)
        )
