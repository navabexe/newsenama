from fastapi import HTTPException, status
from common.security.jwt_handler import generate_access_token, generate_refresh_token
from common.security.password import verify_password
from infrastructure.database.redis.redis_client import hset
from infrastructure.database.mongodb.mongo_client import find_one
from common.logging.logger import log_info, log_error
from datetime import datetime, timezone
from uuid import uuid4


async def login_password_service(phone: str, password: str, client_ip: str) -> dict:
    try:
        phone = phone.strip()

        # Check both user and vendor collections
        user = await find_one("users", {"phone": phone})
        collection = "users"
        if not user:
            user = await find_one("vendors", {"phone": phone})
            collection = "vendors"

        if not user:
            log_error("User not found", extra={"phone": phone, "ip": client_ip})
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        if "password" not in user or not user["password"]:
            log_error("User has no password set", extra={"phone": phone, "ip": client_ip})
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        # Account must be active
        if user.get("status") != "active":
            log_error("Account not active", extra={
                "phone": phone,
                "status": user.get("status"),
                "ip": client_ip
            })
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Account status: {user.get('status')}")

        # Verify password using bcrypt
        if not verify_password(password, user["password"]):
            log_error("Password verification failed", extra={"phone": phone, "ip": client_ip})
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        user_id = str(user["_id"])
        role = user["role"]

        # Define scopes based on role
        scopes = ["read"] if role == "user" else ["vendor:read", "vendor:write"]

        # Generate session and tokens
        session_id = str(uuid4())
        access_token = generate_access_token(user_id, role, session_id, scopes=scopes)
        refresh_token = generate_refresh_token(user_id, role, session_id)

        # Store session info in Redis
        session_key = f"sessions:{user_id}:{session_id}"
        hset(session_key, mapping={
            "ip": client_ip,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "device": "unknown",
            "status": "active"
        })

        # Logging successful login
        log_info("Login successful with password", extra={
            "user_id": user_id,
            "role": role,
            "collection": collection,
            "phone": phone,
            "ip": client_ip,
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "message": "Login successful"
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        log_error("Login with password failed", extra={
            "phone": phone,
            "error": str(e),
            "ip": client_ip
        }, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to login")
