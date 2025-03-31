# File: domain/auth/auth_services/auth_service/complete_profile.py
from datetime import datetime, timezone
from uuid import uuid4
from typing import Optional, List

from fastapi import HTTPException
from redis.asyncio import Redis
from bson import ObjectId

from common.security.jwt.tokens import generate_access_token, generate_refresh_token
from common.security.jwt.decode import decode_token
from common.translations.messages import get_message
from domain.auth.entities.token_entity import VendorJWTProfile, UserJWTProfile
from infrastructure.database.redis.redis_client import get_redis_client
from infrastructure.database.redis.operations.delete import delete
from infrastructure.database.redis.operations.hset import hset
from infrastructure.database.redis.operations.expire import expire
from infrastructure.database.redis.operations.scan import scan_keys
from infrastructure.database.mongodb.mongo_client import find_one, update_one, find
from common.logging.logger import log_error

async def validate_business_categories(category_ids: List[str]) -> None:
    """Validate that provided business category IDs exist in the database."""
    query_ids = [ObjectId(cid) if ObjectId.is_valid(cid) else cid for cid in category_ids]
    existing = await find("business_categories", {"_id": {"$in": query_ids}})
    existing_ids = {str(doc["_id"]) for doc in existing}
    invalid_ids = set(category_ids) - existing_ids
    if invalid_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid business category IDs: {', '.join(invalid_ids)}"
        )

def normalize_vendor_data(data: dict) -> dict:
    """Normalize vendor data by setting default values for optional fields."""
    return {
        **data,
        "logo_urls": data.get("logo_urls") or [],
        "banner_urls": data.get("banner_urls") or [],
        "preferred_languages": data.get("preferred_languages") or [],
        "account_types": data.get("account_types") or [],
        "show_followers_publicly": data.get("show_followers_publicly", True),
    }

