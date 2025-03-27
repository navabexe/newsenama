from datetime import datetime, timezone
from uuid import uuid4
from typing import Optional, List

from fastapi import HTTPException
from redis.asyncio import Redis
from bson import ObjectId

from common.security.jwt.tokens import generate_access_token, generate_refresh_token
from common.security.jwt.decode import decode_token
from common.translations.messages import get_message
from infrastructure.database.redis.redis_client import get_redis_client
from infrastructure.database.redis.operations.delete import delete
from infrastructure.database.redis.operations.hset import hset
from infrastructure.database.mongodb.mongo_client import find_one, update_one, find
from common.logging.logger import log_error


async def validate_business_categories(category_ids: List[str]) -> None:
    query_ids = [ObjectId(cid) if ObjectId.is_valid(cid) else cid for cid in category_ids]
    existing = await find("business_categories", {"_id": {"$in": query_ids}})
    existing_ids = {str(doc["_id"]) for doc in existing}
    invalid_ids = set(category_ids) - existing_ids
    if invalid_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid business category IDs: {', '.join(invalid_ids)}"
        )


async def complete_profile_service(
    temporary_token: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    email: Optional[str] = None,
    business_name: Optional[str] = None,
    owner_name: Optional[str] = None,
    city: Optional[str] = None,
    province: Optional[str] = None,
    location: Optional[dict] = None,
    address: Optional[str] = None,
    business_category_ids: Optional[List[str]] = None,
    client_ip: str = "unknown",
    language: str = "fa",
    redis: Redis = None
) -> dict:
    try:
        if redis is None:
            redis = await get_redis_client()

        payload = await decode_token(temporary_token, token_type="temp", redis=redis)
        phone = payload.get("sub")
        role = payload.get("role")
        jti = payload.get("jti")

        if not phone or role not in ["user", "vendor"]:
            raise HTTPException(status_code=401, detail=get_message("token.invalid", language))

        temp_key = f"temp_token:{jti}"
        if await redis.get(temp_key) != phone:
            raise HTTPException(status_code=401, detail=get_message("otp.expired", language))

        collection = f"{role}s"
        user = await find_one(collection, {"phone": phone})
        if not user or user.get("status") not in ["incomplete", "pending"]:
            raise HTTPException(status_code=400, detail=get_message("vendor.not_eligible", language))

        user_id = str(user["_id"])
        update_data = {"updated_at": datetime.now(timezone.utc)}

        if role == "user":
            if not all([first_name, last_name, email]):
                raise HTTPException(status_code=400, detail="Missing user profile fields")
            update_data.update({
                "first_name": str(first_name).strip(),
                "last_name": str(last_name).strip(),
                "email": str(email).strip().lower(),
                "status": "active"
            })

        if role == "vendor":
            if business_category_ids:
                await validate_business_categories(business_category_ids)
            if business_name is not None:
                update_data["business_name"] = business_name.strip()
            if owner_name is not None:
                update_data["owner_name"] = owner_name.strip()
            if city is not None:
                update_data["city"] = city.strip()
            if province is not None:
                update_data["province"] = province.strip()
            if location is not None:
                update_data["location"] = location
            if address is not None:
                update_data["address"] = address.strip()
            if business_category_ids is not None:
                update_data["business_category_ids"] = business_category_ids

        updated_count = await update_one(collection, {"_id": ObjectId(user_id)}, update_data)
        if not updated_count:
            raise HTTPException(status_code=500, detail="Failed to update profile")

        updated_user = await find_one(collection, {"_id": ObjectId(user_id)})

        status = updated_user.get("status")
        if role == "vendor":
            required_fields = [
                "business_name", "owner_name", "city", "province",
                "location", "address", "business_category_ids"
            ]
            if all(updated_user.get(field) for field in required_fields) and status == "incomplete":
                await update_one(collection, {"_id": ObjectId(user_id)}, {"status": "pending"})
                status = "pending"

        await delete(temp_key, redis)
        session_id = str(uuid4())

        user_profile = {
            "first_name": str(updated_user.get("first_name") or updated_user.get("owner_name")) if (updated_user.get("first_name") or updated_user.get("owner_name")) else None,
            "last_name": str(updated_user.get("last_name")) if updated_user.get("last_name") else None,
            "email": str(updated_user.get("email")) if updated_user.get("email") else None,
            "phone": str(updated_user.get("phone")) if updated_user.get("phone") else None,
            "business_name": str(updated_user.get("business_name")) if updated_user.get("business_name") else None,
            "location": updated_user.get("location"),
            "address": str(updated_user.get("address")) if updated_user.get("address") else None,
            "status": status,
            "business_category_ids": updated_user.get("business_category_ids", []),
            "profile_picture": str(updated_user.get("profile_picture")) if updated_user.get("profile_picture") else None
        }

        access_token = await generate_access_token(
            user_id=user_id,
            role=role,
            session_id=session_id,
            user_profile=user_profile,
            language=language,
            redis=redis
        )

        result = {
            "access_token": access_token,
            "refresh_token": None,
            "status": status,
            "message": get_message("auth.profile.pending" if status == "pending" else "auth.profile.completed", language)
        }

        if role == "user" and status == "active":
            refresh_token = await generate_refresh_token(
                user_id=user_id,
                role=role,
                session_id=session_id,
                redis=redis
            )
            await hset(f"sessions:{user_id}:{session_id}", mapping={
                "ip": client_ip,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "device": "unknown",
                "status": "active",
                "jti": session_id
            }, redis=redis)
            result["refresh_token"] = refresh_token

        return result

    except HTTPException:
        raise
    except Exception as e:
        log_error("Profile completion failed", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(status_code=500, detail=get_message("server.error", language))
