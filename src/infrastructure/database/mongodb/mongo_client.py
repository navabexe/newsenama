import os
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from bson import ObjectId
from common.logging.logger import log_info, log_error

# Environment variables
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB", "senama_db")
MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
MONGO_PORT = int(os.getenv("MONGO_PORT", 27017))
MONGO_USERNAME = os.getenv("MONGO_USERNAME")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
MONGO_TIMEOUT = int(os.getenv("MONGO_TIMEOUT", 5000))  # ms

# Fallback URI construction
if not MONGO_URI:
    auth_part = f"{MONGO_USERNAME}:{MONGO_PASSWORD}@" if MONGO_USERNAME and MONGO_PASSWORD else ""
    MONGO_URI = f"mongodb://{auth_part}{MONGO_HOST}:{MONGO_PORT}"
    log_info("Mongo URI built from parts", extra={"uri": MONGO_URI})

# MongoDB connection
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=MONGO_TIMEOUT)
    db = client[MONGO_DB]
    client.admin.command("ping")
    log_info("MongoDB connection established", extra={"uri": MONGO_URI})
except PyMongoError as e:
    log_error("MongoDB connection failed", extra={"error": str(e)})
    raise RuntimeError(f"Failed to connect to MongoDB: {str(e)}")

class MongoClientError(Exception):
    pass

def _convert_to_objectid(value: str | ObjectId) -> ObjectId:
    if isinstance(value, str) and ObjectId.is_valid(value):
        return ObjectId(value)
    return value

def insert_one(collection: str, document: dict) -> str:
    try:
        if "_id" in document and isinstance(document["_id"], str):
            document["_id"] = _convert_to_objectid(document["_id"])
        result = db[collection].insert_one(document)
        log_info("Mongo insert_one", extra={"collection": collection, "id": str(result.inserted_id)})
        return str(result.inserted_id)
    except PyMongoError as e:
        log_error("Mongo insert_one failed", extra={"collection": collection, "error": str(e)})
        raise MongoClientError(f"Failed to insert into {collection}: {str(e)}")

def find_one(collection: str, query: dict) -> dict | None:
    try:
        if "_id" in query:
            query["_id"] = _convert_to_objectid(query["_id"])
        result = db[collection].find_one(query)
        if result:
            result["_id"] = str(result["_id"])
        log_info("Mongo find_one", extra={"collection": collection, "query": str(query), "found": bool(result)})
        return result
    except PyMongoError as e:
        log_error("Mongo find_one failed", extra={"collection": collection, "error": str(e)})
        raise MongoClientError(f"Failed to find in {collection}: {str(e)}")

def update_one(collection: str, query: dict, update: dict) -> int:
    try:
        if "_id" in query:
            query["_id"] = _convert_to_objectid(query["_id"])
        result = db[collection].update_one(query, {"$set": update})
        log_info("Mongo update_one", extra={"collection": collection, "query": str(query), "modified": result.modified_count})
        return result.modified_count
    except PyMongoError as e:
        log_error("Mongo update_one failed", extra={"collection": collection, "error": str(e)})
        raise MongoClientError(f"Failed to update in {collection}: {str(e)}")

def find(collection: str, query: dict) -> list:
    try:
        if "_id" in query:
            query["_id"] = _convert_to_objectid(query["_id"])
        result = list(db[collection].find(query))
        for doc in result:
            doc["_id"] = str(doc["_id"])
        log_info("Mongo find", extra={"collection": collection, "query": str(query), "count": len(result)})
        return result
    except PyMongoError as e:
        log_error("Mongo find failed", extra={"collection": collection, "error": str(e)})
        raise MongoClientError(f"Failed to find multiple in {collection}: {str(e)}")

def delete_one(collection: str, query: dict) -> int:
    try:
        if "_id" in query:
            query["_id"] = _convert_to_objectid(query["_id"])
        result = db[collection].delete_one(query)
        log_info("Mongo delete_one", extra={"collection": collection, "query": str(query), "deleted": result.deleted_count})
        return result.deleted_count
    except PyMongoError as e:
        log_error("Mongo delete_one failed", extra={"collection": collection, "error": str(e)})
        raise MongoClientError(f"Failed to delete in {collection}: {str(e)}")

def with_transaction(operations: list, collection: str):
    with client.start_session() as session:
        with session.start_transaction():
            try:
                for op in operations:
                    op(db[collection])
                log_info("Transaction completed", extra={"collection": collection})
            except PyMongoError as e:
                log_error("Transaction failed", extra={"collection": collection, "error": str(e)})
                session.abort_transaction()
                raise MongoClientError(f"Transaction failed in {collection}: {str(e)}")