# File: common/security/access_guard.py
from typing import List
from fastapi import Depends, HTTPException, Request
from redis.asyncio import Redis

from common.logging.logger import log_error, log_info
from common.security.jwt.auth import get_token_from_header
from common.security.jwt.decode import decode_token
from common.security.jwt.errors import JWTError
from domain.auth.entities.token_entity import TokenPayload
from domain.access_control.access_control_module import AccessControlService, AccessDeniedError
from infrastructure.database.redis.redis_client import get_redis_client

async def get_redis(redis: Redis = Depends(get_redis_client)) -> Redis:
    """Dependency to provide Redis client."""
    return redis

async def get_token_payload(
    request: Request,
    redis: Redis = Depends(get_redis),
) -> TokenPayload:
    """
    Extract and decode the JWT token payload from the request.

    Args:
        request (Request): FastAPI request object containing the Authorization header.
        redis (Redis): Redis client instance for blacklist validation.

    Returns:
        TokenPayload: Validated JWT payload model.

    Raises:
        HTTPException: If token is missing, invalid, or has an invalid structure.
    """
    try:
        token = get_token_from_header(request)
        payload_data = await decode_token(token, token_type="access", redis=redis)
        token_payload = TokenPayload(**payload_data)

        log_info("Token payload extracted", extra={
            "user_id": token_payload.sub,
            "role": token_payload.role,
        })
        return token_payload

    except JWTError as e:
        log_error("Token payload extraction failed", extra={"error": str(e)})
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        log_error("Invalid token structure", extra={"error": str(e)})
        raise HTTPException(status_code=401, detail="Invalid token payload")

def require_scope(required_scope: str):
    """
    Dependency to enforce a required scope for the authenticated user.

    Args:
        required_scope (str): Scope required to access the resource.

    Returns:
        Callable: Dependency function to validate the scope.

    Raises:
        HTTPException: If the user lacks the required scope.
    """
    async def dependency(user: TokenPayload = Depends(get_token_payload)):
        ac = AccessControlService(
            user_role=user.role,
            user_scopes=user.scopes,
            vendor_status=user.status,
        )
        try:
            ac.assert_scope(required_scope)
            return True
        except AccessDeniedError as e:
            raise HTTPException(status_code=403, detail=str(e))
    return dependency

def require_role(allowed_roles: List[str]):
    """
    Dependency to enforce allowed roles for the authenticated user.

    Args:
        allowed_roles (List[str]): List of roles permitted to access the resource.

    Returns:
        Callable: Dependency function to validate the role.

    Raises:
        HTTPException: If the user's role is not in the allowed list.
    """
    async def dependency(user: TokenPayload = Depends(get_token_payload)):
        if user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail=f"Role '{user.role}' not allowed")
        return True
    return dependency

def require_vendor_status(allowed_statuses: List[str]):
    """
    Dependency to enforce allowed vendor statuses for the authenticated user.

    Args:
        allowed_statuses (List[str]): List of vendor statuses permitted to access the resource.

    Returns:
        Callable: Dependency function to validate the vendor status.

    Raises:
        HTTPException: If the vendor status is not in the allowed list.
    """
    async def dependency(user: TokenPayload = Depends(get_token_payload)):
        ac = AccessControlService(
            user_role=user.role,
            user_scopes=user.scopes,
            vendor_status=user.status,
        )
        try:
            ac.assert_vendor_status(allowed_statuses)
            return True
        except AccessDeniedError as e:
            raise HTTPException(status_code=403, detail=str(e))
    return dependency