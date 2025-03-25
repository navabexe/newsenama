from infrastructure.database.mongodb.mongo_client import find_one, insert_one
from common.logging.logger import log_info
from datetime import datetime, timezone
from dotenv import load_dotenv
import os
from common.security.password import hash_password

load_dotenv()


async def setup_admin_and_categories():
    # Load admin credentials from environment variables with defaults
    admin_username = os.getenv("ADMIN_USERNAME")
    admin_password = os.getenv("ADMIN_PASSWORD")

    # Validate environment variables
    if not admin_password:
        raise ValueError("ADMIN_PASSWORD must be set in .env for security in production")
    if len(admin_password) < 8:
        raise ValueError("ADMIN_PASSWORD must be at least 8 characters long")

    # Hash password with bcrypt
    hashed_password = hash_password(admin_password)

    # Check if admin exists and create if not
    admin = find_one("admins", {"username": admin_username})
    if not admin:
        admin_data = {
            "username": admin_username,
            "password": hashed_password,
            "role": "admin",
            "status": "active",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        admin_id = insert_one("admins", admin_data)
        log_info("Admin user created", extra={"admin_id": str(admin_id)})

    # Setup default business categories
    default_categories = [
        {"name": "Furniture", "description": "Furniture and home decor", "created_at": datetime.now(timezone.utc)},
        {"name": "Electronics", "description": "Electronic gadgets and appliances",
         "created_at": datetime.now(timezone.utc)},
        {"name": "Clothing", "description": "Clothing and fashion items", "created_at": datetime.now(timezone.utc)}
    ]
    for category in default_categories:
        if not find_one("business_categories", {"name": category["name"]}):
            category_id = insert_one("business_categories", category)
            log_info("Business category created", extra={"category_id": str(category_id)})