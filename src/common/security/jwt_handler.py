import os
from datetime import datetime, timedelta, timezone
from typing import Dict
import jwt
from dotenv import load_dotenv
from fastapi import HTTPException, status, Request
from uuid import uuid4
from infrastructure.database.redis.redis_client import get, setex, keys, delete
from infrastructure.database.mongodb.mongo_client import find_one
from common.logging.logger import log_info, log_error, log_warning

load_dotenv()

# Environment variables
ACCESS_SECRET = os.getenv("SECRET_KEY")
REFRESH_SECRET = os.getenv("REFRESH_SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
TEMP_TOKEN_TTL = int(os.getenv("JWT_TEMP_TTL", 300))  # 5 minutes
ACCESS_TTL = int(os.getenv("JWT_ACCESS_TTL", 900))  # 15 mins
REFRESH_TTL = int(os.getenv("JWT_REFRESH_TTL", 86400))  # 1 day

# Security assertions
if not ACCESS_SECRET or len(ACCESS_SECRET) < 32:
    raise RuntimeError("SECRET_KEY must be at least 32 characters long")
if not REFRESH_SECRET or len(REFRESH_SECRET) < 32:
    raise RuntimeError("REFRESH_SECRET_KEY must be at least 32 characters long")


class JWTError(Exception):
    pass


# Token Generation

def generate_temp_token(phone: str, role: str, jti: str = None, phone_verified: bool = False) -> str:
    jti = jti or str(uuid4())
    payload = {
        "sub": phone,
        "role": role,
        "jti": jti,
        "phone_verified": phone_verified,
        "exp": datetime.now(timezone.utc) + timedelta(seconds=TEMP_TOKEN_TTL),
        "iat": int(datetime.now(timezone.utc).timestamp())
    }
    try:
        token = jwt.encode(payload, ACCESS_SECRET, algorithm=ALGORITHM)
        log_info("Temp token generated", extra={"phone": phone, "role": role, "jti": jti})
        return token
    except Exception as e:
        log_error("Temp token generation failed", extra={"phone": phone, "error": str(e)})
        raise JWTError(f"Failed to generate temp token: {str(e)}")


def generate_access_token(user_id: str, role: str, session_id: str, scopes: list[str] = None) -> str:
    jti = str(uuid4())
    collection = "admins" if role == "admin" else "vendors" if role == "vendor" else "users"
    user_data = find_one(collection, {"_id": user_id})
    if not user_data:
        log_error("User not found for token", extra={"user_id": user_id, "role": role})
        raise JWTError(f"No {role} found with ID: {user_id}")

    payload = {
        "sub": user_id,
        "role": role,
        "jti": jti,
        "session_id": session_id,
        "exp": datetime.now(timezone.utc) + timedelta(seconds=ACCESS_TTL),
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "scopes": scopes or (
            ["admin:read", "admin:write"] if role == "admin" else
            ["vendor:read", "vendor:write"] if role == "vendor" else
            ["read"]
        ),
        "status": user_data.get("status", "unknown"),
        "vendor_id": user_id if role == "vendor" else None,
        "phone": user_data.get("phone"),
        "phone_verified": user_data.get("phone_verified", False),
        "account_verified": user_data.get("account_verified", False)
    }
    try:
        token = jwt.encode(payload, ACCESS_SECRET, algorithm=ALGORITHM)
        log_info("Access token generated", extra={"user_id": user_id, "jti": jti})
        return token
    except Exception as e:
        log_error("Access token generation failed", extra={"user_id": user_id, "error": str(e)})
        raise JWTError(f"Failed to generate access token: {str(e)}")


def generate_refresh_token(user_id: str, role: str, session_id: str) -> str:
    jti = str(uuid4())
    payload = {
        "sub": user_id,
        "role": role,
        "jti": jti,
        "session_id": session_id,
        "exp": datetime.now(timezone.utc) + timedelta(seconds=REFRESH_TTL),
        "iat": int(datetime.now(timezone.utc).timestamp())
    }
    try:
        token = jwt.encode(payload, REFRESH_SECRET, algorithm=ALGORITHM)
        redis_key = f"refresh_tokens:{user_id}:{jti}"
        setex(redis_key, REFRESH_TTL, "valid")

        # Limit refresh tokens to 5
        all_keys = keys(f"refresh_tokens:{user_id}:*")
        if len(all_keys) > 5:
            sorted_keys = sorted(all_keys, key=lambda k: get(k) or "")
            for old_key in sorted_keys[:-5]:
                delete(old_key)
                old_jti = old_key.split(":")[-1]
                setex(f"blacklist:{old_jti}", REFRESH_TTL, "revoked")
                log_info("Old refresh token removed", extra={"user_id": user_id, "key": old_key})

        log_info("Refresh token generated", extra={"user_id": user_id, "jti": jti})
        return token

    except Exception as e:
        log_error("Refresh token generation failed", extra={"user_id": user_id, "error": str(e)})
        raise JWTError(f"Failed to generate refresh token: {str(e)}")


# Token Validation

def decode_token(token: str, token_type: str = "access") -> Dict:
    secret = ACCESS_SECRET if token_type in ["access", "temp"] else REFRESH_SECRET
    try:
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
        jti = payload.get("jti")
        if not jti:
            raise JWTError("Token missing jti")
        if get(f"blacklist:{jti}"):
            log_error("Token revoked", extra={"jti": jti, "type": token_type})
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")
        if token_type == "refresh":
            user_id = payload.get("sub")
            redis_key = f"refresh_tokens:{user_id}:{jti}"
            if not get(redis_key):
                revoke_all_user_tokens(user_id)
                log_error("Refresh token reuse detected", extra={"user_id": user_id, "jti": jti})
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token reuse detected")
        log_info("Token decoded", extra={"jti": jti, "type": token_type})
        return payload
    except jwt.ExpiredSignatureError:
        log_error("Token expired", extra={"token_type": token_type})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError as e:
        log_error("Invalid token", extra={"token_type": token_type, "error": str(e)})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {str(e)}")


# Token Utilities

def revoke_token(jti: str, ttl: int):
    try:
        setex(f"blacklist:{jti}", ttl, "revoked")
        log_info("Token revoked", extra={"jti": jti, "ttl": ttl})
    except Exception as e:
        log_error("Token revocation failed", extra={"jti": jti, "error": str(e)})
        raise JWTError(f"Failed to revoke token: {str(e)}")


def revoke_all_user_tokens(user_id: str):
    try:
        refresh_keys = keys(f"refresh_tokens:{user_id}:*")
        for key in refresh_keys:
            jti = key.split(":")[-1]
            delete(key)
            setex(f"blacklist:{jti}", REFRESH_TTL, "revoked")
            log_info("Refresh token revoked", extra={"user_id": user_id, "jti": jti})
        session_keys = keys(f"sessions:{user_id}:*")
        for key in session_keys:
            delete(key)
            log_info("Session removed", extra={"user_id": user_id, "key": key})
    except Exception as e:
        log_error("Revoke all tokens failed", extra={"user_id": user_id, "error": str(e)})
        raise JWTError(f"Failed to revoke all tokens: {str(e)}")


# Authentication

def get_token_from_header(request: Request) -> str:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header missing or invalid")
    return auth_header.split(" ")[1]


async def get_current_user(request: Request) -> Dict:
    token = get_token_from_header(request)
    try:
        payload = decode_token(token, "access")
        user_id = payload.get("sub")
        role = payload.get("role")
        session_id = payload.get("session_id")
        if not all([user_id, role, session_id]):
            log_error("Invalid token payload", extra={"payload": payload})
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

        collection = "admins" if role == "admin" else "vendors" if role == "vendor" else "users"
        user = find_one(collection, {"_id": user_id})
        if not user:
            log_error("User not found for token", extra={"user_id": user_id, "role": role})
            raise HTTPException(status_code=401, detail=f"No {role} found with ID: {user_id}")

        log_info("User authenticated", extra={"user_id": user_id, "role": role})
        return {"user_id": user_id, "role": role, "session_id": session_id}
    except HTTPException as e:
        raise e
    except Exception as e:
        log_error("User authentication failed", extra={"token": token[:10], "error": str(e)})
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")