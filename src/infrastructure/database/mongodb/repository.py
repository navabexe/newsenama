# infrastructure/database/mongodb/repository.py
from typing import Any, Dict, List, Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from common.logging.logger import log_info, log_error

class MongoRepository:
    def __init__(self, db: AsyncIOMotorDatabase, collection_name: str):
        self.db = db
        self.collection = db[collection_name]

    def _convert_to_objectid(self, value: Any) -> ObjectId:
        if isinstance(value, str) and ObjectId.is_valid(value):
            return ObjectId(value)
        return value

    async def insert_one(self, document: Dict[str, Any]) -> str:
        try:
            if "_id" in document and isinstance(document["_id"], str):
                document["_id"] = self._convert_to_objectid(document["_id"])
            result = await self.collection.insert_one(document)
            log_info("Mongo insert_one", extra={"collection": self.collection.name, "id": str(result.inserted_id)})
            return str(result.inserted_id)
        except Exception as e:
            log_error("Mongo insert_one failed", extra={"collection": self.collection.name, "error": str(e)})
            raise

    async def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            if "_id" in query:
                query["_id"] = self._convert_to_objectid(query["_id"])
            result = await self.collection.find_one(query)
            if result:
                result["_id"] = str(result["_id"])
            log_info("Mongo find_one", extra={"collection": self.collection.name, "query": str(query), "found": bool(result)})
            return result
        except Exception as e:
            log_error("Mongo find_one failed", extra={"collection": self.collection.name, "error": str(e)})
            raise

    async def update_one(self, query: Dict[str, Any], update: Dict[str, Any]) -> int:
        try:
            if "_id" in query:
                query["_id"] = self._convert_to_objectid(query["_id"])
            result = await self.collection.update_one(query, {"$set": update})
            log_info("Mongo update_one", extra={"collection": self.collection.name, "query": str(query), "modified": result.modified_count})
            return result.modified_count
        except Exception as e:
            log_error("Mongo update_one failed", extra={"collection": self.collection.name, "error": str(e)})
            raise

    async def find(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        try:
            if "_id" in query:
                query["_id"] = self._convert_to_objectid(query["_id"])
            cursor = self.collection.find(query)
            result = await cursor.to_list(length=None)
            for doc in result:
                doc["_id"] = str(doc["_id"])
            log_info("Mongo find", extra={"collection": self.collection.name, "query": str(query), "count": len(result)})
            return result
        except Exception as e:
            log_error("Mongo find failed", extra={"collection": self.collection.name, "error": str(e)})
            raise

    async def delete_one(self, query: Dict[str, Any]) -> int:
        try:
            if "_id" in query:
                query["_id"] = self._convert_to_objectid(query["_id"])
            result = await self.collection.delete_one(query)
            log_info("Mongo delete_one", extra={"collection": self.collection.name, "query": str(query), "deleted": result.deleted_count})
            return result.deleted_count
        except Exception as e:
            log_error("Mongo delete_one failed", extra={"collection": self.collection.name, "error": str(e)})
            raise