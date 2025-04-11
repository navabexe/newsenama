# File: common/security/access_guard.py

from typing import List

from fastapi import Depends, HTTPException, Request
from redis.asyncio import Redis

from common.logging.logger import log_error, log_info
from common.security.jwt_handler import get_token_from_header, decode_token, JWTError
from domain.access_control.entities.access_control_module import AccessControlService, AccessDeniedError
from domain.auth.entities.token_entity import TokenPayload
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
            "status": token_payload.status,
            "scopes": token_payload.scopes
        })
        return token_payload

    except JWTError as e:
        log_error("Token payload extraction failed", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        log_error("Invalid token structure", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(status_code=401, detail="Invalid token payload")


def require_scope(required_scope: str):
    async def dependency(user: TokenPayload = Depends(get_token_payload)):
        ac = AccessControlService(
            user_role=user.role,
            user_scopes=user.scopes,
            vendor_status=user.status,
        )
        try:
            ac.assert_scope(required_scope)
            log_info("Scope allowed", extra={"required": required_scope, "scopes": user.scopes})
            return True
        except AccessDeniedError as e:
            log_error("Scope denied", extra={"required": required_scope, "scopes": user.scopes})
            raise HTTPException(status_code=403, detail=str(e))
    return dependency


def require_role(allowed_roles: List[str]):
    async def dependency(user: TokenPayload = Depends(get_token_payload)):
        if user.role not in allowed_roles:
            log_error("Role access denied", extra={"user_role": user.role, "allowed_roles": allowed_roles})
            raise HTTPException(status_code=403, detail=f"Role '{user.role}' not allowed")
        log_info("Role allowed", extra={"user_role": user.role})
        return True
    return dependency


def require_vendor_status(allowed_statuses: List[str]):
    async def dependency(user: TokenPayload = Depends(get_token_payload)):
        ac = AccessControlService(
            user_role=user.role,
            user_scopes=user.scopes,
            vendor_status=user.status,
        )
        try:
            ac.assert_vendor_status(allowed_statuses)
            log_info("Vendor status allowed", extra={"status": user.status, "allowed_statuses": allowed_statuses})
            return True
        except AccessDeniedError as e:
            log_error("Vendor status denied", extra={"status": user.status, "allowed_statuses": allowed_statuses})
            raise HTTPException(status_code=403, detail=str(e))
    return dependency
