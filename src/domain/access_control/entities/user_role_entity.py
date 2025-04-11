# File: domain/access_control/entities/user_role_entity.py

from bson import ObjectId
from pydantic import BaseModel, Field


class UserRole(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    user_id: str
    role_name: str

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_schema_extra = {
            "example": {
                "_id": "60d0fe4f5311236168a109cc",
                "user_id": "user_12345",
                "role_name": "vendor"
            }
        }
