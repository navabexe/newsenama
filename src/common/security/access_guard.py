from fastapi import Depends, HTTPException, status, Request
from typing import List
from domain.access_control.access_control_module import AccessControlService, AccessDeniedError
from common.security.jwt.auth import get_token_from_header
from common.config.settings import settings
from jose import jwt, JWTError as JoseJWTError

class TokenPayload:
    def __init__(self, token: str):
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            self.sub = payload.get("sub")
            self.role = payload.get("role")
            self.scope = payload.get("scope", "").split() if isinstance(payload.get("scope"), str) else payload.get("scope", [])
            self.vendor_status = payload.get("status")
            self.raw = payload
        except JoseJWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e

async def get_token_payload(request: Request) -> TokenPayload:
    token = get_token_from_header(request)
    return TokenPayload(token)

def require_scope(required_scope: str):
    def dependency(user: TokenPayload = Depends(get_token_payload)):
        ac = AccessControlService(user_role=user.role, user_scopes=user.scope, vendor_status=user.vendor_status)
        try:
            ac.assert_scope(required_scope)
        except AccessDeniedError as e:
            raise HTTPException(status_code=403, detail=e.detail)
        return True
    return dependency

def require_role(roles: List[str]):
    def dependency(user: TokenPayload = Depends(get_token_payload)):
        if user.role not in roles:
            raise HTTPException(status_code=403, detail=f"Role '{user.role}' not allowed")
        return True
    return dependency

def require_vendor_status(allowed_statuses: List[str]):
    def dependency(user: TokenPayload = Depends(get_token_payload)):
        ac = AccessControlService(user_role=user.role, user_scopes=user.scope, vendor_status=user.vendor_status)
        try:
            ac.assert_vendor_status(allowed_statuses)
        except AccessDeniedError as e:
            raise HTTPException(status_code=403, detail=e.detail)
        return True
    return dependency
