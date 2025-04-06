# File: domain/auth/auth_services/admin/approve_vendor_service.py

from datetime import datetime, timezone
from uuid import uuid4
from bson import ObjectId
from fastapi import HTTPException
from redis.asyncio import Redis

from common.logging.logger import log_info, log_error
from common.security.jwt_handler import generate_access_token, generate_refresh_token
from common.translations.messages import get_message
from common.security.permissions_loader import get_scopes_for_role
from infrastructure.database.mongodb.mongo_client import find_one, update_one, insert_one
from common.exceptions.base_exception import (
    NotFoundException,
    ForbiddenException,
    BadRequestException,
    InternalServerErrorException,
)
from domain.notification.notification_services.builder import build_notification_content
from domain.notification.notification_services.dispatcher import dispatch_notification
from domain.notification.entities.notification_entity import NotificationChannel
from infrastructure.database.redis.operations.redis_operations import expire, incr, get, delete, keys, hset


async def notify_vendor_of_status(vendor_id: str, phone: str, status: str, client_ip: str, language: str) -> bool:
    try:
        message_key = "vendor.approved" if status == "active" else "vendor.rejected"
        content = await build_notification_content(message_key, language)
        await dispatch_notification(
            receiver_id=vendor_id,
            receiver_type="vendor",
            title=content["title"],
            body=content["body"],
            channel=NotificationChannel.INAPP,
            reference_type="vendor",
            reference_id=vendor_id
        )
        # SMS as pending (no real sending yet)
        now = datetime.now(timezone.utc).isoformat()
        await insert_one("notifications", {
            "receiver_type": "vendor",
            "receiver_id": vendor_id,
            "title": content["title"],
            "body": content["body"],
            "channel": "sms",
            "reference_type": "vendor",
            "reference_id": vendor_id,
            "status": "pending",
            "created_at": now
        })
        log_info("Vendor notified successfully", extra={"vendor_id": vendor_id, "status": status, "ip": client_ip})
        return True
    except Exception as e:
        log_error("Failed notifying vendor", extra={"vendor_id": vendor_id, "error": str(e)}, exc_info=True)
        return False

async def log_audit(action: str, details: dict):
    await insert_one("audit_logs", {
        "action": action,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": details
    })

async def approve_vendor_service(
    current_user: dict,
    vendor_id: str,
    action: str,
    client_ip: str,
    redis: Redis,
    language: str = "fa"
) -> dict:
    try:
        # Rate limiting
        rate_limit_key = f"approve_vendor_limit:{current_user.get('user_id')}"
        attempts = await get(rate_limit_key, redis)
        if attempts and int(attempts) >= 10:
            raise BadRequestException(detail=get_message("vendor.too_many", language))
        await incr(rate_limit_key, redis)
        await expire(rate_limit_key, 3600, redis)

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

        notification_sent = await notify_vendor_of_status(str(vendor["_id"]), vendor["phone"], new_status, client_ip, language)

        payload = {
            "status": new_status,
            "notification_sent": notification_sent
        }

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
                "device": device,
                "status": "active",
                "jti": session_id
            }, redis=redis)
            await expire(session_key, 86400, redis=redis)

            payload.update({"access_token": access_token, "refresh_token": refresh_token})

        audit_data = {
            "admin_id": current_user.get("user_id"),
            "vendor_id": vendor_id,
            "action": action,
            "status": new_status,
            "ip": client_ip,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await log_audit(f"vendor_{action}", audit_data)
        log_info("Vendor approval action completed", extra=audit_data)

        return {
            "meta": {
                "status": "success",
                "code": 200,
                "message": get_message(f"vendor.{action}ed", language)
            },
            "data": payload
        }

    except HTTPException:
        raise
    except Exception as e:
        log_error("Unexpected error", extra={"error": str(e)}, exc_info=True)
        raise InternalServerErrorException(detail=get_message("server.error", language))