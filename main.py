# main.py
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, PlainTextResponse
from starlette.responses import JSONResponse

from application.router.all_endpoints import all_routers

from common.logging.logger import log_info, log_error
from infrastructure.database.mongodb.connection import MongoDBConnection
from infrastructure.database.mongodb.repository import MongoRepository
from infrastructure.database.redis.redis_client import init_redis_pool, close_redis_pool
from infrastructure.setup.initial_setup import setup_admin_and_categories

load_dotenv()


# Lifespan handler for startup and shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Initialize MongoDB
        await MongoDBConnection.connect()
        db = MongoDBConnection.get_db()
        admins_repo = MongoRepository(db, "admins")
        categories_repo = MongoRepository(db, "business_categories")
        await setup_admin_and_categories(admins_repo, categories_repo)

        # Initialize Redis
        await init_redis_pool()

        log_info("Senama API started", extra={"version": "1.0.0"})
    except Exception as e:
        log_error("Startup failed", extra={"error": str(e)})
        raise
    yield
    # Cleanup on shutdown
    await MongoDBConnection.disconnect()
    await close_redis_pool()
    log_info("Senama API stopped")


app = FastAPI(
    title="Senama Marketplace API",
    version="1.0.0",
    description="Modular, scalable backend built with FastAPI.",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware (restrict origins in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Example for dev, update for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log_error("Unhandled exception", extra={
        "path": request.url.path,
        "method": request.method,
        "error": str(exc)
    })
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Include API routers
app.include_router(all_routers)


# Root endpoint redirecting to docs
@app.get("/", response_class=RedirectResponse)
async def root():
    return RedirectResponse(url="/docs")


# Favicon endpoint (empty response)
@app.get("/favicon.ico", response_class=PlainTextResponse)
async def favicon():
    return ""


# Health check endpoint
@app.get("/health", status_code=200)
async def health_check():
    from datetime import datetime, timezone
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}