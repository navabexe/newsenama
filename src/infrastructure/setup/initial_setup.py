# infrastructure/setup/initial_setup.py
from datetime import datetime, timezone

from common.config.settings import settings
from common.logging.logger import log_info
from common.security.password import hash_password
from infrastructure.database.mongodb.repository import MongoRepository


async def setup_admin_and_categories(admins_repo: MongoRepository, categories_repo: MongoRepository):
    # Fetch admin credentials from settings
    admin_username = settings.ADMIN_USERNAME
    admin_password = settings.ADMIN_PASSWORD

    # Validate admin credentials
    if not admin_username:
        raise ValueError("ADMIN_USERNAME must be set in .env")
    if not admin_password:
        raise ValueError("ADMIN_PASSWORD must be set in .env for security in production")
    if len(admin_password) < 8:
        raise ValueError("ADMIN_PASSWORD must be at least 8 characters long")

    hashed_password = hash_password(admin_password)

    # Check if admin exists, create if not
    admin = await admins_repo.find_one({"username": admin_username})
    if not admin:
        admin_data = {
            "username": admin_username,
            "password": hashed_password,
            "role": "admin",
            "status": "active",
            "created_at": datetime.now(timezone.utc),
            "updated_at": None  # Only set on updates
        }
        admin_id = await admins_repo.insert_one(admin_data)
        log_info("Admin user created", extra={"admin_id": str(admin_id)})

    # Default business categories
    default_categories = [
        {"name": "Furniture", "description": "Furniture and home decor", "created_at": datetime.now(timezone.utc)},
        {"name": "Electronics", "description": "Electronic gadgets and appliances", "created_at": datetime.now(timezone.utc)},
        {"name": "Clothing", "description": "Clothing and fashion items", "created_at": datetime.now(timezone.utc)}
    ]

    # Insert categories if they don't exist
    for category in default_categories:
        if not await categories_repo.find_one({"name": category["name"]}):
            category_id = await categories_repo.insert_one(category)
            log_info("Business category created", extra={"category_id": str(category_id)})