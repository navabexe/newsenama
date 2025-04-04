from datetime import datetime, timezone
from uuid import uuid4
from typing import Dict, Optional

from redis.asyncio import Redis

from common.logging.logger import log_info, log_error
from common.security.jwt.tokens import generate_access_token, generate_refresh_token
from common.security.password import verify_password
from common.security.permissions_loader import get_scopes_for_role
from common.translations.messages import get_message
from common.exceptions.base_exception import (
    BadRequestException,
    UnauthorizedException,
    ForbiddenException,
    InternalServerErrorException,
    TooManyRequestsException
)

from infrastructure.database.mongodb.mongo_client import find_one
from infrastructure.database.redis.operations.hset import hset
from infrastructure.database.redis.operations.expire import expire
from infrastructure.database.redis.redis_client import get_redis_client

MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 600  # 10 minutes


async def login_service(
    phone: Optional[str],
    username: Optional[str],
    password: str,
    client_ip: str,
    language: str = "fa",
    redis: Redis = None
) -> Dict:
    """
    Authenticate user/vendor/admin and return access/refresh tokens.
    Includes brute-force protection, logging, and scoped token generation.
    """
    try:
        if redis is None:
            redis = await get_redis_client()

        if not phone and not username:
            raise BadRequestException(detail=get_message("auth.login.missing_credentials", language))
        if phone and username:
            raise BadRequestException(detail=get_message("auth.login.too_many_credentials", language))

        identifier = (phone or username).strip().lower()
        login_key = f"login:attempt:{client_ip}:{identifier}"
        attempts = int(await redis.get(login_key) or 0)

        if attempts >= MAX_ATTEMPTS:
            raise TooManyRequestsException(detail=get_message("auth.login.too_many_attempts", language))

        phone = phone.strip() if phone else None
        username = username.strip().lower() if username else None

        user = None
        collection = None

        if phone:
            user = await find_one("users", {"phone": phone}) or await find_one("vendors", {"phone": phone})
            collection = "vendors" if user and user.get("type") == "vendor" else "users"
        else:
            user = await find_one("admins", {"username": username})
            collection = "admins"

        if not user:
            await redis.incr(login_key)
            await redis.expire(login_key, LOCKOUT_SECONDS)
            raise UnauthorizedException(detail=get_message("auth.login.invalid", language))

        if not user.get("password"):
            await redis.incr(login_key)
            await redis.expire(login_key, LOCKOUT_SECONDS)
            raise UnauthorizedException(detail=get_message("auth.login.no_password", language))

        if not verify_password(password, user["password"]):
            await redis.incr(login_key)
            await redis.expire(login_key, LOCKOUT_SECONDS)
            raise UnauthorizedException(detail=get_message("auth.login.invalid", language))

        if user.get("status") != "active":
            raise ForbiddenException(detail=get_message("auth.login.not_active", language))

        await redis.delete(login_key)  # Clear failed attempts

        user_id = str(user["_id"])
        role = user.get("role", "admin" if collection == "admins" else "vendor" if collection == "vendors" else "user")
        session_id = str(uuid4())
        scopes = get_scopes_for_role(role, user.get("status"))

        user_profile = {
            "first_name": user.get("first_name"),
            "last_name": user.get("last_name"),
            "email": user.get("email"),
            "phone": user.get("phone"),
            "business_name": user.get("business_name"),
            "location": user.get("location"),
            "address": user.get("address"),
            "status": user.get("status"),
            "business_category_ids": user.get("business_category_ids", []),
            "profile_picture": user.get("profile_picture"),
            "preferred_languages": user.get("preferred_languages", [])
        }

        access_token = await generate_access_token(
            user_id=user_id,
            role=role,
            session_id=session_id,
            scopes=scopes,
            user_profile=user_profile,
            language=language
        )

        refresh_token = await generate_refresh_token(
            user_id=user_id,
            role=role,
            session_id=session_id,
        )

        session_key = f"sessions:{user_id}:{session_id}"
        key_type = await redis.type(session_key)
        if key_type not in [b"hash", b"none"]:
            await redis.delete(session_key)

        await hset(
            session_key,
            mapping={
                "ip": client_ip,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "device": "unknown",
                "status": "active",
                "jti": session_id
            },
            redis=redis
        )

        if role == "admin":
            await expire(session_key, 86400, redis=redis)

        log_info("Login successful", extra={
            "user_id": user_id,
            "role": role,
            "session_id": session_id,
            "ip": client_ip,
            "endpoint": "login_service"
        })

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 3600,
            "role": role
        }

    except Exception as e:
        log_error("Login service failed", extra={"error": str(e)}, exc_info=True)
        raise InternalServerErrorException(detail=get_message("server.error", language))
