# File: domain/access_control/entities/role_entity.py

from typing import List, Optional

from bson import ObjectId
from pydantic import BaseModel, Field


class Role(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    name: str
    permissions: List[str] = []
    description: Optional[str] = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_schema_extra = {
            "example": {
                "_id": "60d0fe4f5311236168a109ca",
                "name": "admin",
                "permissions": ["read:products", "write:products"],
                "description": "Administrator with full access"
            }
        }
