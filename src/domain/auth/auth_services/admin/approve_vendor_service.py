# File: src/domain/auth/services/admin/approve_vendor_service.py
from datetime import datetime, timezone
from uuid import uuid4
from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis

from common.logging.logger import log_info, log_error
from common.security.jwt_handler import generate_access_token, generate_refresh_token
from common.translations.messages import get_message
from common.security.permissions_loader import get_scopes_for_role
from common.config.settings import settings
from common.exceptions.base_exception import (
    NotFoundException,
    ForbiddenException,
    BadRequestException,
    InternalServerErrorException,
)
from domain.notification.notification_services.notification_service import notification_service
from infrastructure.database.redis.repositories.otp_repository import OTPRepository
from infrastructure.database.mongodb.repositories.auth_repository import AuthRepository

async def approve_vendor_service(
    current_user: dict,
    vendor_id: str,
    action: str,
    client_ip: str,
    redis: Redis,
    db: AsyncIOMotorDatabase,
    language: str = "fa"
) -> dict:
    repo = OTPRepository(redis)
    auth_repo = AuthRepository(db)

    try:
        # Rate limiting
        rate_limit_key = f"approve_vendor_limit:{current_user.get('user_id')}"
        attempts = await repo.get(rate_limit_key)
        if attempts and int(attempts) >= settings.VENDOR_APPROVAL_RATE_LIMIT:
            raise BadRequestException(detail=get_message("vendor.too_many", language))
        await repo.incr(rate_limit_key)
        await repo.expire(rate_limit_key, settings.BLOCK_DURATION)

        if current_user.get("role") != "admin":
            log_error("Unauthorized attempt detected", extra={"user_id": current_user.get("user_id"), "ip": client_ip})
            raise ForbiddenException(detail=get_message("auth.forbidden", language))

        if action not in {"approve", "reject"}:
            raise BadRequestException(detail=get_message("vendor.invalid_action", language))

        if not ObjectId.is_valid(vendor_id):
            raise BadRequestException(detail=get_message("vendor.invalid_id", language))

        vendor = await auth_repo.find_one("vendors", {"_id": ObjectId(vendor_id)})
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

        updated = await auth_repo.update_one("vendors", {"_id": ObjectId(vendor_id)}, update_data)
        if updated == 0:
            raise InternalServerErrorException(detail=get_message("server.error", language))

        if action == "reject":
            temp_keys = await repo.scan_keys(f"temp_token:*:{vendor['phone']}")
            for key in temp_keys:
                await repo.delete(key)
                log_info("Temporary tokens removed", extra={"vendor_id": vendor_id, "key": key})

        # اصلاح نوتیفیکیشن: استفاده از "vendor.approved" به‌جای "vendor.active"
        notification_sent = await notification_service.send(
            receiver_id=str(vendor["_id"]),
            receiver_type="vendor",
            template_key=f"vendor.{action}ed",  # "vendor.approved" یا "vendor.rejected"
            variables={"phone": vendor["phone"]},
            reference_type="vendor",
            reference_id=str(vendor["_id"]),
            language=language,
            return_bool=True
        )

        payload = {
            "status": new_status,
            "notification_sent": notification_sent
        }

        if action == "approve":
            session_id = str(uuid4())
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
                user_id=str(vendor["_id"]),
                role="vendor",
                session_id=session_id,
                user_profile=user_profile,
                language=language,
                scopes=scopes
            )
            refresh_token, refresh_jti = await generate_refresh_token(
                user_id=str(vendor["_id"]),
                role="vendor",
                session_id=session_id,
                return_jti=True
            )

            session_key = f"sessions:{vendor['_id']}:{session_id}"
            now = datetime.now(timezone.utc).isoformat()
            await repo.hset(session_key, mapping={
                b"ip": client_ip.encode(),
                b"created_at": now.encode(),
                b"last_seen_at": now.encode(),
                b"device_name": b"Unknown Device",
                b"device_type": b"Desktop",
                b"os": b"Windows",
                b"browser": b"Chrome",
                b"user_agent": b"Unknown",
                b"location": b"Unknown",
                b"status": b"active",
                b"jti": session_id.encode()
            })
            await repo.expire(session_key, settings.SESSION_EXPIRY)

            await repo.setex(
                f"refresh_tokens:{vendor['_id']}:{refresh_jti}",
                settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
                "active"
            )

            payload.update({"access_token": access_token, "refresh_token": refresh_token})

        audit_data = {
            "admin_id": current_user.get("user_id"),
            "vendor_id": vendor_id,
            "action": action,
            "status": new_status,
            "ip": client_ip,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await auth_repo.log_audit(f"vendor_{action}", audit_data)
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
        log_error("Unexpected error in approve_vendor_service", extra={"error": str(e), "ip": client_ip}, exc_info=True)
        raise InternalServerErrorException(detail=get_message("server.error", language))