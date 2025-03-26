# application/users/controllers/profile/set_username.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from common.security.auth import get_current_user
from domain.users.user_services.username_service.validate import is_valid_username
from domain.users.user_services.username_service.check_unique import check_username_unique
from domain.users.user_services.username_service.reserve import check_reserved_username
from domain.users.user_services.username_service.update import update_username
from common.logging.logger import log_info
from infrastructure.database.mongodb.repository import MongoRepository
from infrastructure.database.mongodb.mongo_client import get_mongo_collection

router = APIRouter()

class SetUsernameRequest(BaseModel):
    username: str = Field(..., json_schema_extra={"example": "mihaanwood"})

class SetUsernameResponse(BaseModel):
    message: str = Field(..., json_schema_extra={"example": "Username has been set successfully."})

@router.post(
    "/profile/set-username",
    response_model=SetUsernameResponse,
    tags=["Profile"],
    summary="Set Username",
    description="Set a unique and permanent username (only once) for current user or vendor",
)
async def set_username(
    payload: SetUsernameRequest,
    current_user: dict = Depends(get_current_user),
    users_repo: MongoRepository = Depends(get_mongo_collection("users")),
    vendors_repo: MongoRepository = Depends(get_mongo_collection("vendors"))
):
    user_id = current_user["sub"]
    role = current_user["role"]
    username = payload.username.strip().lower()

    if not is_valid_username(username):
        raise HTTPException(status_code=400, detail="Invalid username format.")

    check_reserved_username(username)
    await check_username_unique(username, users_repo=users_repo, vendors_repo=vendors_repo)
    await update_username(user_id=user_id, role=role, username=username, users_repo=users_repo, vendors_repo=vendors_repo)

    log_info("Username set successfully", extra={"user_id": user_id, "username": username})

    return SetUsernameResponse(message="Username has been set successfully.")