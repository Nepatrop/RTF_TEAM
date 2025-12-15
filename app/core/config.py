import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    PROJECT_NAME: str = "Business Requirements AI Agent"
    DATABASE_URL: str = os.getenv("", "DATABASE_URL")
    ALGORITHM: str = os.getenv("", "ALGORITHM")
    SECRET_KEY: str = os.getenv("", "SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = os.getenv("", "ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_MINUTES: int = os.getenv("", "REFRESH_TOKEN_EXPIRE_MINUTES")
    BACKEND_CORS_ORIGINS: str = os.getenv("", "BACKEND_CORS_ORIGINS")
    EXTERNAL_API_URL: str = os.getenv("", "EXTERNAL_API_URL")
    CALLBACK_URL: str = os.getenv("", "СALLBACK_URL")


class LocalSettings(Settings):
    RELOAD: bool = True


settings_name = {"local": LocalSettings(), "production": Settings()}
settings = settings_name[os.getenv("APP_ENV") or "local"]
