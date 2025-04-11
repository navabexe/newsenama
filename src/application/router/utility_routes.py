# File: application/router/utility_routes.py

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse, PlainTextResponse
from datetime import datetime, timezone

router = APIRouter()


@router.get("/", response_class=RedirectResponse)
async def root():
    return RedirectResponse(url="/docs")


@router.get("/favicon.ico", response_class=PlainTextResponse)
async def favicon():
    return ""


@router.get("/health", status_code=200)
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/sentry-debug")
async def trigger_error():
    1 / 0
    return {"message": "This won't happen"}

