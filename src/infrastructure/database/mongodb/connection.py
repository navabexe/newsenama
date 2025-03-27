from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from common.config.settings import settings
from common.logging.logger import log_info, log_error


class MongoDBConnection:
    _client: AsyncIOMotorClient = None
    _db: AsyncIOMotorDatabase = None

    @classmethod
    async def connect(cls):
        # Only connect if not already connected
        if cls._client is None:
            try:
                # Ensure MONGO_URI is valid, fallback to localhost for dev if empty
                mongo_uri = settings.MONGO_URI or "mongodb://localhost:27017"
                timeout = getattr(settings, "MONGO_TIMEOUT", 20000)  # Default timeout 20s

                cls._client = AsyncIOMotorClient(
                    mongo_uri,
                    serverSelectionTimeoutMS=timeout
                )
                cls._db = cls._client[settings.MONGO_DB]
                await cls._client.admin.command("ping")
                log_info("MongoDB async connection established", extra={"uri": mongo_uri})
            except Exception as e:
                log_error("MongoDB async connection failed", extra={"error": str(e)})
                raise RuntimeError(f"Failed to connect to MongoDB: {str(e)}")

    @classmethod
    async def disconnect(cls):
        # Close connection if it exists
        if cls._client is not None:
            cls._client.close()
            cls._client = None
            cls._db = None
            log_info("MongoDB connection closed")

    @classmethod
    def get_db(cls) -> AsyncIOMotorDatabase:
        # Return DB instance or raise error if not connected
        if cls._db is None:
            raise RuntimeError("MongoDB not connected. Call connect() first.")
        return cls._db


# Dependency for FastAPI injection
async def get_mongo_db() -> AsyncIOMotorDatabase:
    # Ensure connection is established before returning DB
    if MongoDBConnection._client is None:
        await MongoDBConnection.connect()
    return MongoDBConnection.get_db()


# Startup & Shutdown hooks
async def startup_db():
    await MongoDBConnection.connect()


async def shutdown_db():
    await MongoDBConnection.disconnect()