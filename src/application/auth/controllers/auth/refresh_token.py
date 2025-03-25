# File: src/application/auth/controllers/auth/refresh_token.py

from fastapi import APIRouter, HTTPException, status, Request
from pydantic import BaseModel, Field

from infrastructure.database.redis.redis_client import get, delete, redis
from common.security.jwt_handler import decode_token, generate_access_token, generate_refresh_token, revoke_token
from common.logging.logger import log_info, log_error
from datetime import datetime, timezone

router = APIRouter(prefix="/auth", tags=["Authentication"])

class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="Current refresh token to rotate")

@router.post("/refresh-token", status_code=status.HTTP_200_OK)
async def refresh_token_endpoint(data: RefreshTokenRequest, request: Request):
    """
    Refresh an access token using a refresh token with rotation.

    - **refresh_token**: Current refresh token to be rotated.
    """
    global user_id
    client_ip = request.client.host

    try:
        # Decode refresh token
        payload = decode_token(data.refresh_token, "refresh")
        user_id = payload["sub"]
        role = payload["role"]
        old_jti = payload["jti"]
        session_id = payload["session_id"]
        redis_key = f"refresh_tokens:{user_id}:{old_jti}"

        # Verify refresh token in Redis
        if not get(redis_key):
            log_error("Refresh token not found or reused", extra={"user_id": user_id, "jti": old_jti, "ip": client_ip})
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or reused refresh token")

        # Revoke old refresh token
        delete(redis_key)
        revoke_token(old_jti, 604800)  # Blacklist for 7 days

        # Generate new tokens
        new_access_token = generate_access_token(user_id, role, session_id)
        new_refresh_token = generate_refresh_token(user_id, role, session_id)

        # Update session info
        session_key = f"sessions:{user_id}:{session_id}"
        redis.hset(session_key, mapping={
            "ip": client_ip,
            "last_refreshed": datetime.now(timezone.utc).isoformat()
        })

        # Log success
        log_info("Tokens refreshed", extra={
            "user_id": user_id,
            "role": role,
            "session_id": session_id,
            "ip": client_ip,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "message": "Tokens refreshed successfully"
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        log_error("Token refresh failed", extra={
            "user_id": user_id if "user_id" in locals() else "unknown",
            "error": str(e),
            "ip": client_ip
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh tokens"
        )