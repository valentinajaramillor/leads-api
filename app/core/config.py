from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Leads API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/leads_db"

    # Security
    SECRET_KEY: str = "changeme-use-a-strong-secret-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # API Key (alternative auth)
    API_KEY: Optional[str] = None

    # AI — Anthropic
    ANTHROPIC_API_KEY: Optional[str] = None
    AI_MOCK_MODE: bool = True  # Set to False when a real API key is provided

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()