import jwt
from fastapi import HTTPException, status
from common.config.settings import settings
from infrastructure.database.redis.redis_client import get
from .revoke import revoke_all_user_tokens
from common.logging.logger import log_error, log_info
from .errors import JWTError

def decode_token(token: str, token_type: str = "access"):
    secret = settings.ACCESS_SECRET if token_type in ["access", "temp"] else settings.REFRESH_SECRET
    try:
        payload = jwt.decode(token, secret, algorithms=[settings.ALGORITHM])
        jti = payload.get("jti")
        if not jti:
            raise JWTError("Token missing jti")
        if get(f"blacklist:{jti}"):
            log_error("Token revoked", extra={"jti": jti, "type": token_type})
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")
        if token_type == "refresh":
            user_id = payload.get("sub")
            redis_key = f"refresh_tokens:{user_id}:{jti}"
            if not get(redis_key):
                revoke_all_user_tokens(user_id)
                log_error("Refresh token reuse detected", extra={"user_id": user_id, "jti": jti})
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token reuse detected")
        log_info("Token decoded", extra={"jti": jti, "type": token_type})
        return payload
    except jwt.ExpiredSignatureError:
        log_error("Token expired", extra={"token_type": token_type})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError as e:
        log_error("Invalid token", extra={"token_type": token_type, "error": str(e)})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {str(e)}")
