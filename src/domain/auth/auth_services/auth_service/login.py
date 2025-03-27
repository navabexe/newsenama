# login_service.py - نسخه اصلاح‌شده با بررسی نوع کلید Redis قبل از hset

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from redis.asyncio import Redis

from common.logging.logger import log_info, log_error
from common.security.jwt.tokens import generate_access_token, generate_refresh_token
from common.security.password import verify_password
from common.security.permissions_loader import get_scopes_for_role
from infrastructure.database.mongodb.mongo_client import find_one
from infrastructure.database.redis.operations.hset import hset
from infrastructure.database.redis.operations.expire import expire
from infrastructure.database.redis.redis_client import get_redis_client


async def login_service(
    phone: str | None,
    username: str | None,
    password: str,
    client_ip: str,
    language: str = "fa",
    redis: Redis = None
) -> dict:
    try:
        if redis is None:
            redis = await get_redis_client()

        if not phone and not username:
            raise HTTPException(status_code=400, detail="Phone or username is required")
        if phone and username:
            raise HTTPException(status_code=400, detail="Provide either phone or username, not both")

        phone = phone.strip() if phone else None
        username = username.strip().lower() if username else None

        user = None
        collection = None
        if phone:
            user = await find_one("users", {"phone": phone})
            collection = "users"
            if not user:
                user = await find_one("vendors", {"phone": phone})
                collection = "vendors"
        else:
            user = await find_one("admins", {"username": username})
            collection = "admins"

        if not user:
            log_error("User not found", extra={"phone": phone, "username": username, "ip": client_ip})
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if "password" not in user or not user["password"]:
            log_error("User has no password set", extra={"id": str(user['_id']), "ip": client_ip})
            raise HTTPException(status_code=401, detail="Password not set")

        if not verify_password(password, user["password"]):
            log_error("Invalid password", extra={"id": str(user['_id']), "ip": client_ip})
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if user.get("status") != "active":
            raise HTTPException(status_code=403, detail="Account not active")

        user_id = str(user["_id"])
        role = user.get("role", "admin" if collection == "admins" else "vendor" if collection == "vendors" else "user")
        session_id = str(uuid4())
        scopes = get_scopes_for_role(role, user.get("status"))

        user_profile = {
            "first_name": str(user.get("first_name")) if user.get("first_name") else None,
            "last_name": str(user.get("last_name")) if user.get("last_name") else None,
            "email": str(user.get("email")) if user.get("email") else None,
            "phone": str(user.get("phone")) if user.get("phone") else None,
            "business_name": str(user.get("business_name")) if user.get("business_name") else None,
            "location": user.get("location"),
            "address": str(user.get("address")) if user.get("address") else None,
            "status": user.get("status"),
            "business_category_ids": user.get("business_category_ids", []),
            "profile_picture": str(user.get("profile_picture")) if user.get("profile_picture") else None
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
        if key_type != b'hash' and key_type != b'none':
            await redis.delete(session_key)

        await hset(session_key, mapping={
            "ip": client_ip,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "device": "unknown",
            "status": "active",
            "jti": session_id
        }, redis=redis)

        if role == "admin":
            await expire(session_key, 86400, redis=redis)

        log_info("Login successful", extra={
            "user_id": user_id,
            "role": role,
            "session_id": session_id,
            "ip": client_ip
        })

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "role": role,
            "message": "Login successful"
        }

    except HTTPException:
        raise
    except Exception as e:
        log_error("Login service failed", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(status_code=500, detail="Login failed")
