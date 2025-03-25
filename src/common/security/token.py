from jose import jwt
from datetime import datetime, timedelta, UTC
import uuid
import os

SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

def generate_access_token(
    user_id: str,
    role: str,
    scopes: list = None,
    ttl: int = 900,
    **extra_payload
) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "role": role,
        "scopes": scopes or [],
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl)).timestamp()),
        "jti": str(uuid.uuid4()),
        **extra_payload
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_refresh_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
