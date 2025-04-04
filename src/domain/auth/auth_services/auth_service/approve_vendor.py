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
from common.exceptions.base_exception import (
    NotFoundException,
    ForbiddenException,
    BadRequestException,
    InternalServerErrorException,
    UnauthorizedException
)

async def notify_vendor_of_status(vendor_id: str, phone: str, status: str, client_ip: str, language: str):
    """Notify vendor about approval/rejection via SMS."""
    try:
        message_key = "vendor.approved" if status == "active" else "vendor.rejected"
        notification = {
            "receiver_type": "vendor",
            "receiver_id": vendor_id,
            "title": get_message("vendor.status_update.title", language),
            "body": get_message(message_key, language),
            "channel": "sms",
            "reference_type": "vendor",
            "reference_id": vendor_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await insert_one("notifications", notification)
        log_info("Vendor notified successfully", extra={"vendor_id": vendor_id, "status": status, "ip": client_ip})
    except Exception as e:
        log_error("Failed notifying vendor", extra={"vendor_id": vendor_id, "error": str(e)}, exc_info=True)
        raise InternalServerErrorException(detail=get_message("server.error", language))

async def approve_vendor_service(
    current_user: dict,
    vendor_id: str,
    action: str,
    client_ip: str,
    redis: Redis,
    language: str = "fa"
) -> dict:
    """Approve or reject vendor profiles (admin-only action)."""
    try:
        if current_user.get("role") != "admin":
            log_error("Unauthorized attempt detected", extra={"user_id": current_user.get("user_id"), "ip": client_ip})
            raise ForbiddenException(detail=get_message("auth.forbidden", language))

        if action not in {"approve", "reject"}:
            raise BadRequestException(detail=get_message("vendor.invalid_action", language))

        if not ObjectId.is_valid(vendor_id):
            raise BadRequestException(detail=get_message("vendor.invalid_id", language))

        vendor = await find_one("vendors", {"_id": ObjectId(vendor_id)})
        if not vendor or vendor.get("status") != "pending":
            raise NotFoundException(detail=get_message("vendor.not_pending", language))

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
            raise InternalServerErrorException(detail=get_message("server.error", language))

        if action == "reject":
            temp_keys = await keys(f"temp_token:*:{vendor['phone']}", redis=redis)
            for key in temp_keys:
                await delete(key, redis=redis)
                log_info("Temporary tokens removed", extra={"vendor_id": vendor_id, "key": key})

        await notify_vendor_of_status(str(vendor["_id"]), vendor["phone"], new_status, client_ip, language)

        result = {"status": new_status, "message": get_message(f"vendor.{action}ed", language)}

        if action == "approve":
            session_id = str(uuid4())
            device = "unknown"
            scopes = get_scopes_for_role("vendor", new_status)

            user_profile = {
                "first_name": vendor.get("owner_name", ""),
                "phone": vendor.get("phone"),
                "business_name": vendor.get("business_name"),
                "location": vendor.get("location"),
                "address": vendor.get("address"),
                "status": new_status,
                "business_category_ids": vendor.get("business_category_ids", []),
                "profile_picture": vendor.get("profile_picture", ""),
                "preferred_languages": vendor.get("preferred_languages", [])
            }

            access_token = await generate_access_token(
                user_id=str(vendor["_id"]), role="vendor",
                session_id=session_id, user_profile=user_profile,
                language=language, scopes=scopes
            )
            refresh_token = await generate_refresh_token(
                user_id=str(vendor["_id"]), role="vendor",
                session_id=session_id
            )

            session_key = f"sessions:{vendor['_id']}:{session_id}"
            await hset(session_key, mapping={
                "ip": client_ip,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "device": device, "status": "active", "jti": session_id
            }, redis=redis)
            await expire(session_key, 86400, redis=redis)

            result.update({"access_token": access_token, "refresh_token": refresh_token})

        log_info("Vendor approval action completed", extra={"vendor_id": vendor_id, "status": new_status})
        return result

    except HTTPException:
        raise
    except Exception as e:
        log_error("Unexpected error", extra={"error": str(e)}, exc_info=True)
        raise InternalServerErrorException(detail=get_message("server.error", language))
