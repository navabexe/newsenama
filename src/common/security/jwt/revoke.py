from infrastructure.database.redis.redis_client import setex, delete, keys
from common.logging.logger import log_info, log_error
from common.config.settings import settings
from .errors import JWTError

def revoke_token(jti: str, ttl: int):
    try:
        setex(f"blacklist:{jti}", ttl, "revoked")
        log_info("Token revoked", extra={"jti": jti, "ttl": ttl})
    except Exception as e:
        log_error("Token revocation failed", extra={"jti": jti, "error": str(e)})
        raise JWTError(f"Failed to revoke token: {str(e)}")

def revoke_all_user_tokens(user_id: str):
    try:
        refresh_keys = keys(f"refresh_tokens:{user_id}:*")
        for key in refresh_keys:
            jti = key.split(":")[-1]
            delete(key)
            setex(f"blacklist:{jti}", settings.REFRESH_TTL, "revoked")
            log_info("Refresh token revoked", extra={"user_id": user_id, "jti": jti})
        session_keys = keys(f"sessions:{user_id}:*")
        for key in session_keys:
            delete(key)
            log_info("Session removed", extra={"user_id": user_id, "key": key})
    except Exception as e:
        log_error("Revoke all tokens failed", extra={"user_id": user_id, "error": str(e)})
        raise JWTError(f"Failed to revoke all tokens: {str(e)}")
