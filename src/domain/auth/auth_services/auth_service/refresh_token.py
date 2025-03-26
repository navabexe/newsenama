# === SERVICE: refresh_token.py ===

from fastapi import HTTPException
from infrastructure.database.redis.redis_client import get
from common.security.jwt.decode import decode_token as decode_refresh_token
from common.security.jwt.tokens import generate_access_token

async def generate_new_access_token(refresh_token: str) -> str:
    try:
        payload = decode_refresh_token(refresh_token, token_type="refresh")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = payload.get("sub")
    role = payload.get("role")
    session_id = payload.get("session_id")

    if not user_id or not role or not session_id:
        raise HTTPException(status_code=400, detail="Malformed token")

    session_key = f"sessions:{user_id}:{session_id}"
    if not get(session_key):
        raise HTTPException(status_code=401, detail="Session is no longer active")

    return await generate_access_token(
        user_id=user_id,
        role=role,
        session_id=session_id,
        scopes=payload.get("scopes")  # Optional: preserve original scopes
    )