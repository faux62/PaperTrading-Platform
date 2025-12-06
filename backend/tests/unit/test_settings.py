"""
PaperTrading Platform - Settings Tests
Unit tests for user settings functionality.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from app.db.models.user_settings import UserSettings, _get_encryption_key


# =========================
# UserSettings Model Tests
# =========================

class TestUserSettingsModel:
    """Tests for UserSettings model."""

    def test_encrypt_decrypt_api_key(self):
        """Test API key encryption and decryption."""
        settings = UserSettings(user_id=1)
        original_key = "test-api-key-12345"
        
        encrypted = settings.encrypt_api_key(original_key)
        
        # Encrypted should be different from original
        assert encrypted != original_key
        assert encrypted is not None
        
        # Decrypted should match original
        decrypted = settings.decrypt_api_key(encrypted)
        assert decrypted == original_key

    def test_encrypt_none_returns_none(self):
        """Test that encrypting None returns None."""
        settings = UserSettings(user_id=1)
        
        result = settings.encrypt_api_key(None)
        assert result is None
        
        result = settings.encrypt_api_key("")
        assert result is None

    def test_decrypt_none_returns_none(self):
        """Test that decrypting None returns None."""
        settings = UserSettings(user_id=1)
        
        result = settings.decrypt_api_key(None)
        assert result is None
        
        result = settings.decrypt_api_key("")
        assert result is None

    def test_decrypt_invalid_returns_none(self):
        """Test that decrypting invalid data returns None."""
        settings = UserSettings(user_id=1)
        
        result = settings.decrypt_api_key("invalid-encrypted-data")
        assert result is None

    def test_set_provider_key(self):
        """Test setting a provider API key."""
        settings = UserSettings(user_id=1)
        
        settings.set_provider_key("finnhub", "my-finnhub-key")
        
        # Key should be stored encrypted
        assert settings.api_key_finnhub is not None
        assert settings.api_key_finnhub != "my-finnhub-key"

    def test_get_provider_key(self):
        """Test getting a provider API key."""
        settings = UserSettings(user_id=1)
        
        # Set and then get
        settings.set_provider_key("polygon", "my-polygon-key")
        result = settings.get_provider_key("polygon")
        
        assert result == "my-polygon-key"

    def test_get_nonexistent_provider_key(self):
        """Test getting key for non-configured provider."""
        settings = UserSettings(user_id=1)
        
        result = settings.get_provider_key("finnhub")
        assert result is None

    def test_has_provider_key(self):
        """Test checking if provider has key configured."""
        settings = UserSettings(user_id=1)
        
        assert settings.has_provider_key("finnhub") is False
        
        settings.set_provider_key("finnhub", "my-key")
        assert settings.has_provider_key("finnhub") is True

    def test_invalid_provider_set_get(self):
        """Test setting/getting key for invalid provider."""
        settings = UserSettings(user_id=1)
        
        # Should not raise, just ignore
        settings.set_provider_key("invalid_provider", "key")
        result = settings.get_provider_key("invalid_provider")
        
        assert result is None

    def test_default_values(self):
        """Test default values for settings."""
        settings = UserSettings(user_id=1)
        
        # Theme defaults
        assert settings.theme is None or settings.theme == "dark"
        
        # Notification defaults
        assert settings.notifications_email is None or settings.notifications_email is True
        assert settings.notifications_push is None or settings.notifications_push is True

    def test_encryption_key_consistency(self):
        """Test that encryption key is consistent."""
        key1 = _get_encryption_key()
        key2 = _get_encryption_key()
        
        assert key1 == key2

    def test_all_supported_providers(self):
        """Test all supported provider key columns exist."""
        settings = UserSettings(user_id=1)
        
        providers = [
            "alpaca", "alpaca_secret", "polygon", "finnhub", "twelvedata",
            "eodhd", "fmp", "alphavantage", "nasdaq", "tiingo",
            "marketstack", "stockdata", "intrinio", "yfinance", "stooq", "investingcom"
        ]
        
        for provider in providers:
            attr_name = f"api_key_{provider}"
            assert hasattr(settings, attr_name), f"Missing attribute: {attr_name}"


# =========================
# Settings API Tests
# =========================

class TestSettingsAPI:
    """Tests for settings API endpoints."""

    def test_mask_api_key_full(self):
        """Test API key masking with long key."""
        from app.api.v1.endpoints.settings import mask_api_key
        
        masked = mask_api_key("abcd1234efgh5678ijkl")
        
        assert masked.startswith("abcd")
        assert masked.endswith("ijkl")
        assert "****" in masked

    def test_mask_api_key_short(self):
        """Test API key masking with short key."""
        from app.api.v1.endpoints.settings import mask_api_key
        
        masked = mask_api_key("short")
        assert masked == "****"

    def test_mask_api_key_none(self):
        """Test API key masking with None."""
        from app.api.v1.endpoints.settings import mask_api_key
        
        masked = mask_api_key(None)
        assert masked is None

    def test_supported_providers_list(self):
        """Test that supported providers list is complete."""
        from app.api.v1.endpoints.settings import SUPPORTED_PROVIDERS
        
        expected = [
            "alpaca", "alpaca_secret", "polygon", "finnhub", "twelvedata",
            "eodhd", "fmp", "alphavantage", "nasdaq", "tiingo",
            "marketstack", "stockdata", "intrinio", "yfinance", "stooq", "investingcom"
        ]
        
        for provider in expected:
            assert provider in SUPPORTED_PROVIDERS, f"Missing provider: {provider}"

    def test_env_to_provider_mapping(self):
        """Test environment variable to provider mapping."""
        from app.api.v1.endpoints.settings import ENV_TO_PROVIDER
        
        assert ENV_TO_PROVIDER["ALPACA_API_KEY"] == "alpaca"
        assert ENV_TO_PROVIDER["POLYGON_API_KEY"] == "polygon"
        assert ENV_TO_PROVIDER["FINNHUB_API_KEY"] == "finnhub"
        assert ENV_TO_PROVIDER["ALPHA_VANTAGE_API_KEY"] == "alphavantage"


# =========================
# Schema Validation Tests
# =========================

class TestSettingsSchemas:
    """Tests for settings Pydantic schemas."""

    def test_api_key_request_validation(self):
        """Test ApiKeyRequest schema validation."""
        from app.api.v1.endpoints.settings import ApiKeyRequest
        
        # Valid request
        request = ApiKeyRequest(provider="finnhub", api_key="my-api-key")
        assert request.provider == "finnhub"
        assert request.api_key == "my-api-key"
        
        # Empty api_key should fail
        with pytest.raises(ValueError):
            ApiKeyRequest(provider="finnhub", api_key="")

    def test_notification_settings_defaults(self):
        """Test NotificationSettings schema defaults."""
        from app.api.v1.endpoints.settings import NotificationSettings
        
        settings = NotificationSettings()
        
        assert settings.email is True
        assert settings.push is True
        assert settings.trade_execution is True
        assert settings.price_alerts is True
        assert settings.portfolio_updates is True
        assert settings.market_news is False

    def test_display_settings_defaults(self):
        """Test DisplaySettings schema defaults."""
        from app.api.v1.endpoints.settings import DisplaySettings
        
        settings = DisplaySettings()
        
        assert settings.theme == "dark"
        assert settings.compact_mode is False
        assert settings.show_percent_change is True
        assert settings.default_chart_period == "1M"
        assert settings.chart_type == "candlestick"

    def test_test_connection_response(self):
        """Test TestConnectionResponse schema."""
        from app.api.v1.endpoints.settings import TestConnectionResponse
        
        response = TestConnectionResponse(
            provider="finnhub",
            success=True,
            message="Connection successful!"
        )
        
        assert response.provider == "finnhub"
        assert response.success is True
        assert "successful" in response.message

    def test_import_from_env_response(self):
        """Test ImportFromEnvResponse schema."""
        from app.api.v1.endpoints.settings import ImportFromEnvResponse
        
        response = ImportFromEnvResponse(
            imported=["finnhub", "polygon"],
            skipped=["alpaca (no env var)"],
            message="Imported 2 API keys"
        )
        
        assert len(response.imported) == 2
        assert len(response.skipped) == 1
        assert "2" in response.message
