# Enterprise Configuration Management
# This file contains all environment-specific configuration

import os
from enum import Enum
from typing import Optional, Union
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, model_validator, ValidationInfo


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class Settings(BaseSettings):
    """
    Application settings with environment-based configuration.
    All settings can be overridden via environment variables.
    """
    
    # ==========================================
    # ENVIRONMENT & APP SETTINGS
    # ==========================================
    ENVIRONMENT: Environment = Field(default=Environment.DEVELOPMENT)
    APP_NAME: str = Field(default="Elevare")
    APP_VERSION: str = Field(default="1.0.0")
    DEBUG: bool = Field(default=False)
    
    # ==========================================
    # SERVER CONFIGURATION
    # ==========================================
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    RELOAD: bool = Field(default=False)
    WORKERS: int = Field(default=1)
    
    # ==========================================
    # DATABASE CONFIGURATION
    # ==========================================
    DATABASE_URL: str = Field(default="sqlite:///./elevare.db")
    DATABASE_POOL_SIZE: int = Field(default=5)
    DATABASE_MAX_OVERFLOW: int = Field(default=10)
    DATABASE_POOL_TIMEOUT: int = Field(default=30)
    DATABASE_POOL_RECYCLE: int = Field(default=3600)
    
    # ==========================================
    # REDIS CONFIGURATION
    # ==========================================
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    REDIS_PASSWORD: Optional[str] = Field(default=None)
    REDIS_MAX_CONNECTIONS: int = Field(default=10)
    REDIS_SOCKET_TIMEOUT: int = Field(default=5)
    REDIS_SOCKET_CONNECT_TIMEOUT: int = Field(default=5)
    
    # ==========================================
    # SECURITY & AUTHENTICATION
    # ==========================================
    SECRET_KEY: str = Field(default="CHANGE_THIS_IN_PRODUCTION_USE_SECURE_RANDOM_KEY")
    JWT_SECRET_KEY: str = Field(default="CHANGE_THIS_IN_PRODUCTION_USE_SECURE_RANDOM_KEY")
    JWT_ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)
    
    # Password hashing
    BCRYPT_ROUNDS: int = Field(default=12)
    
    # CORS settings
    CORS_ORIGINS: Union[str, list[str]] = Field(default=["http://localhost:3000", "http://localhost:8000"])
    CORS_CREDENTIALS: bool = Field(default=True)
    CORS_METHODS: list[str] = Field(default=["*"])
    CORS_HEADERS: list[str] = Field(default=["*"])
    
    # ==========================================
    # API KEYS & EXTERNAL SERVICES
    # ==========================================
    # Groq API
    GROQ_API_KEY: str = Field(default="")
    GROQ_MODEL: str = Field(default="llama-3.3-70b-versatile")
    GROQ_MAX_RETRIES: int = Field(default=3)
    GROQ_TIMEOUT: int = Field(default=60)
    
    # GitHub API (for cofounder matching)
    GITHUB_API_TOKEN: Optional[str] = Field(default=None)
    GITHUB_API_URL: str = Field(default="https://api.github.com")
    GITHUB_RATE_LIMIT_PER_HOUR: int = Field(default=5000)
    
    # SERP API (for market analysis)
    SERP_API_KEY: Optional[str] = Field(default=None)
    
    # AngelList/Wellfound API
    ANGELLIST_API_KEY: Optional[str] = Field(default=None)
    
    # Email service (SendGrid/SES/SMTP)
    EMAIL_ENABLED: bool = Field(default=False)
    EMAIL_FROM: str = Field(default="noreply@elevare.com")
    SMTP_HOST: Optional[str] = Field(default=None)
    SMTP_PORT: int = Field(default=587)
    SMTP_USER: Optional[str] = Field(default=None)
    SMTP_PASSWORD: Optional[str] = Field(default=None)
    SENDGRID_API_KEY: Optional[str] = Field(default=None)
    
    # ==========================================
    # RATE LIMITING
    # ==========================================
    RATE_LIMIT_ENABLED: bool = Field(default=True)
    RATE_LIMIT_PER_MINUTE: int = Field(default=60)
    RATE_LIMIT_PER_HOUR: int = Field(default=1000)
    
    # ==========================================
    # CACHING
    # ==========================================
    CACHE_ENABLED: bool = Field(default=True)
    CACHE_TTL_SECONDS: int = Field(default=300)  # 5 minutes default
    CACHE_MAX_SIZE: int = Field(default=1000)
    
    # ==========================================
    # LOGGING
    # ==========================================
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FORMAT: str = Field(default="json")  # json or text
    LOG_FILE: Optional[str] = Field(default=None)
    LOG_ROTATION: str = Field(default="100 MB")
    LOG_RETENTION: str = Field(default="30 days")
    
    # ==========================================
    # MONITORING & OBSERVABILITY
    # ==========================================
    SENTRY_DSN: Optional[str] = Field(default=None)
    SENTRY_ENVIRONMENT: Optional[str] = Field(default=None)
    SENTRY_TRACES_SAMPLE_RATE: float = Field(default=0.1)
    
    # Prometheus metrics
    METRICS_ENABLED: bool = Field(default=True)
    METRICS_PORT: int = Field(default=9090)
    
    # ==========================================
    # FILE STORAGE
    # ==========================================
    UPLOAD_MAX_SIZE_MB: int = Field(default=10)
    UPLOAD_ALLOWED_EXTENSIONS: list[str] = Field(default=[".jpg", ".jpeg", ".png", ".pdf", ".doc", ".docx"])
    STORAGE_TYPE: str = Field(default="local")  # local, s3, gcs
    S3_BUCKET: Optional[str] = Field(default=None)
    S3_REGION: Optional[str] = Field(default="us-east-1")
    AWS_ACCESS_KEY_ID: Optional[str] = Field(default=None)
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(default=None)
    
    # ==========================================
    # FEATURE FLAGS
    # ==========================================
    FEATURE_COFOUNDER_MATCHING: bool = Field(default=True)
    FEATURE_AI_MENTOR: bool = Field(default=True)
    FEATURE_COLLABORATION: bool = Field(default=True)
    FEATURE_DIMENSIONAL_ANALYSIS: bool = Field(default=True)
    FEATURE_REAL_GITHUB_API: bool = Field(default=False)  # Toggle real vs mock
    FEATURE_EMAIL_NOTIFICATIONS: bool = Field(default=False)
    
    # ==========================================
    # BUSINESS LOGIC SETTINGS
    # ==========================================
    # Idea validation
    MIN_IDEA_LENGTH: int = Field(default=20)
    MAX_IDEA_LENGTH: int = Field(default=5000)
    
    # Cofounder matching
    COFOUNDER_MATCH_TOP_K: int = Field(default=10)
    COFOUNDER_MIN_MATCH_SCORE: float = Field(default=0.4)
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = Field(default=20)
    MAX_PAGE_SIZE: int = Field(default=100)
    
    # ==========================================
    # VALIDATORS
    # ==========================================
    @field_validator("ENVIRONMENT", mode="before")
    @classmethod
    def validate_environment(cls, v):
        if isinstance(v, str):
            return Environment(v.lower())
        return v
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def validate_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @model_validator(mode='after')
    def validate_production_settings(self):
        if self.ENVIRONMENT == Environment.PRODUCTION:
            if not self.GROQ_API_KEY:
                raise ValueError("GROQ_API_KEY must be set in production")
            if "CHANGE_THIS" in self.SECRET_KEY:
                raise ValueError("SECRET_KEY must be changed in production")
            if "CHANGE_THIS" in self.JWT_SECRET_KEY:
                raise ValueError("JWT_SECRET_KEY must be changed in production")
        return self
    
    # ==========================================
    # COMPUTED PROPERTIES
    # ==========================================
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == Environment.PRODUCTION
    
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == Environment.DEVELOPMENT
    
    @property
    def is_testing(self) -> bool:
        return self.ENVIRONMENT == Environment.TESTING
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()


# Environment-specific overrides
def get_settings() -> Settings:
    """
    Dependency injection for FastAPI routes.
    Allows easy testing with overridden settings.
    """
    return settings


# Export commonly used values
__all__ = ["settings", "get_settings", "Environment"]
