"""
PaperTrading Platform - Configuration Settings
"""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
import json


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    # =========================
    # Application Settings
    # =========================
    APP_NAME: str = "PaperTrading Platform"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change-this-in-production"
    API_V1_PREFIX: str = "/api/v1"
    
    # =========================
    # Server Configuration
    # =========================
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v
    
    # =========================
    # Database - PostgreSQL
    # =========================
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "papertrading"
    POSTGRES_USER: str = "papertrading_user"
    POSTGRES_PASSWORD: str = "dev_password_123"
    # Optional: full DATABASE_URL from environment (overrides individual settings)
    DATABASE_URL_ENV: str = ""
    
    @property
    def DATABASE_URL(self) -> str:
        # Use environment DATABASE_URL if provided (for Docker)
        if self.DATABASE_URL_ENV:
            url = self.DATABASE_URL_ENV
            # Ensure it uses asyncpg driver
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    @property
    def DATABASE_URL_SYNC(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # =========================
    # Database - TimescaleDB
    # =========================
    TIMESCALE_HOST: str = "localhost"
    TIMESCALE_PORT: int = 5433
    TIMESCALE_DB: str = "papertrading_ts"
    TIMESCALE_USER: str = "papertrading_user"
    TIMESCALE_PASSWORD: str = "dev_password_123"
    
    @property
    def TIMESCALE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.TIMESCALE_USER}:{self.TIMESCALE_PASSWORD}@{self.TIMESCALE_HOST}:{self.TIMESCALE_PORT}/{self.TIMESCALE_DB}"
    
    # =========================
    # Redis
    # =========================
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    
    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # =========================
    # JWT Authentication
    # =========================
    JWT_SECRET_KEY: str = "your-jwt-secret-key-change-this"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # =========================
    # Data Providers - API Keys
    # =========================
    # US Market Primary
    ALPACA_API_KEY: str = ""
    ALPACA_SECRET_KEY: str = ""
    ALPACA_BASE_URL: str = "https://paper-api.alpaca.markets"
    
    POLYGON_API_KEY: str = ""
    
    # Global Coverage
    FINNHUB_API_KEY: str = ""
    TWELVE_DATA_API_KEY: str = ""
    
    # Historical Data
    EODHD_API_KEY: str = ""
    
    # Fundamentals
    FMP_API_KEY: str = ""
    ALPHA_VANTAGE_API_KEY: str = ""
    
    # Additional Providers
    NASDAQ_DATA_LINK_API_KEY: str = ""
    TIINGO_API_KEY: str = ""
    MARKETSTACK_API_KEY: str = ""
    STOCKDATA_API_KEY: str = ""
    INTRINIO_API_KEY: str = ""
    
    # =========================
    # Rate Limit Settings
    # =========================
    RATE_LIMIT_TARGET_PERCENT: int = 75
    
    # =========================
    # Scheduler Settings
    # =========================
    REALTIME_UPDATE_INTERVAL: int = 5  # minutes
    TIMEZONE: str = "UTC"
    
    # =========================
    # ML Settings
    # =========================
    ML_MODELS_PATH: str = "./ml_models"
    ML_RETRAIN_INTERVAL_DAYS: int = 7
    
    # =========================
    # Logging
    # =========================
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE: str = "logs/app.log"
    
    # =========================
    # Feature Flags
    # =========================
    ENABLE_ML_PREDICTIONS: bool = True
    ENABLE_WEBSOCKET_STREAMING: bool = True
    ENABLE_PROVIDER_HEALTH_MONITOR: bool = True


# Create global settings instance
settings = Settings()
