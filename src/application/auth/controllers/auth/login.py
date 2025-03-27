from typing import Optional

from fastapi import APIRouter, Request, HTTPException, status, Depends
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from domain.auth.auth_services.auth_service.login import login_service
from infrastructure.database.redis.redis_client import get_redis_client

router = APIRouter()


class LoginRequest(BaseModel):
    phone: Optional[str] = Field(
        default=None,
        min_length=10,
        pattern=r"^\+?\d+$",
        description="User/Vendor phone number (e.g., +989123456789)"
    )
    username: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=50,
        description="Admin username (e.g., navabexe)"
    )
    password: str = Field(
        min_length=8,
        max_length=128,
        description="User/Admin/Vendor password"
    )

    model_config = {
        "str_strip_whitespace": True,
        "extra": "forbid"
    }


@router.post("/login", status_code=status.HTTP_200_OK)
async def login(
        data: LoginRequest,
        request: Request,
        redis: Redis = Depends(get_redis_client)
):
    """
    Unified login endpoint for users, vendors, and admins.

    Args:
        data (LoginRequest): Login credentials (phone or username, and password).
        request (Request): FastAPI request object.
        redis (Redis): Redis client dependency.

    Returns:
        dict: Login response with tokens and role.

    Raises:
        HTTPException: If login fails.
    """
    try:
        return await login_service(data.phone, data.username, data.password, request.client.host, redis)
    except HTTPException as e:
        raise e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to login")
