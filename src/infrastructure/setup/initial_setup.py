# File: infrastructure/setup/initial_setup.py

from infrastructure.database.mongodb.mongo_client import find_one, insert_one
from common.logging.logger import log_info
from datetime import datetime, timezone
import hashlib

async def setup_admin_and_categories():
    """Setup admin user and default business categories on startup."""
    # Setup admin
    admin_username = "navabexe"  # Updated from logs
    admin_password = "Exe@1835"  # Change this in production!
    hashed_password = hashlib.sha256(admin_password.encode()).hexdigest()
    admin = find_one("admins", {"username": admin_username})
    if not admin:
        admin_id = insert_one("admins", {
            "username": admin_username,
            "password": hashed_password,
            "role": "admin",
            "status": "active",
            "created_at": datetime.now(timezone.utc)
        })
        log_info("Admin user created", extra={"admin_id": admin_id})

    # Setup default business categories (let MongoDB generate _id)
    default_categories = [
        {"name": "Furniture", "description": "Furniture and home decor"},
        {"name": "Electronics", "description": "Electronic gadgets and appliances"},
        {"name": "Clothing", "description": "Clothing and fashion items"}
    ]
    for category in default_categories:
        if not find_one("business_categories", {"name": category["name"]}):  # Check by name
            category_id = insert_one("business_categories", category)  # MongoDB generates _id
            log_info("Business category created", extra={"category_id": str(category_id)})