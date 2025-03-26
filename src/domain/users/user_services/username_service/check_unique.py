# domain/users/user_services/username_service/check_unique.py
from fastapi import HTTPException, Depends
from infrastructure.database.mongodb.mongo_client import get_mongo_collection
from infrastructure.database.mongodb.repository import MongoRepository
from common.logging.logger import log_info

async def check_username_unique(
    username: str,
    users_repo: MongoRepository = Depends(get_mongo_collection("users")),
    vendors_repo: MongoRepository = Depends(get_mongo_collection("vendors"))
) -> bool:
    username_lower = username.lower()

    user_match = await users_repo.find_one({"username": {"$regex": f"^{username_lower}$", "$options": "i"}})
    if user_match:
        log_info("Username already taken (user)", extra={"username": username})
        raise HTTPException(status_code=409, detail="Username already taken.")

    vendor_match = await vendors_repo.find_one({"username": {"$regex": f"^{username_lower}$", "$options": "i"}})
    if vendor_match:
        log_info("Username already taken (vendor)", extra={"username": username})
        raise HTTPException(status_code=409, detail="Username already taken.")

    return True