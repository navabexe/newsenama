# domain/users/user_services/username_service/update.py
from fastapi import HTTPException, Depends
from infrastructure.database.mongodb.mongo_client import get_mongo_collection
from infrastructure.database.mongodb.repository import MongoRepository
from datetime import datetime, UTC

async def update_username(
    user_id: str,
    role: str,
    username: str,
    users_repo: MongoRepository = Depends(get_mongo_collection("users")),
    vendors_repo: MongoRepository = Depends(get_mongo_collection("vendors"))
):
    username = username.lower()

    if role == "user":
        collection = users_repo
    elif role == "vendor":
        collection = vendors_repo
    else:
        raise HTTPException(status_code=403, detail="Invalid role for username update.")

    existing = await collection.find_one({"_id": user_id})
    if not existing:
        raise HTTPException(status_code=404, detail="User not found.")

    if existing.get("username"):
        raise HTTPException(status_code=400, detail="Username already set and cannot be changed.")

    result = await collection.update_one(
        {"_id": user_id},
        {
            "$set": {
                "username": username,
                "updated_at": datetime.now(UTC).isoformat()
            }
        }
    )

    if result == 0:
        raise HTTPException(status_code=500, detail="Username update failed.")

    return True