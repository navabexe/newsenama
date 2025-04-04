# File: common/dependencies/cache_dep.py

from fastapi import HTTPException, status
from infrastructure.database import redis
from common.logging.logger import log_error

def check_redis():
    if redis is None:
        log_error("Redis dependency check failed", extra={"service": "redis"})
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis service is unavailable."
        )
