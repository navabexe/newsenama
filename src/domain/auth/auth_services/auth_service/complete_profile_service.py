from datetime import datetime, timezone
from uuid import uuid4
from typing import Optional, List

from bson import ObjectId
from redis.asyncio import Redis
from fastapi import HTTPException, Request

from common.translations.messages import get_message
from common.logging.logger import log_error, log_info
from common.exceptions.base_exception import (
    BadRequestException, ForbiddenException, InternalServerErrorException, UnauthorizedException
)
from common.security.jwt.tokens import generate_access_token, generate_refresh_token
from common.security.jwt.decode import decode_token
from common.utils.ip_utils import extract_client_ip

from domain.auth.entities.token_entity import UserJWTProfile, VendorJWTProfile
from domain.notification.notification_services.builder import build_notification_content
from domain.notification.notification_services.dispatcher import dispatch_notification
from domain.notification.entities.notification_entity import NotificationChannel

from infrastructure.database.mongodb.mongo_client import find_one, update_one, find
from infrastructure.database.redis.redis_client import get_redis_client
from infrastructure.database.redis.operations.delete import delete
from infrastructure.database.redis.operations.scan import scan_keys
from infrastructure.database.redis.operations.expire import expire
from infrastructure.database.redis.operations.hset import hset


async def delete_all_sessions(user_id: str, redis: Redis):
    keys = await scan_keys(redis, f"sessions:{user_id}:*")
    for key in keys:
        await redis.delete(key)


def normalize_vendor_data(data: dict) -> dict:
    return {
        **data,
        "logo_urls": data.get("logo_urls") or [],
        "banner_urls": data.get("banner_urls") or [],
        "preferred_languages": data.get("preferred_languages") or [],
        "account_types": data.get("account_types") or [],
        "show_followers_publicly": data.get("show_followers_publicly", True),
    }


async def validate_business_categories(ids: List[str]):
    query_ids = [ObjectId(cid) if ObjectId.is_valid(cid) else cid for cid in ids]
    existing = await find("business_categories", {"_id": {"$in": query_ids}})
    found_ids = {str(doc["_id"]) for doc in existing}
    invalid = set(ids) - found_ids
    if invalid:
        raise BadRequestException(detail=f"Invalid business category IDs: {', '.join(invalid)}")


