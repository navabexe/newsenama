# File: common/config/settings.py
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings

# Calculate base directory for consistent file paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
ENV_PATH = BASE_DIR / ".env"
ENVIRONMENT: str = "development"  # "production" or "development"

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"  # "production" or "development"

    # Add BASE_DIR as a field
    BASE_DIR: Path = Field(default=BASE_DIR, description="Base directory of the project")

    # Security keys (required from .env)
    SECRET_KEY: str
    ACCESS_SECRET: str
    REFRESH_SECRET: str
    SMS_PANEL_KEY: str

    # Token expiration settings (required from .env)
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    ALGORITHM: str
    TEMP_TOKEN_TTL: int
    ACCESS_TTL: int
    REFRESH_TTL: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    TEMP_TOKEN_EXPIRE_MINUTES: int

    # MongoDB settings (required from .env)
    MONGO_URI: str
    MONGO_DB: str
    MONGO_TIMEOUT: int

    # SMS settings (required from .env)
    MOCK_SMS: bool

    # Admin credentials (required from .env)
    ADMIN_USERNAME: str
    ADMIN_PASSWORD: str

    # Redis settings (required from .env)
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int
    REDIS_SSL_CA_CERTS: str
    REDIS_SSL_CERT: str
    REDIS_SSL_KEY: str
    REDIS_USE_SSL: str

    # HTTPS settings (required from .env)
    SSL_CERT_FILE: str
    SSL_KEY_FILE: str

    class Config:
        # Load environment variables from .env file
        env_file = ENV_PATH
        env_file_encoding = "utf-8"
        case_sensitive = True

# Instantiate settings object
settings = Settings()