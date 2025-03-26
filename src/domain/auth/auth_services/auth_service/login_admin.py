# File: domain/auth/auth_services/auth_service/login_admin.py

from fastapi import HTTPException, status
from common.security.jwt_handler import generate_access_token, generate_refresh_token
from common.security.password import verify_password
from common.security.permissions_loader import get_scopes_for_role
from infrastructure.database.mongodb.mongo_client import find_one
from infrastructure.database.redis.redis_client import hset, setex
from common.logging.logger import log_info, log_error
from datetime import datetime, timezone
from uuid import uuid4


async def login_admin_service(username: str, password: str, client_ip: str) -> dict:
    try:
        # Clean username
        username = username.strip().lower()

        # Find admin in MongoDB
        admin = await find_one("admins", {"username": username})
        if not admin:
            log_error("Admin not found", extra={"username": username, "ip": client_ip})
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        if "password" not in admin:
            log_error("Admin has no password set", extra={"username": username, "ip": client_ip})
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        # Verify password
        if not verify_password(password, admin["password"]):
            log_error("Password verification failed", extra={"username": username, "ip": client_ip})
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        # Check account status
        if admin.get("status") != "active":
            log_error("Admin account not active", extra={
                "username": username,
                "status": admin.get("status"),
                "ip": client_ip
            })
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Account status: {admin.get('status')}")

        # Generate tokens
        admin_id = str(admin["_id"])
        role = "admin"
        session_id = str(uuid4())

        scopes = get_scopes_for_role(role)
        access_token = await generate_access_token(
            user_id=admin_id,
            role=role,
            session_id=session_id,
            scopes=scopes
        )
        refresh_token = await generate_refresh_token(admin_id, role, session_id)

        # Store session info in Redis
        session_key = f"sessions:{admin_id}:{session_id}"
        hset(session_key, mapping={
            "ip": client_ip,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "device": "unknown",
            "status": "active"
        })
        setex(session_key, 86400, "active")  # 24 hours TTL

        # Log success
        log_info("Admin login successful", extra={
            "admin_id": admin_id,
            "username": username,
            "ip": client_ip,
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "message": "Admin login successful"
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        log_error("Admin login failed", extra={
            "username": username if "username" in locals() else "unknown",
            "error": str(e),
            "ip": client_ip
        }, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to login admin")