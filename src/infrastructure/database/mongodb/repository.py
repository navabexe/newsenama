from typing import Any, Dict, List, Optional, Tuple
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from common.logging.logger import log_info, log_error


class MongoDBError(Exception):
    """Custom exception for MongoDB operations."""
    pass


class MongoRepository:
    def __init__(self, db: AsyncIOMotorDatabase, collection_name: str):
        """
        Initialize MongoRepository with a database and collection.

        Args:
            db (AsyncIOMotorDatabase): MongoDB database instance.
            collection_name (str): Name of the collection to operate on.
        """
        self.db = db
        self.collection = db[collection_name]

    @staticmethod
    def _convert_to_objectid(value: Any) -> ObjectId:
        """
        Convert a string to ObjectId if valid.

        Args:
            value (Any): Value to convert.

        Returns:
            ObjectId: Converted ObjectId or original value if not convertible.
        """
        if isinstance(value, str) and ObjectId.is_valid(value):
            return ObjectId(value)
        return value

    async def insert_one(self, document: Dict[str, Any]) -> str:
        """
        Insert a single document into the collection.

        Args:
            document (Dict[str, Any]): Document to insert.

        Returns:
            str: ID of the inserted document.

        Raises:
            MongoDBError: If insertion fails.
        """
        try:
            if "_id" in document and isinstance(document["_id"], str):
                document["_id"] = self._convert_to_objectid(document["_id"])
            result = await self.collection.insert_one(document)
            inserted_id = str(result.inserted_id)
            log_info("Mongo insert_one", extra={"collection": self.collection.name, "id": inserted_id})
            return inserted_id
        except Exception as e:
            log_error("Mongo insert_one failed", extra={"collection": self.collection.name, "error": str(e)})
            raise MongoDBError(f"Failed to insert document: {str(e)}")

    async def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Find a single document matching the query.

        Args:
            query (Dict[str, Any]): Query to match.

        Returns:
            Optional[Dict[str, Any]]: Found document or None.

        Raises:
            MongoDBError: If query fails.
        """
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
            raise MongoDBError(f"Failed to find document: {str(e)}")

    async def update_one(self, query: Dict[str, Any], update: Dict[str, Any]) -> int:
        """
        Update a single document matching the query.

        Args:
            query (Dict[str, Any]): Query to match.
            update (Dict[str, Any]): Update data.

        Returns:
            int: Number of modified documents (0 or 1).

        Raises:
            MongoDBError: If update fails.
        """
        try:
            if "_id" in query:
                query["_id"] = self._convert_to_objectid(query["_id"])
            result = await self.collection.update_one(query, {"$set": update})
            log_info("Mongo update_one", extra={
                "collection": self.collection.name,
                "query": str(query),
                "modified": result.modified_count
            })
            return result.modified_count
        except Exception as e:
            log_error("Mongo update_one failed", extra={"collection": self.collection.name, "error": str(e)})
            raise MongoDBError(f"Failed to update document: {str(e)}")

    async def find(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Find all documents matching the query.

        Args:
            query (Dict[str, Any]): Query to match.

        Returns:
            List[Dict[str, Any]]: List of matching documents.

        Raises:
            MongoDBError: If query fails.
        """
        try:
            if "_id" in query:
                query["_id"] = self._convert_to_objectid(query["_id"])
            cursor = self.collection.find(query)
            result = await cursor.to_list(length=None)
            for doc in result:
                doc["_id"] = str(doc["_id"])
            log_info("Mongo find", extra={
                "collection": self.collection.name,
                "query": str(query),
                "count": len(result)
            })
            return result
        except Exception as e:
            log_error("Mongo find failed", extra={"collection": self.collection.name, "error": str(e)})
            raise MongoDBError(f"Failed to find documents: {str(e)}")

    async def find_with_pagination(
        self,
        query: Dict[str, Any],
        skip: int = 0,
        limit: int = 10,
        sort: Optional[List[Tuple[str, int]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find documents with pagination and optional sorting.

        Args:
            query (Dict[str, Any]): Query to match.
            skip (int): Number of documents to skip (default: 0).
            limit (int): Maximum number of documents to return (default: 10).
            sort (Optional[List[Tuple[str, int]]]): Sort criteria (field, direction).

        Returns:
            List[Dict[str, Any]]: List of matching documents.

        Raises:
            MongoDBError: If query fails.
        """
        try:
            if "_id" in query:
                query["_id"] = self._convert_to_objectid(query["_id"])
            cursor = self.collection.find(query).skip(skip).limit(limit)
            if sort:
                cursor = cursor.sort(sort)
            result = await cursor.to_list(length=limit)
            for doc in result:
                doc["_id"] = str(doc["_id"])
            log_info("Mongo find_with_pagination", extra={
                "collection": self.collection.name,
                "query": str(query),
                "skip": skip,
                "limit": limit,
                "sort": sort,
                "count": len(result)
            })
            return result
        except Exception as e:
            log_error("Mongo find_with_pagination failed", extra={"collection": self.collection.name, "error": str(e)})
            raise MongoDBError(f"Failed to find documents with pagination: {str(e)}")

    async def delete_one(self, query: Dict[str, Any]) -> int:
        """
        Delete a single document matching the query.

        Args:
            query (Dict[str, Any]): Query to match.

        Returns:
            int: Number of deleted documents (0 or 1).

        Raises:
            MongoDBError: If deletion fails.
        """
        try:
            if "_id" in query:
                query["_id"] = self._convert_to_objectid(query["_id"])
            result = await self.collection.delete_one(query)
            log_info("Mongo delete_one", extra={
                "collection": self.collection.name,
                "query": str(query),
                "deleted": result.deleted_count
            })
            return result.deleted_count
        except Exception as e:
            log_error("Mongo delete_one failed", extra={"collection": self.collection.name, "error": str(e)})
            raise MongoDBError(f"Failed to delete document: {str(e)}")