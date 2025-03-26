# common/config/settings.py
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from pathlib import Path
import os


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
    TEMP_TOKEN_TTL: int = 300  # 5 minutes
    ACCESS_TTL: int = 900      # 15 mins
    REFRESH_TTL: int = 86400   # 1 day

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

# برای دیباگ
print("SECRET_KEY:", os.getenv("SECRET_KEY"))
print("ACCESS_SECRET:", os.getenv("ACCESS_SECRET"))
print("REFRESH_SECRET:", os.getenv("REFRESH_SECRET"))

settings = Settings()