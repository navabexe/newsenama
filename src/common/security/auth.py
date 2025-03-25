from fastapi import HTTPException, Request
from jose import JWTError, jwt
from infrastructure.database.redis.redis_client import redis
from common.security.jwt_handler import ACCESS_SECRET, ALGORITHM
from common.logging.logger import log_warning

def decode_jwt(token: str):
    try:
        payload = jwt.decode(token, ACCESS_SECRET, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        log_warning("JWT decode failed", extra={"error": str(e)})
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_token_from_header(request: Request) -> str:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header missing or invalid")

    return auth_header.split(" ")[1]


async def get_current_user(request: Request) -> dict:
    token = get_token_from_header(request)
    payload = decode_jwt(token)

    jti = payload.get("jti")
    user_id = payload.get("sub")
    role = payload.get("role")

    if not user_id or not role:
        raise HTTPException(status_code=401, detail="Token payload invalid")

    # === Check if token is blacklisted ===
    if jti and redis and redis.get(f"token:blacklist:{jti}"):
        raise HTTPException(status_code=401, detail="Token is blacklisted")

    # === Check if user is globally blocked ===
    if redis and redis.get(f"token:blacklist:user:{user_id}"):
        raise HTTPException(status_code=401, detail="User sessions are revoked")

    return payload
