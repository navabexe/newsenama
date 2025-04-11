# File: main.py

from contextlib import asynccontextmanager

import sentry_sdk
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sentry_sdk.integrations.fastapi import FastApiIntegration

from api.routers.all_endpoints import all_routers
from common.config.settings import settings
from common.exceptions.exception_handlers import register_exception_handlers
from common.logging.logger import log_info, log_error
from api.middleware.error_middleware import ErrorLoggingMiddleware
from infrastructure.database.mongodb.connection import MongoDBConnection
from infrastructure.database.mongodb.repository import MongoRepository
from infrastructure.database.redis.redis_client import init_redis_pool, close_redis_pool
from infrastructure.setup.initial_setup import setup_admin_and_categories

# Load environment variables
load_dotenv()

# Initialize Sentry
sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    integrations=[FastApiIntegration()],
    traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
    environment=settings.ENVIRONMENT,
    send_default_pii=settings.SENTRY_SEND_PII
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    try:
        await MongoDBConnection.connect()
        db = MongoDBConnection.get_db()

        admins_repo = MongoRepository(db, "admins")
        categories_repo = MongoRepository(db, "business_categories")
        await setup_admin_and_categories(admins_repo, categories_repo)

        await init_redis_pool()

        log_info("Registered routes", extra={"routes": [route.path for route in app.routes]})
        log_info("Senama API started", extra={"version": app.version})
    except Exception as e:
        log_error("Startup failed", extra={"error": str(e)})
        sentry_sdk.capture_exception(e)
        raise

    yield  # Application is running

    # Shutdown tasks
    await MongoDBConnection.disconnect()
    await close_redis_pool()
    log_info("Senama API stopped")

# Create FastAPI app instance
app = FastAPI(
    title="Senama Marketplace API",
    version="1.0.0",
    description="Modular, scalable backend built with FastAPI.",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Request logger middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    log_info("Incoming request", extra={"method": request.method, "url": str(request.url)})
    return await call_next(request)

# Register middlewares
app.add_middleware(ErrorLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exception handlers
register_exception_handlers(app)

# Register routers
try:
    log_info("Attempting to include all_routers", extra={"router": str(all_routers)})
    app.include_router(all_routers)
    log_info("Successfully included all_routers")
except Exception as e:
    log_error("Failed to include all_routers", extra={"error": str(e)})
    sentry_sdk.capture_exception(e)
    raise
