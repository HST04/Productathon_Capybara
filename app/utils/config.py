"""Configuration management for the HPCL Lead Intelligence Agent."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = "postgresql://hpcl_user:hpcl_password@localhost:5432/hpcl_leads"
    
    # Pinecone
    pinecone_api_key: str
    pinecone_environment: str = "us-west1-gcp"
    pinecone_index_name: str = "hpcl-companies"
    
    # Gemini
    gemini_api_key: Optional[str] = None
    
    # WhatsApp
    whatsapp_api_url: str = "https://graph.facebook.com/v18.0"
    whatsapp_access_token: Optional[str] = None
    whatsapp_phone_number_id: Optional[str] = None
    
    # Application
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    frontend_url: str = "http://localhost:3000"
    
    # Worker
    worker_poll_interval_seconds: int = 10
    signal_processing_timeout_minutes: int = 2
    
    # Embedding
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    company_similarity_threshold: float = 0.85
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"  # Ignore extra fields from .env
    )


# Global settings instance
settings = Settings()
