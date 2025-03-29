# File: common/security/access_guard.py

from typing import List
from fastapi import Depends, HTTPException, status, Request
from redis.asyncio import Redis

from common.logging.logger import log_error, log_info
from common.security.jwt.auth import get_token_from_header
from common.security.jwt.decode import decode_token
from domain.auth.entities.token_entity import TokenPayload
from domain.access_control.access_control_module import AccessControlService, AccessDeniedError
from infrastructure.database.redis.redis_client import get_redis_client


async def get_token_payload(
    request: Request,
    redis: Redis = Depends(get_redis_client)
) -> TokenPayload:
    """
    Extract and decode token payload using shared decode logic.

    Returns:
        TokenPayload: Validated JWT payload model.
    """
    token = get_token_from_header(request)
    payload_data = await decode_token(token, token_type="access", redis=redis)

    try:
        token_payload = TokenPayload(**payload_data)
    except Exception as e:
        log_error("Invalid token structure", extra={"error": str(e)})
        raise HTTPException(status_code=401, detail="Invalid token payload")

    log_info("Token payload extracted", extra={
        "user_id": token_payload.sub,
        "role": token_payload.role
    })

    return token_payload


def require_scope(required_scope: str):
    """
    Dependency to enforce a required scope.
    """
    async def dependency(user: TokenPayload = Depends(get_token_payload)):
        ac = AccessControlService(
            user_role=user.role,
            user_scopes=user.scopes,
            vendor_status=user.status
        )
        try:
            ac.assert_scope(required_scope)
        except AccessDeniedError as e:
            raise HTTPException(status_code=403, detail=e.detail)
        return True
    return dependency


def require_role(roles: List[str]):
    """
    Dependency to enforce allowed roles.
    """
    async def dependency(user: TokenPayload = Depends(get_token_payload)):
        if user.role not in roles:
            raise HTTPException(status_code=403, detail=f"Role '{user.role}' not allowed")
        return True
    return dependency


def require_vendor_status(allowed_statuses: List[str]):
    """
    Dependency to enforce allowed vendor statuses.
    """
    async def dependency(user: TokenPayload = Depends(get_token_payload)):
        ac = AccessControlService(
            user_role=user.role,
            user_scopes=user.scopes,
            vendor_status=user.status
        )
        try:
            ac.assert_vendor_status(allowed_statuses)
        except AccessDeniedError as e:
            raise HTTPException(status_code=403, detail=e.detail)
        return True
    return dependency
