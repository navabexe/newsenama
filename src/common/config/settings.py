# common/config/settings.py
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).parent.parent.parent.parent
env_path = BASE_DIR / ".env"


print("Trying to load .env from:", env_path)
load_dotenv(dotenv_path=env_path)

class Settings(BaseSettings):
    SECRET_KEY: str
    ACCESS_SECRET: str
    REFRESH_SECRET: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"
    TEMP_TOKEN_TTL: int = 300
    ACCESS_TTL: int = 900
    REFRESH_TTL: int = 86400
    MONGO_URI: str
    MONGO_DB: str
    MONGO_TIMEOUT: int = 5000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()