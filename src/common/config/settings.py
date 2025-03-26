from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from pathlib import Path
import os

# Load .env from project root
load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env")

class Settings(BaseSettings):
    SECRET_KEY: str
    ACCESS_SECRET: str
    REFRESH_SECRET: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"
    TEMP_TOKEN_TTL: int = 300  # 5 minutes
    ACCESS_TTL: int = 900      # 15 mins
    REFRESH_TTL: int = 86400   # 1 day

    class Config:
        env_file = ".env"
        case_sensitive = True

# Fallback fix for env name mismatches
settings = Settings(
    ACCESS_SECRET=os.getenv("ACCESS_SECRET", os.getenv("SECRET_KEY", "")),
    REFRESH_SECRET=os.getenv("REFRESH_SECRET", os.getenv("REFRESH_SECRET_KEY", "")),
)
