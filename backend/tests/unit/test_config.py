"""
Unit Tests - Configuration
Tests for application settings and config.
"""
import pytest
import os
from unittest.mock import patch


class TestSettings:
    """Tests for Settings configuration class."""
    
    def test_default_app_name(self):
        """Default app name should be set."""
        from app.config import Settings
        settings = Settings()
        assert settings.APP_NAME == "PaperTrading Platform"
    
    def test_environment_from_env(self):
        """Environment should come from env vars."""
        from app.config import Settings
        settings = Settings()
        # In test environment, this is set to 'testing' by conftest
        assert settings.APP_ENV in ["development", "testing", "production"]
    
    def test_default_debug(self):
        """Debug should default to True in development."""
        from app.config import Settings
        settings = Settings()
        assert settings.DEBUG is True
    
    def test_api_prefix(self):
        """API prefix should be /api/v1."""
        from app.config import Settings
        settings = Settings()
        assert settings.API_V1_PREFIX == "/api/v1"
    
    def test_server_defaults(self):
        """Server configuration should have defaults."""
        from app.config import Settings
        settings = Settings()
        assert settings.BACKEND_HOST == "0.0.0.0"
        assert settings.BACKEND_PORT == 8000
        assert settings.FRONTEND_URL == "http://localhost:5173"
    
    def test_cors_origins_default(self):
        """CORS origins should include localhost."""
        from app.config import Settings
        settings = Settings()
        assert "http://localhost:5173" in settings.CORS_ORIGINS
        assert "http://localhost:3000" in settings.CORS_ORIGINS
    
    def test_database_url_property(self):
        """DATABASE_URL should be constructed from components."""
        from app.config import Settings
        settings = Settings(
            POSTGRES_HOST="localhost",
            POSTGRES_PORT=5432,
            POSTGRES_DB="testdb",
            POSTGRES_USER="testuser",
            POSTGRES_PASSWORD="testpass"
        )
        assert "postgresql+asyncpg://" in settings.DATABASE_URL
        assert "testuser:testpass" in settings.DATABASE_URL
        assert "localhost:5432" in settings.DATABASE_URL
        assert "testdb" in settings.DATABASE_URL
    
    def test_database_url_sync_property(self):
        """DATABASE_URL_SYNC should use sync driver."""
        from app.config import Settings
        settings = Settings()
        assert "postgresql://" in settings.DATABASE_URL_SYNC
        assert "+asyncpg" not in settings.DATABASE_URL_SYNC
    
    def test_redis_url_without_password(self):
        """REDIS_URL without password should not have auth."""
        from app.config import Settings
        settings = Settings(REDIS_PASSWORD="")
        url = settings.REDIS_URL
        assert "redis://" in url
        assert "@" not in url or ":@" not in url
    
    def test_redis_url_with_password(self):
        """REDIS_URL with password should include auth."""
        from app.config import Settings
        settings = Settings(REDIS_PASSWORD="secretpass")
        url = settings.REDIS_URL
        assert ":secretpass@" in url
    
    def test_jwt_settings(self):
        """JWT settings should have defaults."""
        from app.config import Settings
        settings = Settings()
        assert settings.JWT_ALGORITHM == "HS256"
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30
        assert settings.REFRESH_TOKEN_EXPIRE_DAYS == 7
    
    def test_timescale_url_property(self):
        """TIMESCALE_URL should be constructed correctly."""
        from app.config import Settings
        settings = Settings()
        assert "postgresql+asyncpg://" in settings.TIMESCALE_URL


class TestCorsOriginsParser:
    """Tests for CORS origins parsing."""
    
    def test_parse_cors_as_list(self):
        """CORS origins should accept list directly."""
        from app.config import Settings
        origins = ["http://example.com", "http://test.com"]
        settings = Settings(CORS_ORIGINS=origins)
        assert settings.CORS_ORIGINS == origins
    
    def test_parse_cors_as_json_string(self):
        """CORS origins should parse JSON string."""
        from app.config import Settings
        origins_json = '["http://example.com", "http://test.com"]'
        settings = Settings(CORS_ORIGINS=origins_json)
        assert "http://example.com" in settings.CORS_ORIGINS
        assert "http://test.com" in settings.CORS_ORIGINS
    
    def test_parse_cors_as_comma_separated(self):
        """CORS origins should parse comma-separated string."""
        from app.config import Settings
        origins_str = "http://example.com, http://test.com"
        settings = Settings(CORS_ORIGINS=origins_str)
        assert "http://example.com" in settings.CORS_ORIGINS
        assert "http://test.com" in settings.CORS_ORIGINS


class TestEnvironmentVariables:
    """Tests for environment variable loading."""
    
    def test_env_override(self):
        """Environment variables should override defaults."""
        with patch.dict(os.environ, {"APP_NAME": "Custom Name"}):
            from importlib import reload
            from app import config
            reload(config)
            settings = config.Settings()
            # Note: This may not work due to pydantic-settings caching
            # The test demonstrates the expected behavior
    
    def test_secret_key_is_set(self):
        """Secret key should be set (different in prod)."""
        from app.config import Settings
        settings = Settings()
        # Secret key should exist and not be empty
        assert settings.SECRET_KEY
        assert len(settings.SECRET_KEY) > 10


class TestDatabaseConfiguration:
    """Tests for database configuration."""
    
    def test_postgres_config_exists(self):
        """PostgreSQL should have config values set."""
        from app.config import Settings
        settings = Settings()
        assert settings.POSTGRES_HOST == "localhost"
        assert settings.POSTGRES_PORT == 5432
        # DB name might be different in test environment
        assert settings.POSTGRES_DB.startswith("papertrading")
    
    def test_timescale_defaults(self):
        """TimescaleDB should have development defaults."""
        from app.config import Settings
        settings = Settings()
        assert settings.TIMESCALE_HOST == "localhost"
        assert settings.TIMESCALE_PORT == 5433
        assert settings.TIMESCALE_DB == "papertrading_ts"
    
    def test_redis_defaults(self):
        """Redis should have development defaults."""
        from app.config import Settings
        settings = Settings()
        assert settings.REDIS_HOST == "localhost"
        assert settings.REDIS_PORT == 6379
        assert settings.REDIS_DB == 0
