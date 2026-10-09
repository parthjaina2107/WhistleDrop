import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "WhistleDrop — Speak Without Being Seen"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    
    # Security & Auth
    SECRET_KEY: str = "whistledrop-gdg-2026-super-secret-key-change-in-prod"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Database
    DATABASE_URL: str = "sqlite:///./whistledrop.db"
    
    # Default Moderator Credentials (seeded on startup)
    DEFAULT_ADMIN_USERNAME: str = "moderator"
    DEFAULT_ADMIN_PASSWORD: str = "WhistleDrop@2026"
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    # AI / ML Thresholds
    CONFIDENCE_AUTO_CLASSIFY_THRESHOLD: float = 0.80
    CONFIDENCE_REVIEW_THRESHOLD: float = 0.50
    SIMILARITY_THRESHOLD_HIGH: float = 0.85
    SIMILARITY_THRESHOLD_MODERATE: float = 0.70

    model_config = SettingsConfigDict(env_file=".env", extra="allow")

settings = Settings()
