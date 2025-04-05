# File: main.py
from contextlib import asynccontextmanager
import subprocess
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, PlainTextResponse

from application.router.all_endpoints import all_routers
from common.exceptions.exception_handlers import register_exception_handlers
from common.logging.logger import log_info, log_error
from infrastructure.database.mongodb.connection import MongoDBConnection
from infrastructure.database.mongodb.repository import MongoRepository
from infrastructure.database.redis.redis_client import init_redis_pool, close_redis_pool
from infrastructure.setup.initial_setup import setup_admin_and_categories

load_dotenv()

# Function to run Celery worker in a separate thread
def run_celery_worker():
    try:
        log_info("Starting Celery worker")
        process = subprocess.Popen(
            ["celery", "-A", "celery_config.celery_app", "worker", "--loglevel=info"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        log_info("Celery worker started successfully", extra={"pid": process.pid})
        for line in process.stdout:
            log_info("Celery worker output", extra={"output": line.strip()})
        for line in process.stderr:
            log_error("Celery worker error", extra={"error": line.strip()})
    except Exception as e:
        log_error("Failed to start Celery worker", extra={"error": str(e)})

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

        # # Start Celery worker in a separate thread
        # celery_thread = Thread(target=run_celery_worker, daemon=True)
        # celery_thread.start()

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
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

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