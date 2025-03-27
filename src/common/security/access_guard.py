from typing import List

from fastapi import Depends, HTTPException, status, Request
from jose import jwt, JWTError as JoseJWTError
from redis.asyncio import Redis

from common.config.settings import settings
from common.logging.logger import log_error, log_info
from common.security.jwt_handler import get_token_from_header
from domain.access_control.access_control_module import AccessControlService, AccessDeniedError
from infrastructure.database.redis.operations.get import get
from infrastructure.database.redis.redis_client import get_redis_client


class TokenPayload:
    def __init__(self, token: str, redis: Redis):
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            self.sub = payload.get("sub")
            self.role = payload.get("role")
            self.scope = payload.get("scope", "").split() if isinstance(payload.get("scope"), str) else payload.get("scope", [])
            self.vendor_status = payload.get("status")
            self.jti = payload.get("jti")
            self.raw = payload

            # Check if token is blacklisted
            if self.jti and redis:
                if get(f"blacklist:{self.jti}"):
                    log_error("Token revoked", extra={"jti": self.jti})
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token has been revoked",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
        except JoseJWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e


async def get_token_payload(
    request: Request,
    redis: Redis = Depends(get_redis_client)
) -> TokenPayload:
    """
    Extract and decode token payload from the request.

    Args:
        request (Request): FastAPI request object.
        redis (Redis): Redis client dependency.

    Returns:
        TokenPayload: Decoded token payload with user info.

    Raises:
        HTTPException: If token is invalid, expired, or revoked.
    """
    token = get_token_from_header(request)
    payload = TokenPayload(token, redis)
    log_info("Token payload extracted", extra={"user_id": payload.sub, "role": payload.role})
    return payload


def require_scope(required_scope: str):
    """
    Dependency to enforce a required scope.

    Args:
        required_scope (str): Scope required for access.

    Returns:
        Callable: Dependency function.
    """
    async def dependency(user: TokenPayload = Depends(get_token_payload)):
        ac = AccessControlService(user_role=user.role, user_scopes=user.scope, vendor_status=user.vendor_status)
        try:
            ac.assert_scope(required_scope)
        except AccessDeniedError as e:
            raise HTTPException(status_code=403, detail=e.detail)
        return True
    return dependency


def require_role(roles: List[str]):
    """
    Dependency to enforce allowed roles.

    Args:
        roles (List[str]): List of allowed roles.

    Returns:
        Callable: Dependency function.
    """
    async def dependency(user: TokenPayload = Depends(get_token_payload)):
        if user.role not in roles:
            raise HTTPException(status_code=403, detail=f"Role '{user.role}' not allowed")
        return True
    return dependency


def require_vendor_status(allowed_statuses: List[str]):
    """
    Dependency to enforce allowed vendor statuses.

    Args:
        allowed_statuses (List[str]): List of allowed vendor statuses.

    Returns:
        Callable: Dependency function.
    """
    async def dependency(user: TokenPayload = Depends(get_token_payload)):
        ac = AccessControlService(user_role=user.role, user_scopes=user.scope, vendor_status=user.vendor_status)
        try:
            ac.assert_vendor_status(allowed_statuses)
        except AccessDeniedError as e:
            raise HTTPException(status_code=403, detail=e.detail)
        return True
    return dependency