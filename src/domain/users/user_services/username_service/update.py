from fastapi import HTTPException
from infrastructure.database.mongodb.mongo_client import db
from datetime import datetime, UTC

async def update_username(user_id: str, role: str, username: str):
    username = username.lower()

    if role == "user":
        collection = db["users"]
    elif role == "vendor":
        collection = db["vendors"]
    else:
        raise HTTPException(status_code=403, detail="Invalid role for username update.")

    existing = collection.find_one({"id": user_id})
    if not existing:
        raise HTTPException(status_code=404, detail="User not found.")

    if existing.get("username"):
        raise HTTPException(status_code=400, detail="Username already set and cannot be changed.")

    result = collection.update_one(
        {"id": user_id},
        {
            "$set": {
                "username": username,
                "updated_at": datetime.now(UTC).isoformat()
            }
        }
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=500, detail="Username update failed.")

    return True
