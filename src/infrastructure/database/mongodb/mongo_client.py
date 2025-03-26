from fastapi import Depends
from typing import Callable
from motor.motor_asyncio import AsyncIOMotorDatabase
from .connection import get_mongo_db
from .repository import MongoRepository

def get_mongo_collection(collection_name: str) -> Callable[[], MongoRepository]:
    def _get_repo(db: AsyncIOMotorDatabase = Depends(get_mongo_db)) -> MongoRepository:
        return MongoRepository(db, collection_name)
    return _get_repo

async def insert_one(collection: str, document: dict) -> str:
    db: AsyncIOMotorDatabase = await get_mongo_db()
    repo = MongoRepository(db, collection)
    return await repo.insert_one(document)

async def find_one(collection: str, query: dict) -> dict | None:
    db: AsyncIOMotorDatabase = await get_mongo_db()
    repo = MongoRepository(db, collection)
    return await repo.find_one(query)

async def update_one(collection: str, query: dict, update: dict) -> int:
    db: AsyncIOMotorDatabase = await get_mongo_db()
    repo = MongoRepository(db, collection)
    return await repo.update_one(query, update)

async def find(collection: str, query: dict) -> list:
    db: AsyncIOMotorDatabase = await get_mongo_db()
    repo = MongoRepository(db, collection)
    return await repo.find(query)

async def delete_one(collection: str, query: dict) -> int:
    db: AsyncIOMotorDatabase = await get_mongo_db()
    repo = MongoRepository(db, collection)
    return await repo.delete_one(query)
