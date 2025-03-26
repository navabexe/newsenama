# File: main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, PlainTextResponse
from starlette.responses import JSONResponse
from contextlib import asynccontextmanager
from common.logging.logger import log_info, log_error
from dotenv import load_dotenv
from infrastructure.setup.initial_setup import setup_admin_and_categories
from infrastructure.database.mongodb.connection import MongoDBConnection
from infrastructure.database.mongodb.repository import MongoRepository

# === Import Routers ===
from application.auth.controllers.auth_controller import router as auth_router
from application.users.controllers.profile.set_username import router as username_router
from application.access_control.controllers.access_control import router as access_control_router

load_dotenv()

# === Lifespan Handler ===
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    await MongoDBConnection.connect()  # اتصال به MongoDB
    db = MongoDBConnection.get_db()
    admins_repo = MongoRepository(db, "admins")
    categories_repo = MongoRepository(db, "business_categories")
    await setup_admin_and_categories(admins_repo, categories_repo)  # پاس دادن رپوزیتوری‌ها
    log_info("Senama API started", extra={"version": "1.0.0"})
    yield
    # Shutdown logic
    await MongoDBConnection.disconnect()  # بستن اتصال
    log_info("Senama API stopped")

app = FastAPI(
    title="Senama Marketplace API",
    version="1.0.0",
    description="Modular, scalable backend built with FastAPI.",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# === CORS (for frontend dev) ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restrict this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Global Exception Handler ===
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

# === Include Routers ===
app.include_router(auth_router)
app.include_router(access_control_router)
app.include_router(username_router, prefix="/profile")

# === Root Endpoint ===
@app.get("/", response_class=RedirectResponse)
async def root():
    return RedirectResponse(url="/docs")

# === Favicon Endpoint ===
@app.get("/favicon.ico", response_class=PlainTextResponse)
async def favicon():
    return ""

# === Health Check Endpoint ===
@app.get("/health", status_code=200)
async def health_check():
    from datetime import datetime, timezone  # Local import to avoid circular issues
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}