async def complete_profile_service(
    temporary_token: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    email: Optional[str] = None,
    business_name: Optional[str] = None,
    city: Optional[str] = None,
    province: Optional[str] = None,
    location: Optional[dict] = None,
    address: Optional[str] = None,
    business_category_ids: Optional[List[str]] = None,
    visibility: Optional[str] = "COLLABORATIVE",
    vendor_type: Optional[str] = None,
    languages: Optional[List[str]] = None,
    request: Optional[Request] = None,
    language: str = "fa",
    redis: Redis = None
) -> dict:
    try:
        redis = redis or await get_redis_client()
        payload = await decode_token(temporary_token, token_type="temp", redis=redis)

        phone = payload.get("sub")
        role = payload.get("role")
        jti = payload.get("jti")

        if not phone or role not in ["user", "vendor"]:
            raise UnauthorizedException(detail=get_message("token.invalid", language))

        temp_key = f"temp_token:{jti}"
        stored_phone = await redis.get(temp_key)
        if stored_phone != phone:
            raise UnauthorizedException(detail=get_message("otp.expired", language))

        if role == "user" and any([business_name, business_category_ids, city, province, location, address, vendor_type]):
            raise ForbiddenException(detail=get_message("auth.forbidden", language))

        if role == "vendor" and not business_name:
            raise BadRequestException(detail=get_message("vendor.not_eligible", language))

        collection = f"{role}s"
        user = await find_one(collection, {"phone": phone})
        if not user or user.get("status") not in ["incomplete", "pending"]:
            raise BadRequestException(detail=get_message(f"{role}.not_eligible", language))

        user_id = str(user["_id"])
        update_data = {"updated_at": datetime.now(timezone.utc)}

        if role == "user":
            if not first_name or not last_name:
                raise BadRequestException(detail=get_message("auth.profile.incomplete", language))
            update_data.update({
                "first_name": first_name.strip(),
                "last_name": last_name.strip(),
                "email": email.strip().lower() if email else None,
                "preferred_languages": languages or [],
                "status": "active"
            })

        if role == "vendor":
            if first_name: update_data["first_name"] = first_name.strip()
            if last_name: update_data["last_name"] = last_name.strip()
            if business_category_ids: await validate_business_categories(business_category_ids)
            update_data.update({
                "business_name": business_name.strip(),
                "city": city.strip() if city else None,
                "province": province.strip() if province else None,
                "location": location,
                "address": address.strip() if address else None,
                "visibility": visibility,
                "vendor_type": vendor_type,
                "preferred_languages": languages or [],
                "business_category_ids": business_category_ids or []
            })

        await update_one(collection, {"_id": ObjectId(user_id)}, update_data)
        updated_user = await find_one(collection, {"_id": ObjectId(user_id)})

        if role == "vendor" and updated_user.get("status") == "incomplete":
            required = ["business_name", "city", "province", "location", "address", "business_category_ids"]
            if all(updated_user.get(f) for f in required):
                await update_one(collection, {"_id": ObjectId(user_id)}, {"status": "pending"})
                updated_user["status"] = "pending"

        await delete(temp_key, redis)
        await delete_all_sessions(user_id, redis)

        session_id = str(uuid4())
        if role == "vendor":
            updated_user = normalize_vendor_data(updated_user)

        profile_model = UserJWTProfile if role == "user" else VendorJWTProfile
        profile_data = profile_model(**updated_user).model_dump()
        token_lang = (languages or [language])[0]
        client_ip = extract_client_ip(request)
        device = getattr(request, 'device_fingerprint', "unknown")

        access_token = await generate_access_token(
            user_id=user_id,
            role=role,
            session_id=session_id,
            user_profile=profile_data if role == "user" else None,
            vendor_profile=profile_data if role == "vendor" else None,
            language=token_lang,
            vendor_id=user_id if role == "vendor" else None
        )

        refresh_token = None
        if role == "user" and updated_user.get("status") == "active":
            refresh_token = await generate_refresh_token(user_id, role, session_id)
            session_key = f"sessions:{user_id}:{session_id}"
            await hset(session_key, {
                "ip": client_ip,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "device": device,
                "status": "active",
                "jti": session_id
            }, redis=redis)
            await expire(session_key, 86400, redis=redis)

        log_info("Profile completed", extra={
            "user_id": user_id,
            "role": role,
            "status": updated_user["status"],
            "ip": client_ip,
            "session_id": session_id,
            "device": device
        })

        try:
            if role == "vendor" and updated_user["status"] == "pending":
                vendor_msg = await build_notification_content("vendor.profile_pending", language, {
                    "name": business_name,
                    "phone": phone
                })
                await dispatch_notification(user_id, "vendor", vendor_msg["title"], vendor_msg["body"], NotificationChannel.INAPP, "profile", user_id)

                admin_msg = await build_notification_content("admin.vendor_submitted", language, {
                    "vendor_name": business_name,
                    "vendor_phone": phone
                })
                await dispatch_notification("admin", "admin", admin_msg["title"], admin_msg["body"], NotificationChannel.INAPP, "profile", user_id)

            elif role == "user" and updated_user["status"] == "active":
                user_msg = await build_notification_content("user.profile_completed", language, {
                    "name": first_name,
                    "phone": phone
                })
                await dispatch_notification(user_id, "user", user_msg["title"], user_msg["body"], NotificationChannel.INAPP, "profile", user_id)

                admin_msg = await build_notification_content("admin.user_joined", language, {
                    "user_name": first_name,
                    "user_phone": phone
                })
                await dispatch_notification("admin", "admin", admin_msg["title"], admin_msg["body"], NotificationChannel.INAPP, "profile", user_id)

        except Exception as notify_err:
            log_error("Profile notification failed", extra={"error": str(notify_err)})

        response_data = {
            "access_token": access_token,
            "status": updated_user["status"]
        }
        if refresh_token:
            response_data["refresh_token"] = refresh_token

        return {
            "meta": {
                "status": "success",
                "code": 200,
                "message": get_message(
                    "auth.profile.pending" if updated_user["status"] == "pending" else "auth.profile.completed",
                    language
                )
            },
            "data": response_data
        }

    except HTTPException:
        raise
    except Exception as e:
        log_error("Profile completion failed", extra={"error": str(e)}, exc_info=True)
        raise InternalServerErrorException(detail=get_message("server.error", language))
