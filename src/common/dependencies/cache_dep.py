from fastapi import HTTPException

from infrastructure.database import redis


def check_redis():
    if redis is None:
        raise HTTPException(
            status_code=503,
            detail="Redis service is unavailable."
        )
