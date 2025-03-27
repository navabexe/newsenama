from datetime import datetime, timezone

from fastapi import HTTPException, status
from redis.asyncio import Redis

from common.logging.logger import log_info, log_error
from common.translations.messages import get_message
from common.security.jwt_handler import revoke_all_user_tokens
from infrastructure.database.mongodb.mongo_client import update_one


async def request_account_deletion_service(
    user_id: str,
    role: str,
    client_ip: str,
    language: str = "fa",
    redis: Redis = None
) -> dict:
    """
    Handles logic for marking a user account for deletion and revoking all sessions/tokens.
    """
    try:
        if redis is None:
            from infrastructure.database.redis.redis_client import get_redis_client
            redis = await get_redis_client()

        collection = f"{role}s"
        update_data = {
            "status": "pending_deletion",
            "deletion_requested_at": datetime.now(timezone.utc)
        }

        updated = await update_one(collection, {"_id": user_id}, update_data)
        if not updated:
            raise HTTPException(status_code=404, detail=get_message("user.not_found", language))

        await revoke_all_user_tokens(user_id, redis)

        log_info("Account deletion requested", extra={
            "user_id": user_id,
            "role": role,
            "ip": client_ip,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return {
            "message": get_message("account.deletion.requested", language),
            "status": "pending_deletion"
        }

    except HTTPException:
        raise
    except Exception as e:
        log_error("Account deletion request failed", extra={
            "user_id": user_id,
            "role": role,
            "ip": client_ip,
            "error": str(e)
        }, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_message("server.error", language)
        )
