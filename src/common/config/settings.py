# File: common/config/settings.py

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings

# Calculate base directory for consistent file paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
ENV_PATH = BASE_DIR / ".env"
ENVIRONMENT: str = "development"  # "production" or "development"


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"

    BASE_DIR: Path = Field(default=BASE_DIR, description="Base directory of the project")

    # Security keys
    SECRET_KEY: str = Field(..., description="Primary secret key for signing")
    ACCESS_SECRET: str = Field(..., description="Secret for access tokens")
    REFRESH_SECRET: str = Field(..., description="Secret for refresh tokens")
    SMS_PANEL_KEY: str = Field(..., description="API key for SMS provider")

    # Token expiration & algorithms
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    ALGORITHM: str
    TEMP_TOKEN_TTL: int
    ACCESS_TTL: int
    REFRESH_TTL: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    TEMP_TOKEN_EXPIRE_MINUTES: int

    # MongoDB
    MONGO_URI: str
    MONGO_DB: str
    MONGO_TIMEOUT: int

    # SMS
    MOCK_SMS: bool

    # Admin credentials
    ADMIN_USERNAME: str
    ADMIN_PASSWORD: str

    # Redis
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int
    REDIS_SSL_CA_CERTS: str
    REDIS_SSL_CERT: str
    REDIS_SSL_KEY: str
    REDIS_USE_SSL: str

    # SSL
    SSL_CERT_FILE: str
    SSL_KEY_FILE: str

    class Config:
        env_file = ENV_PATH
        env_file_encoding = "utf-8"
        case_sensitive = True


# Singleton settings instance
settings = Settings()