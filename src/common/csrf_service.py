# File: src/domain/common/csrf_service.py
from fastapi import Depends
from redis.asyncio import Redis
from common.config.settings import settings
from common.utils.string_utils import generate_random_string
from common.logging.logger import log_info, log_error
from infrastructure.database.redis.redis_client import get_redis_client

class CSRFService:
    def __init__(self, redis: Redis):
        self.redis = redis
        log_info("CSRFService initialized", extra={"redis_host": settings.REDIS_HOST, "redis_port": settings.REDIS_PORT})

    async def generate_csrf_token(self, user_id: str) -> str | None:
        """Generate a CSRF token and store it in Redis."""
        log_info("Generating CSRF token", extra={"user_id": user_id})
        token = generate_random_string(32)
        key = f"csrf:{user_id}:{token}"
        try:
            await self.redis.setex(key, settings.CSRF_TOKEN_EXPIRY, "valid")
            log_info("CSRF token stored in Redis", extra={
                "key": key,
                "token": token,
                "expiry": settings.CSRF_TOKEN_EXPIRY,
                "user_id": user_id
            })
            return token
        except Exception as e:
            log_error("Failed to store CSRF token in Redis", extra={
                "key": key,
                "user_id": user_id,
                "error": str(e)
            })
            return None

    async def validate_csrf_token(self, user_id: str, token: str) -> bool:
        """Validate a CSRF token from Redis."""
        key = f"csrf:{user_id}:{token}"
        log_info("Validating CSRF token", extra={"key": key, "user_id": user_id, "token": token})
        try:
            value = await self.redis.get(key)
            log_info("Retrieved CSRF token value from Redis", extra={"key": key, "value": value})
            if value == "valid" or value == b"valid":
                await self.redis.delete(key)
                log_info("CSRF token validated and removed", extra={"key": key, "user_id": user_id})
                return True
            log_error("CSRF token invalid or not found", extra={"key": key, "user_id": user_id, "value": value})
            return False
        except Exception as e:
            log_error("Failed to validate CSRF token in Redis", extra={
                "key": key,
                "user_id": user_id,
                "token": token,
                "error": str(e)
            })
            return False

def get_csrf_service(redis: Redis = Depends(get_redis_client)):
    return CSRFService(redis)

csrf_service = get_csrf_service()