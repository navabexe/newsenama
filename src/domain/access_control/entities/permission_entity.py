# File: domain/access_control/entities/permission_entity.py

from typing import Optional

from bson import ObjectId
from pydantic import BaseModel, Field


class Permission(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    name: str
    description: Optional[str] = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_schema_extra = {
            "example": {
                "_id": "60d0fe4f5311236168a109cb",
                "name": "read:products",
                "description": "Allows reading product data"
            }
        }
