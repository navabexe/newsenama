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
    OTP_SALT: str = Field(..., description="Salt value used for hashing OTP codes")

    # Token expiration & algorithms
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(60, description="Access token expiry in minutes")
    ALGORITHM: str = Field("HS256", description="JWT signing algorithm")
    TEMP_TOKEN_TTL: int = Field(300, description="Temporary token TTL in seconds")
    ACCESS_TTL: int = Field(900, description="Access token TTL in seconds")
    REFRESH_TTL: int = Field(86400, description="Refresh token TTL in seconds")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(30, description="Refresh token expiry in days")
    TEMP_TOKEN_EXPIRE_MINUTES: int = Field(300, description="Temporary token expiry in minutes")
    OTP_EXPIRY: int = Field(300, description="OTP expiry time in seconds")
    BLOCK_DURATION: int = Field(3600, description="General block duration in seconds")
    MAX_OTP_ATTEMPTS: int = Field(5, description="Maximum OTP attempts allowed")
    BLOCK_DURATION_OTP: int = Field(600, description="OTP block duration in seconds")

    # MongoDB
    MONGO_URI: str = Field("mongodb://localhost:27017", description="MongoDB connection URI")
    MONGO_DB: str = Field("senama_db", description="MongoDB database name")
    MONGO_TIMEOUT: int = Field(5000, description="MongoDB connection timeout in milliseconds")

    # SMS
    MOCK_SMS: bool = Field(True, description="Mock SMS sending for testing")

    # Admin credentials
    ADMIN_USERNAME: str = Field(..., description="Admin username")
    ADMIN_PASSWORD: str = Field(..., description="Admin password")

    # Redis
    REDIS_HOST: str = Field("localhost", description="Redis host")
    REDIS_PORT: int = Field(6379, description="Redis port")
    REDIS_DB: int = Field(0, description="Redis database number")
    REDIS_SSL_CA_CERTS: str = Field("", description="Path to Redis SSL CA certificate")
    REDIS_SSL_CERT: str = Field("", description="Path to Redis SSL certificate")
    REDIS_SSL_KEY: str = Field("", description="Path to Redis SSL key")
    REDIS_USE_SSL: bool = Field(False, description="Use SSL for Redis connection")

    # SSL
    SSL_CERT_FILE: str = Field("", description="Path to HTTPS certificate file")
    SSL_KEY_FILE: str = Field("", description="Path to HTTPS key file")

    # IP info
    IPINFO_TOKEN: str = Field(..., description="API token for ipinfo.io to fetch geolocation data")

    class Config:
        env_file = ENV_PATH
        env_file_encoding = "utf-8"
        case_sensitive = True

# Singleton settings instance
settings = Settings()