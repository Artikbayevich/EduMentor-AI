from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # App
    PROJECT_NAME: str = "EduMentor AI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    SECRET_KEY: str = "changeme"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "sezgi_user"
    POSTGRES_PASSWORD: str = "sezgi_password"
    POSTGRES_DB: str = "sezgi_db"
    DATABASE_URL: str = (
        "postgresql+asyncpg://sezgi_user:sezgi_password@localhost:5432/sezgi_db"
    )

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # Email
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAILS_FROM_EMAIL: str = "noreply@edumentor.ai"
    EMAILS_FROM_NAME: str = "EduMentor AI Platform"

    # AI
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    CHROMA_PERSIST_DIR: str = "./chroma_db"

    # HEMIS OAuth
    HEMIS_CLIENT_ID: str = ""
    HEMIS_CLIENT_SECRET: str = ""
    HEMIS_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/hemis/callback"
    USE_HEMIS_MOCK: bool = False

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"


settings = Settings()
