from fastapi import Request, HTTPException, status
from common.logging.logger import log_error, log_info
from infrastructure.database.mongodb.mongo_client import find_one
from .decode import decode_token

def get_token_from_header(request: Request) -> str:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header missing or invalid")
    return auth_header.split(" ")[1]

async def get_current_user(request: Request) -> dict:
    token = get_token_from_header(request)
    try:
        payload = decode_token(token, "access")
        user_id = payload.get("sub")
        role = payload.get("role")
        session_id = payload.get("session_id")
        if not all([user_id, role, session_id]):
            log_error("Invalid token payload", extra={"payload": payload})
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

        collection = "admins" if role == "admin" else "vendors" if role == "vendor" else "users"
        user = find_one(collection, {"_id": user_id})
        if not user:
            log_error("User not found for token", extra={"user_id": user_id, "role": role})
            raise HTTPException(status_code=401, detail=f"No {role} found with ID: {user_id}")

        log_info("User authenticated", extra={"user_id": user_id, "role": role})
        return {"user_id": user_id, "role": role, "session_id": session_id}
    except HTTPException as e:
        raise e
    except Exception as e:
        log_error("User authentication failed", extra={"token": token[:10], "error": str(e)})
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
