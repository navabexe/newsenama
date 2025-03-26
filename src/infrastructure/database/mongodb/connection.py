# infrastructure/database/mongodb/connection.py
import os
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from fastapi import Depends
from common.logging.logger import log_info, log_error
from common.config.settings import Settings

settings = Settings()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB", "senama_db")
MONGO_TIMEOUT = int(os.getenv("MONGO_TIMEOUT", 5000))  # ms

class MongoDBConnection:
    _client: AsyncIOMotorClient = None
    _db: AsyncIOMotorDatabase = None

    @classmethod
    async def connect(cls):
        if cls._client is None:
            try:
                cls._client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=MONGO_TIMEOUT)
                cls._db = cls._client[MONGO_DB]
                await cls._client.admin.command("ping")
                log_info("MongoDB async connection established", extra={"uri": MONGO_URI})
            except Exception as e:
                log_error("MongoDB async connection failed", extra={"error": str(e)})
                raise RuntimeError(f"Failed to connect to MongoDB: {str(e)}")

    @classmethod
    async def disconnect(cls):
        if cls._client is not None:
            cls._client.close()
            log_info("MongoDB connection closed")

    @classmethod
    def get_db(cls) -> AsyncIOMotorDatabase:
        if cls._db is None:
            raise RuntimeError("MongoDB not connected. Call connect() first.")
        return cls._db

# Dependency
async def get_mongo_db() -> AsyncIOMotorDatabase:
    await MongoDBConnection.connect()
    return MongoDBConnection.get_db()

# Startup و Shutdown  FastAPI
async def startup_db():
    await MongoDBConnection.connect()

async def shutdown_db():
    await MongoDBConnection.disconnect()