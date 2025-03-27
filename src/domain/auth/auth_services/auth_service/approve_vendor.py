from datetime import datetime, timezone
from uuid import uuid4
from bson import ObjectId
from fastapi import HTTPException, status
from redis.asyncio import Redis

from common.logging.logger import log_info, log_error
from common.translations.messages import get_message
from common.security.permissions_loader import get_scopes_for_role
from common.security.jwt.tokens import generate_access_token, generate_refresh_token
from infrastructure.database.mongodb.mongo_client import find_one, update_one, insert_one
from infrastructure.database.redis.operations.delete import delete
from infrastructure.database.redis.operations.keys import keys
from infrastructure.database.redis.operations.hset import hset
from infrastructure.database.redis.operations.expire import expire


async def notify_vendor_of_status(vendor_id: str, phone: str, status: str, client_ip: str):
    try:
        message = (
            "Your vendor profile has been approved!" if status == "active"
            else "Your vendor profile was rejected."
        )
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
        await insert_one("notifications", notification)
        log_info("Vendor notified", extra={"vendor_id": vendor_id, "status": status, "ip": client_ip})
    except Exception as e:
        log_error("Failed to notify vendor", extra={"vendor_id": vendor_id, "error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to notify vendor")


async def approve_vendor_service(
    current_user: dict,
    vendor_id: str,
    action: str,
    client_ip: str,
    redis: Redis,
    language: str = "fa"
) -> dict:
    try:
        if current_user.get("role") != "admin":
            log_error("Unauthorized approval attempt", extra={"user_id": current_user.get("user_id"), "vendor_id": vendor_id})
            raise HTTPException(status_code=403, detail=get_message("token.invalid", language))

        if not ObjectId.is_valid(vendor_id):
            raise HTTPException(status_code=400, detail="Invalid vendor ID format")

        vendor = await find_one("vendors", {"_id": ObjectId(vendor_id)})
        if not vendor or vendor.get("status") != "pending":
            raise HTTPException(status_code=400, detail="Vendor is not pending approval")

        new_status = "active" if action == "approve" else "rejected"
        update_data = {
            "status": new_status,
            "updated_at": datetime.now(timezone.utc),
            "updated_by": current_user.get("user_id")
        }

        if action == "approve":
            update_data["account_verified"] = True

        updated = await update_one("vendors", {"_id": ObjectId(vendor_id)}, update_data)
        if updated == 0:
            raise HTTPException(status_code=500, detail="Failed to update vendor status")

        # 🔁 حذف توکن‌های موقت فقط در صورت رد شدن
        if action == "reject":
            temp_keys = await keys(f"temp_token:*:{vendor['phone']}", redis=redis)
            for key in temp_keys:
                await delete(key, redis=redis)
                log_info("Temp token deleted", extra={"vendor_id": vendor_id, "key": key})

        # 📢 ارسال پیام اطلاع‌رسانی
        await notify_vendor_of_status(str(vendor["_id"]), vendor["phone"], new_status, client_ip)

        result = {
            "status": new_status,
            "message": f"Vendor {action}ed successfully"
        }

        # ✅ صدور توکن و سشن در صورت تأیید
        if action == "approve":
            session_id = str(uuid4())
            scopes = get_scopes_for_role("vendor", new_status)

            user_profile = {
                "first_name": str(vendor.get("owner_name")) if vendor.get("owner_name") else None,
                "phone": vendor.get("phone"),
                "business_name": vendor.get("business_name"),
                "location": vendor.get("location"),
                "address": vendor.get("address"),
                "status": new_status,
                "business_category_ids": vendor.get("business_category_ids", []),
                "profile_picture": str(vendor.get("profile_picture")) if vendor.get("profile_picture") else None
            }

            access_token = await generate_access_token(
                user_id=str(vendor["_id"]),
                role="vendor",
                session_id=session_id,
                user_profile=user_profile,
                language=language,
                scopes=scopes,
            )

            refresh_token = await generate_refresh_token(
                user_id=str(vendor["_id"]),
                role="vendor",
                session_id=session_id,
            )

            session_key = f"sessions:{vendor['_id']}:{session_id}"
            key_type = await redis.type(session_key)
            key_type_str = key_type.decode() if isinstance(key_type, bytes) else str(key_type)

            if key_type_str not in ["hash", "none"]:
                await redis.delete(session_key)
                log_error("Invalid session key type", extra={"key": session_key, "type": key_type_str})
                raise HTTPException(status_code=401, detail="Invalid session type")

            await hset(session_key, mapping={
                "ip": client_ip,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "device": "unknown",
                "status": "active",
                "jti": session_id
            }, redis=redis)

            await expire(session_key, 86400, redis=redis)

            result.update({
                "access_token": access_token,
                "refresh_token": refresh_token
            })

        log_info(f"Vendor {action}ed", extra={
            "vendor_id": vendor_id,
            "new_status": new_status,
            "admin_id": current_user.get("user_id"),
            "ip": client_ip,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return result

    except HTTPException:
        raise
    except Exception as e:
        log_error("Vendor approval failed", extra={"vendor_id": vendor_id, "error": str(e), "ip": client_ip})
        raise HTTPException(status_code=500, detail=get_message("server.error", language))
