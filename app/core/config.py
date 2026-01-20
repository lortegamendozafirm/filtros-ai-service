"""Application configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "FILTROS AI Service"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # GCP Configuration
    PROJECT_ID: str
    LOCATION: str = "us-central1"
    VERTEX_ENDPOINT_ID: str
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None
    
    # External Services
    APPS_SCRIPT_URL: str
    M2GDW_URL: str
    TARGET_FOLDER_ID: str
    
    # Security
    API_KEY: str
    
    # Optional Features
    FIRESTORE_ENABLED: bool = False
    FIRESTORE_COLLECTION: str = "process_logs"
    
    # Processing
    MAX_PDF_PAGES: int = 50
    MAX_TEXT_LENGTH: int = 300000
    AI_TEMPERATURE: float = 0.1
    AI_MAX_OUTPUT_TOKENS: int = 300000
    AI_MAX_RETRIES: int = 3
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
