from fastapi import HTTPException, status
from common.security.jwt_handler import generate_access_token, generate_refresh_token
from common.security.password import verify_password
from common.security.permissions_loader import get_scopes_for_role
from infrastructure.database.mongodb.mongo_client import find_one
from infrastructure.database.redis.redis_client import hset
from common.logging.logger import log_info, log_error
from datetime import datetime, timezone
from uuid import uuid4

async def login_vendor_service(phone: str, password: str, client_ip: str) -> dict:
    try:
        vendor = find_one("vendors", {"phone": phone})
        if not vendor or "password" not in vendor:
            log_error("Vendor not found or no password set", extra={"phone": phone, "ip": client_ip})
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        if vendor["status"] != "active":
            log_error("Vendor not active", extra={"phone": phone, "status": vendor["status"], "ip": client_ip})
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Account is {vendor['status']}")

        if not verify_password(password, vendor["password"]):
            log_error("Password verification failed", extra={"phone": phone, "ip": client_ip})
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        vendor_id = str(vendor["_id"])
        role = "vendor"
        session_id = str(uuid4())

        vendor_status = vendor["status"]
        access_token = generate_access_token(
            vendor_id,
            role,
            session_id,
            scopes=get_scopes_for_role(role, vendor_status)
        )
        refresh_token = generate_refresh_token(vendor_id, role, session_id)

        hset(f"sessions:{vendor_id}:{session_id}", mapping={
            "ip": client_ip,
            "created_at": datetime.now(timezone.utc).isoformat()
        })

        log_info("Vendor login successful", extra={
            "vendor_id": vendor_id,
            "phone": phone,
            "ip": client_ip,
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
        log_error("Vendor login failed", extra={"phone": phone, "error": str(e), "ip": client_ip})
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to login")