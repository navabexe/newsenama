# File: src/domain/auth/services/profile/complete_profile_service.py
from datetime import datetime, timezone
from typing import Optional, List
from uuid import uuid4

from bson import ObjectId
from fastapi import Request, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis

from common.config.settings import settings
from common.exceptions.base_exception import (
    BadRequestException, ForbiddenException, InternalServerErrorException, UnauthorizedException
)
from common.logging.logger import log_error, log_info
from common.security.jwt_handler import decode_token, generate_access_token, generate_refresh_token
from common.translations.messages import get_message
from common.utils.ip_utils import extract_client_ip
from domain.auth.entities.token_entity import UserJWTProfile, VendorJWTProfile
from domain.auth.services.session_service import get_session_service
from domain.notification.services.notification_service import notification_service
from infrastructure.database.mongodb.repositories.auth_repository import AuthRepository
from infrastructure.database.redis.repositories.otp_repository import OTPRepository


async def validate_business_categories(auth_repo: AuthRepository, ids: List[str], language: str):
    query_ids = [ObjectId(cid) if ObjectId.is_valid(cid) else cid for cid in ids]
    existing = await auth_repo.find("business_categories", {"_id": {"$in": query_ids}})
    found_ids = {str(doc["_id"]) for doc in existing}
    invalid = set(ids) - found_ids
    if invalid:
        raise BadRequestException(detail=f"Invalid business category IDs: {', '.join(invalid)}")

def normalize_vendor_data(data: dict) -> dict:
    return {
        **data,
        "logo_urls": data.get("logo_urls") or [],
        "banner_urls": data.get("banner_urls") or [],
        "preferred_languages": data.get("preferred_languages") or [],
        "account_types": data.get("account_types") or [],
        "show_followers_publicly": data.get("show_followers_publicly", True),
    }

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
    redis: Redis = None,
    db: AsyncIOMotorDatabase = None
) -> dict:
    repo = OTPRepository(redis)
    auth_repo = AuthRepository(db)
    client_ip = await extract_client_ip(request) if request else "unknown"

    # Rate limiting
    rate_limit_key = f"profile_complete_limit:{temporary_token}"
    attempts = await repo.get(rate_limit_key)
    if attempts and int(attempts) >= settings.PROFILE_COMPLETE_RATE_LIMIT:
        raise BadRequestException(detail=get_message("profile.too_many", language))
    await repo.incr(rate_limit_key)
    await repo.expire(rate_limit_key, settings.BLOCK_DURATION)

    try:
        payload = await decode_token(temporary_token, token_type="temp", redis=redis)
        phone = payload.get("sub")
        role = payload.get("role")
        jti = payload.get("jti")

        if not phone or role not in ["user", "vendor"]:
            raise UnauthorizedException(detail=get_message("token.invalid", language))

        temp_key = f"temp_token:{jti}"
        stored_phone = await repo.get(temp_key)
        if stored_phone != phone:
            raise UnauthorizedException(detail=get_message("otp.expired", language))

        if role == "user" and any([business_name, business_category_ids, city, province, location, address, vendor_type]):
            raise ForbiddenException(detail=get_message("auth.forbidden", language))

        if role == "vendor" and not business_name:
            raise BadRequestException(detail=get_message("vendor.not_eligible", language))

        collection = f"{role}s"
        user = await auth_repo.find_one(collection, {"phone": phone})
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
            if business_category_ids: await validate_business_categories(auth_repo, business_category_ids, language)
            if visibility and visibility not in settings.VALID_VISIBILITY:
                raise BadRequestException(detail=f"Visibility must be one of {settings.VALID_VISIBILITY}")
            if vendor_type and vendor_type not in settings.VALID_VENDOR_TYPES:
                raise BadRequestException(detail=f"Vendor type must be one of {settings.VALID_VENDOR_TYPES}")
            update_data.update({
                "business_name": business_name.strip(),
                "city": city.strip() if city else None,
                "province": province.strip() if province else None,
                "location": location,
                "address": address.strip() if address else None,
                "visibility": visibility,
                "vendor_type": vendor_type,
                "preferred_languages": languages or [],
                "business_category_ids": business_category_ids or [],
                "status": "pending" if all([business_name, city, province, location, address, business_category_ids]) else "incomplete"
            })

        await auth_repo.update_one(collection, {"_id": ObjectId(user_id)}, update_data)
        updated_user = await auth_repo.find_one(collection, {"_id": ObjectId(user_id)})
        if not updated_user:
            raise InternalServerErrorException(detail=get_message("server.error", language))

        await repo.delete(temp_key)
        session_service = get_session_service(redis)
        await session_service.delete_incomplete_sessions(user_id)

        session_id = str(uuid4())
        if role == "vendor":
            updated_user = normalize_vendor_data(updated_user)

        profile_model = UserJWTProfile if role == "user" else VendorJWTProfile
        profile_data = profile_model(**updated_user).model_dump()
        token_lang = (languages or [language])[0]
        device = getattr(request, "device_fingerprint", "unknown") if request else "unknown"

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
            refresh_token, refresh_jti = await generate_refresh_token(user_id, role, session_id, return_jti=True)
            session_key = f"sessions:{user_id}:{session_id}"
            await repo.hset(session_key, mapping={
                b"ip": client_ip.encode(),
                b"created_at": datetime.now(timezone.utc).isoformat().encode(),
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
                f"refresh_tokens:{user_id}:{refresh_jti}",
                settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
                "active"
            )

        audit_data = {
            "user_id": user_id,
            "role": role,
            "status": updated_user["status"],
            "ip": client_ip,
            "session_id": session_id,
            "device": device,
            "request_id": getattr(request, "request_id", None) if request else None,
            "client_version": getattr(request, "client_version", None) if request else None
        }
        await auth_repo.log_audit(f"{role}_profile_completed", audit_data)
        log_info("Profile completed", extra=audit_data)

        notification_sent = await notification_service.send(
            receiver_id=user_id,
            receiver_type=role,
            template_key="user.profile_completed" if role == "user" else "vendor.profile_pending",
            variables={"name": first_name or business_name, "phone": phone},
            reference_type="profile",
            reference_id=user_id,
            language=language,
            return_bool=True
        )
        if role == "vendor" and updated_user["status"] == "pending":
            await notification_service.send(
                receiver_id="admin",
                receiver_type="admin",
                template_key="admin.vendor_submitted",
                variables={"vendor_name": business_name, "vendor_phone": phone},
                reference_type="profile",
                reference_id=user_id,
                language=language,
                return_bool=False
            )
        elif role == "user" and updated_user["status"] == "active":
            await notification_service.send(
                receiver_id="admin",
                receiver_type="admin",
                template_key="admin.user_joined",
                variables={"user_name": first_name, "user_phone": phone},
                reference_type="profile",
                reference_id=user_id,
                language=language,
                return_bool=False
            )

        response_data = {
            "access_token": access_token,
            "status": updated_user["status"],
            "notification_sent": notification_sent
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
        log_error("Profile completion failed", extra={"error": str(e), "ip": client_ip}, exc_info=True)
        raise InternalServerErrorException(detail=get_message("server.error", language))