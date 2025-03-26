from fastapi import HTTPException, status
from common.security.jwt_handler import generate_access_token, generate_refresh_token
from common.security.permissions_loader import get_scopes_for_role
from infrastructure.database.mongodb.mongo_client import find_one, update_one, insert_one
from infrastructure.database.redis.redis_client import delete, keys, hset
from common.logging.logger import log_info, log_error
from datetime import datetime, timezone
from uuid import uuid4

async def notify_vendor_of_status(vendor_id: str, phone: str, status: str, client_ip: str):
    try:
        message = "Your vendor profile has been approved!" if status == "active" else "Your vendor profile was rejected."
        notification = {
            "receiver_type": "vendor",
            "receiver_id": vendor_id,
            "title": "Profile Status Update",
            "body": message,
            "channel": "sms",
            "reference_type": "vendor",
            "reference_id": vendor_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        insert_one("notifications", notification)
        log_info("Vendor notified", extra={"vendor_id": vendor_id, "status": status, "ip": client_ip})
    except Exception as e:
        log_error("Failed to notify vendor", extra={"vendor_id": vendor_id, "error": str(e)})
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to notify vendor")

async def approve_vendor_service(current_user: dict, vendor_id: str, action: str, client_ip: str) -> dict:
    try:
        # Check admin access
        if current_user["role"] != "admin":
            log_error("Unauthorized approval attempt", extra={"user_id": current_user["user_id"], "vendor_id": vendor_id})
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

        # Find vendor
        vendor = find_one("vendors", {"_id": vendor_id})
        if not vendor or vendor["status"] != "pending":
            log_error("Vendor not found or not pending", extra={"vendor_id": vendor_id, "ip": client_ip})
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Vendor not eligible for approval")

        # Update status and account_verified (if approved)
        new_status = "active" if action == "approve" else "rejected"
        update_data = {
            "status": new_status,
            "updated_at": datetime.now(timezone.utc),
            "updated_by": current_user["user_id"]
        }
        if action == "approve":
            update_data["account_verified"] = True  # اضافه کردن این خط

        modified_count = update_one("vendors", {"_id": vendor_id}, update_data)
        if modified_count == 0:
            log_error("Failed to update vendor status", extra={"vendor_id": vendor_id, "ip": client_ip})
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update status")

        # If rejected, invalidate temp tokens
        if action == "reject":
            temp_keys = keys(f"temp_token:*:{vendor['phone']}")
            for key in temp_keys:
                delete(key)
                log_info("Temp token deleted", extra={"vendor_id": vendor_id, "key": key})

        # Notify vendor
        await notify_vendor_of_status(vendor_id, vendor["phone"], new_status, client_ip)

        # If approved, generate full tokens
        response = {"message": f"Vendor {action}ed successfully"}
        if action == "approve":
            session_id = str(uuid4())
            vendor_status = new_status
            access_token = generate_access_token(
                user_id=vendor_id,
                role="vendor",
                session_id=session_id,
                scopes=get_scopes_for_role("vendor", vendor_status)
            )

            refresh_token = generate_refresh_token(vendor_id, "vendor", session_id)

            response.update({
                "access_token": access_token,
                "refresh_token": refresh_token
            })
        log_info(f"Vendor {action}ed", extra={
            "vendor_id": vendor_id,
            "new_status": new_status,
            "admin_id": current_user["user_id"],
            "ip": client_ip,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return response

    except HTTPException as e:
        raise e
    except Exception as e:
        log_error("Vendor approval failed", extra={
            "vendor_id": vendor_id,
            "error": str(e),
            "ip": client_ip
        })
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to process approval")