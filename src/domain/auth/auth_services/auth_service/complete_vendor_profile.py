from uuid import uuid4

from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from common.security.jwt_handler import decode_token, generate_access_token, generate_refresh_token
from common.security.permissions_loader import get_scopes_for_role
from infrastructure.database.redis.redis_client import get, delete, hset
from infrastructure.database.mongodb.mongo_client import find_one, update_one, find, insert_one
from common.logging.logger import log_info, log_error
from datetime import datetime, timezone
from typing import Optional, List
from bson import ObjectId

# Pydantic v2 Models
class Location(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)

# Validation Functions

async def validate_business_categories(category_ids: List[str]) -> None:
    try:
        query_ids = [ObjectId(cid) if ObjectId.is_valid(cid) else cid for cid in category_ids]
        existing_categories = {str(doc["_id"]) for doc in find("business_categories", {"_id": {"$in": query_ids}})}
        invalid_ids = set(category_ids) - existing_categories
        if invalid_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid business category IDs: {', '.join(invalid_ids)}"
            )
    except Exception as e:
        log_error("Business category validation failed", extra={"category_ids": category_ids, "error": str(e)})
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to validate categories")

# Notification Function

async def notify_admin_of_pending_vendor(vendor_id: str, phone: str, business_name: str, client_ip: str):
    try:
        notification = {
            "receiver_type": "admin",
            "receiver_id": "admin_group",
            "title": "New Vendor Registration",
            "body": f"Vendor {business_name} ({phone}) registered and awaiting approval.",
            "channel": "inapp",
            "reference_type": "vendor",
            "reference_id": vendor_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        insert_one("notifications", notification)
        log_info("Admin notified of pending vendor", extra={"vendor_id": vendor_id, "ip": client_ip})
    except Exception as e:
        log_error("Failed to notify admin", extra={"vendor_id": vendor_id, "error": str(e)})
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to notify admin")

# Main Service

async def complete_vendor_profile_service(
    temporary_token: str,
    business_name: Optional[str] = None,
    owner_name: Optional[str] = None,
    city: Optional[str] = None,
    province: Optional[str] = None,
    location: Optional[Location] = None,
    address: Optional[str] = None,
    business_category_ids: Optional[List[str]] = None,
    client_ip: str = "unknown"
) -> dict:
    try:
        # Decode temporary token
        payload = decode_token(temporary_token, "temp")
        phone = payload["sub"]
        role = payload["role"]
        jti = payload["jti"]
        token_key = f"temp_token:{jti}"

        # Verify token and role
        if get(token_key) != phone:
            log_error("Invalid temporary token", extra={"phone": phone, "jti": jti, "ip": client_ip})
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid temporary token")
        if role != "vendor":
            log_error("Role mismatch", extra={"phone": phone, "role": role, "ip": client_ip})
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Endpoint restricted to vendors")

        # Check vendor in MongoDB
        vendor = find_one("vendors", {"phone": phone})
        if not vendor or vendor["status"] not in ["incomplete", "pending"]:
            log_error("Vendor not found or not eligible", extra={"phone": phone, "ip": client_ip})
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profile not eligible")

        vendor_id = str(vendor["_id"])

        # Validate business_category_ids if provided
        if business_category_ids:
            await validate_business_categories(business_category_ids)

        # Prepare update data
        update_data = {"updated_at": datetime.now(timezone.utc)}
        if business_name is not None:
            update_data["business_name"] = business_name.strip() if business_name else None
        if owner_name is not None:
            update_data["owner_name"] = owner_name.strip() if owner_name else None
        if city is not None:
            update_data["city"] = city.strip() if city else None
        if province is not None:
            update_data["province"] = province.strip() if province else None
        if location is not None:
            update_data["location"] = {"lat": location.lat, "lng": location.lng}
        if address is not None:
            update_data["address"] = address.strip() if address else None
        if business_category_ids is not None:
            update_data["business_category_ids"] = business_category_ids

        # Update vendor in MongoDB
        modified_count = update_one("vendors", {"_id": ObjectId(vendor_id)}, update_data)
        if modified_count == 0:
            log_error("Vendor update failed", extra={"vendor_id": vendor_id, "ip": client_ip})
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update profile")

        # Fetch updated vendor
        updated_vendor = find_one("vendors", {"_id": ObjectId(vendor_id)})
        if not updated_vendor:
            log_error("Failed to retrieve updated vendor", extra={"vendor_id": vendor_id, "ip": client_ip})
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch updated profile")

        # Check completeness
        required_fields = ["business_name", "owner_name", "city", "province", "location", "address", "business_category_ids"]
        is_complete = all(updated_vendor.get(field) is not None for field in required_fields)

        # Set status and tokens
        if is_complete and updated_vendor["status"] == "incomplete":
            update_one("vendors", {"_id": ObjectId(vendor_id)}, {"status": "pending"})
            await notify_admin_of_pending_vendor(...)
            message = "Vendor profile registered successfully and is pending admin review"

            session_id = str(uuid4())
            vendor_status = updated_vendor["status"]
            access_token = generate_access_token(
                user_id=vendor_id,
                role=role,
                session_id=session_id,
                scopes=get_scopes_for_role(role, vendor_status)
            )
            refresh_token = None

            delete(token_key)

        else:
            message = "Profile updated successfully. Please complete all required fields."
            access_token = temporary_token
            refresh_token = None

        # Log success
        log_info("Vendor profile updated", extra={
            "vendor_id": vendor_id,
            "phone": phone,
            "updated_fields": list(update_data.keys()),
            "is_complete": is_complete,
            "ip": client_ip,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "status": "pending" if is_complete else "incomplete",
            "message": message
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        log_error("Vendor profile completion failed", extra={
            "phone": phone if "phone" in locals() else "unknown",
            "error": str(e),
            "ip": client_ip
        })
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to complete vendor profile")