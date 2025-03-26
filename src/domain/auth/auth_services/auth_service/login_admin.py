from fastapi import HTTPException, status
from common.security.jwt_handler import generate_access_token, generate_refresh_token
from common.security.password import hash_password, verify_password  # اضافه کردن bcrypt
from common.security.permissions_loader import get_scopes_for_role
from infrastructure.database.mongodb.mongo_client import find_one
from infrastructure.database.redis.redis_client import hset, get  # برای چک session
from common.logging.logger import log_info, log_error
from datetime import datetime, timezone
from uuid import uuid4

async def login_admin_service(username: str, password: str, client_ip: str) -> dict:
    try:
        # Find admin in MongoDB
        admin = find_one("admins", {"username": username})
        if not admin or "password" not in admin:
            log_error("Admin not found or no password set", extra={"username": username, "ip": client_ip})
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        # Verify password with bcrypt
        if not verify_password(password, admin["password"]):
            log_error("Password verification failed", extra={"username": username, "ip": client_ip})
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        # Check status
        if admin["status"] != "active":
            log_error("Admin account not active", extra={"username": username, "status": admin["status"], "ip": client_ip})
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Account status: {admin['status']}")

        admin_id = str(admin["_id"])
        role = "admin"

        # Generate session ID and tokens
        session_id = str(uuid4())
        access_token = generate_access_token(
            user_id=admin_id,
            role=role,
            session_id=session_id,
            scopes=get_scopes_for_role(role)
        )
        refresh_token = generate_refresh_token(admin_id, role, session_id)

        # Store session info in Redis with TTL (e.g., 1 day)
        session_key = f"sessions:{admin_id}:{session_id}"
        hset(session_key, mapping={
            "ip": client_ip,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "device": "unknown",
            "status": "active"
        })
        # تنظیم TTL برای session (مثلاً 24 ساعت)
        from infrastructure.database.redis.redis_client import setex
        setex(session_key, 86400, "active")  # 24 ساعت

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
        })
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to login admin")