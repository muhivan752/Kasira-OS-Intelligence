from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List

class Settings(BaseSettings):
    PROJECT_NAME: str = "Kasira POS API"
    API_V1_STR: str = "/api/v1"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "kasira"
    POSTGRES_PORT: str = "5432"
    # Non-superuser role for runtime (RLS enforced). Falls back to POSTGRES_USER if not set.
    POSTGRES_APP_USER: str = ""
    POSTGRES_APP_PASSWORD: str = ""

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        user = self.POSTGRES_APP_USER or self.POSTGRES_USER
        password = self.POSTGRES_APP_PASSWORD or self.POSTGRES_PASSWORD
        return f"postgresql+asyncpg://{user}:{password}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Fonnte WA
    FONNTE_TOKEN: str = ""

    # Xendit Master Keys
    XENDIT_API_KEY: str = ""
    XENDIT_WEBHOOK_TOKEN: str = ""
    XENDIT_IS_PRODUCTION: bool = False

    # JWT Security
    SECRET_KEY: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7" # Change in production
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # Encryption
    ENCRYPTION_KEY: str = ""

    # App Environment
    ENVIRONMENT: str = "development"

    # Superadmin — comma-separated phone numbers
    SUPERADMIN_PHONES: str = ""

    # Claude AI
    ANTHROPIC_API_KEY: str = ""

    # Voyage AI (embeddings for Layer 4)
    VOYAGE_API_KEY: str = ""

    # Sentry Error Tracking
    SENTRY_DSN: str = ""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

settings = Settings()