async def delete_all_sessions(user_id: str, redis: Redis):
    """Delete all existing sessions for a user from Redis."""
    session_keys = await scan_keys(redis, f"sessions:{user_id}:*")
    for key in session_keys:
        await redis.delete(key)

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
    client_ip: str = "unknown",
    language: str = "fa",
    redis: Redis = None,
) -> dict:
    """
    Complete a user or vendor profile using a temporary token.

    Args:
        temporary_token (str): Temporary token from OTP verification.
        first_name (Optional[str]): User's or vendor's first name.
        last_name (Optional[str]): User's or vendor's last name.
        email (Optional[str]): User's email address.
        business_name (Optional[str]): Vendor's business name.
        city (Optional[str]): City name.
        province (Optional[str]): Province name.
        location (Optional[dict]): Geographical coordinates.
        address (Optional[str]): Full address.
        business_category_ids (Optional[List[str]]): List of business category IDs.
        visibility (Optional[str]): Vendor profile visibility status.
        vendor_type (Optional[str]): Type of vendor.
        languages (Optional[List[str]]): Preferred languages for the profile.
        client_ip (str): Client IP address.
        language (str): Language for response messages.
        redis (Redis): Redis client instance.

    Returns:
        dict: Contains access token, refresh token (if applicable), status, and message.
    """
    try:
        redis = redis or await get_redis_client()
        payload = await decode_token(temporary_token, token_type="temp", redis=redis)

        phone = payload.get("sub")
        role = payload.get("role")
        jti = payload.get("jti")

        if not phone or role not in ["user", "vendor"]:
            raise HTTPException(status_code=401, detail=get_message("token.invalid", language))

        temp_key = f"temp_token:{jti}"
        if await redis.get(temp_key) != phone:
            raise HTTPException(status_code=401, detail=get_message("otp.expired", language))

        is_vendor_data = any([
            bool(business_name), bool(business_category_ids), bool(city), bool(province),
            bool(location), bool(address), bool(vendor_type),
            bool(visibility and visibility != "COLLABORATIVE")
        ])

        if role == "user" and is_vendor_data:
            raise HTTPException(status_code=403, detail=get_message("access.denied", language))

        if role == "vendor" and not business_name:
            raise HTTPException(status_code=400, detail=get_message("vendor.not_eligible", language))

        collection = f"{role}s"
        user = await find_one(collection, {"phone": phone})
        if not user or user.get("status") not in ["incomplete", "pending"]:
            msg_key = "user.not_eligible" if role == "user" else "vendor.not_eligible"
            raise HTTPException(status_code=400, detail=get_message(msg_key, language))

        user_id = str(user["_id"])
        update_data = {"updated_at": datetime.now(timezone.utc)}

        if role == "user":
            if not all([first_name, last_name]):
                raise HTTPException(status_code=400, detail="Missing user profile fields")
            update_data.update({
                "first_name": first_name.strip(),
                "last_name": last_name.strip(),
                "status": "active",
                "preferred_languages": languages or [],
            })
            if email:
                update_data["email"] = email.strip().lower()

        if role == "vendor":
            if isinstance(first_name, str):
                update_data["first_name"] = first_name.strip()
            if isinstance(last_name, str):
                update_data["last_name"] = last_name.strip()
            if business_category_ids:
                await validate_business_categories(business_category_ids)
            if isinstance(business_name, str):
                update_data["business_name"] = business_name.strip()
            if isinstance(city, str):
                update_data["city"] = city.strip()
            if isinstance(province, str):
                update_data["province"] = province.strip()
            if location is not None:
                update_data["location"] = location
            if isinstance(address, str):
                update_data["address"] = address.strip()
            if business_category_ids is not None:
                update_data["business_category_ids"] = business_category_ids
            if isinstance(visibility, str):
                update_data["visibility"] = visibility
            if isinstance(vendor_type, str):
                update_data["vendor_type"] = vendor_type
            update_data["preferred_languages"] = languages or []

        updated_count = await update_one(collection, {"_id": ObjectId(user_id)}, update_data)
        if not updated_count:
            raise HTTPException(status_code=500, detail="Failed to update profile")

        updated_user = await find_one(collection, {"_id": ObjectId(user_id)})
        status = updated_user.get("status")

        if role == "vendor":
            required_fields = ["business_name", "city", "province", "location", "address", "business_category_ids"]
            if all(updated_user.get(field) for field in required_fields) and status == "incomplete":
                await update_one(collection, {"_id": ObjectId(user_id)}, {"status": "pending"})
                status = "pending"

        await delete(temp_key, redis)
        await delete_all_sessions(user_id, redis)

        session_id = str(uuid4())

        if role == "vendor":
            updated_user = normalize_vendor_data(updated_user)

        profile_model = UserJWTProfile if role == "user" else VendorJWTProfile
        profile_data = profile_model(**updated_user).model_dump()

        token_language = (languages[0] if languages else language) if languages else language

        access_token = await generate_access_token(
            user_id=user_id,
            role=role,
            session_id=session_id,
            user_profile=profile_data if role == "user" else None,
            vendor_profile=profile_data if role == "vendor" else None,
            language=token_language,
            vendor_id=user_id if role == "vendor" else None,
        )

        result = {
            "access_token": access_token,
            "refresh_token": None,
            "status": status,
            "message": get_message("auth.profile.pending" if status == "pending" else "auth.profile.completed", language),
        }

        if role == "user" and status == "active":
            refresh_token = await generate_refresh_token(
                user_id=user_id,
                role=role,
                session_id=session_id,
            )

            session_key = f"sessions:{user_id}:{session_id}"
            key_type = await redis.type(session_key)
            if key_type not in [b"hash", b"none"]:
                await redis.delete(session_key)

            await hset(
                session_key,
                mapping={
                    "ip": client_ip,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "device": "unknown",
                    "status": "active",
                    "jti": session_id,
                },
                redis=redis,
            )
            await expire(session_key, 86400, redis=redis)

            result["refresh_token"] = refresh_token

        return result

    except HTTPException:
        raise
    except Exception as e:
        log_error("Profile completion failed", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(status_code=500, detail=get_message("server.error", language))