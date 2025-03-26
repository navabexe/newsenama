# === SERVICE: refresh_token.py ===


from fastapi import HTTPException
from common.security.token import decode_refresh_token, generate_access_token
from infrastructure.database.redis.redis_client import get

def generate_new_access_token(refresh_token: str) -> str:
    try:
        payload = decode_refresh_token(refresh_token)
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

    return generate_access_token(
        user_id=user_id,
        role=role,
        session_id=session_id,
        phone_verified=payload.get("phone_verified", False)
    )
