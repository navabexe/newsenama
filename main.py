# File: main.py
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, PlainTextResponse
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

from application.router.all_endpoints import all_routers
from common.config.settings import settings
from common.csrf_service import CSRFService, get_csrf_service
from common.exceptions.exception_handlers import register_exception_handlers
from common.middleware.csrf_middleware import CSRFMiddleware
from common.middleware.error_middleware import ErrorLoggingMiddleware  # ✅ به صورت کلاس
from common.logging.logger import log_info, log_error
from infrastructure.database.mongodb.connection import MongoDBConnection
from infrastructure.database.mongodb.repository import MongoRepository
from infrastructure.database.redis.redis_client import init_redis_pool, close_redis_pool
from infrastructure.setup.initial_setup import setup_admin_and_categories

load_dotenv()

sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    integrations=[FastApiIntegration()],
    traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
    environment=settings.ENVIRONMENT,
    send_default_pii=settings.SENTRY_SEND_PII
)

@asynccontextmanager
async def lifespan(app: FastAPI):
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

    yield

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

# ✅ Logging request method/url (can remain function-based)
@app.middleware("http")
async def log_requests(request: Request, call_next):
    log_info("Incoming request", extra={"method": request.method, "url": str(request.url)})
    return await call_next(request)

# ✅ CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
from common.middleware.error_middleware import ErrorLoggingMiddleware
from common.middleware.csrf_middleware import CSRFMiddleware

app.add_middleware(ErrorLoggingMiddleware)
app.add_middleware(CSRFMiddleware)
register_exception_handlers(app)

# ✅ Routes
try:
    log_info("Attempting to include all_routers", extra={"router": str(all_routers)})
    app.include_router(all_routers)
    log_info("Successfully included all_routers")
except Exception as e:
    log_error("Failed to include all_routers", extra={"error": str(e)})
    sentry_sdk.capture_exception(e)
    raise

# ✅ Utility Endpoints
@app.get("/", response_class=RedirectResponse)
async def root():
    return RedirectResponse(url="/docs")

@app.get("/favicon.ico", response_class=PlainTextResponse)
async def favicon():
    return ""

@app.get("/health", status_code=200)
async def health_check():
    from datetime import datetime, timezone
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.get("/sentry-debug")
async def trigger_error():
    division_by_zero = 1 / 0
    return {"message": "This won't happen"}

@app.get("/csrf-token")
async def get_csrf_token(csrf_service: CSRFService = Depends(get_csrf_service)):
    user_id = "anonymous"
    token = await csrf_service.generate_csrf_token(user_id)
    return {"csrf_token": token}
