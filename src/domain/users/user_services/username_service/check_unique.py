from fastapi import HTTPException
from infrastructure.database.mongodb.mongo_client import db

from common.logging.logger import log_info


async def check_username_unique(username: str):
    username_lower = username.lower()

    users = db["users"]
    vendors = db["vendors"]

    user_match = users.find_one({"username": {"$regex": f"^{username_lower}$", "$options": "i"}})
    if user_match:
        log_info("Username already taken (user)", extra={"username": username})
        raise HTTPException(status_code=409, detail="Username already taken.")

    vendor_match = vendors.find_one({"username": {"$regex": f"^{username_lower}$", "$options": "i"}})
    if vendor_match:
        log_info("Username already taken (vendor)", extra={"username": username})
        raise HTTPException(status_code=409, detail="Username already taken.")

    return True
