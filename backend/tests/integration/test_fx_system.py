"""
Integration Tests - FX Rate System
Tests for the FX rate update job and exchange rate integration.

Note: These tests require Docker containers running for full integration.
For unit tests, see tests/unit/test_fx_rate_service.py
"""
import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

# Test configuration
TEST_USER = "faux62"
TEST_PASSWORD = "Pallazz@99"


class TestFxRateUpdateJob:
    """Tests for the FX rate scheduler job."""
    
    @pytest.mark.asyncio
    async def test_fx_rate_updater_service_creation(self):
        """FxRateUpdaterService should be importable and instantiable."""
        from app.services.fx_rate_updater import FxRateUpdaterService
        
        service = FxRateUpdaterService()
        
        assert service is not None
        assert service.timeout > 0
        assert len(service.currencies) == 4
    
    @pytest.mark.asyncio
    async def test_update_function_exists(self):
        """update_exchange_rates function should exist for scheduler."""
        from app.services.fx_rate_updater import update_exchange_rates
        
        assert callable(update_exchange_rates)
    
    def test_bot_scheduler_has_fx_job(self):
        """Bot scheduler should have fx_rate_update job configured."""
        # This tests that the job is defined in bot/__init__.py
        # Without actually starting the scheduler
        
        # Import the bot module to check job configuration
        try:
            from app.bot import create_scheduler_jobs
            # If the function exists, the job configuration is present
            assert callable(create_scheduler_jobs)
        except ImportError:
            # Alternative: check bot/__init__.py content
            import os
            bot_init = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "app", "bot", "__init__.py"
            )
            
            if os.path.exists(bot_init):
                with open(bot_init) as f:
                    content = f.read()
                    assert "fx_rate_update" in content or "update_exchange_rates" in content


class TestExchangeRateRepository:
    """Integration tests for ExchangeRateRepository."""
    
    @pytest.mark.asyncio
    async def test_repository_methods_exist(self):
        """Repository should have all required methods."""
        from app.db.repositories.exchange_rate import ExchangeRateRepository
        
        assert hasattr(ExchangeRateRepository, 'get_rate')
        assert hasattr(ExchangeRateRepository, 'get_rate_value')
        assert hasattr(ExchangeRateRepository, 'get_all_rates')
        assert hasattr(ExchangeRateRepository, 'upsert_rate')
        assert hasattr(ExchangeRateRepository, 'bulk_upsert_rates')
        assert hasattr(ExchangeRateRepository, 'convert_amount')
    
    @pytest.mark.asyncio
    async def test_model_structure(self):
        """ExchangeRate model should have correct structure."""
        from app.db.models.exchange_rate import ExchangeRate
        
        # Check table name
        assert ExchangeRate.__tablename__ == "exchange_rates"
        
        # Check columns exist
        assert hasattr(ExchangeRate, 'base_currency')
        assert hasattr(ExchangeRate, 'quote_currency')
        assert hasattr(ExchangeRate, 'rate')
        assert hasattr(ExchangeRate, 'source')
        assert hasattr(ExchangeRate, 'fetched_at')


class TestCurrencyConversionIntegration:
    """Integration tests for currency conversion using DB rates."""
    
    @pytest.mark.asyncio
    async def test_convert_function_exists(self):
        """convert() function should exist in utils/currency.py."""
        from app.utils.currency import convert
        
        assert callable(convert)
    
    @pytest.mark.asyncio
    async def test_get_exchange_rate_from_db_exists(self):
        """get_exchange_rate_from_db() function should exist."""
        from app.utils.currency import get_exchange_rate_from_db
        
        assert callable(get_exchange_rate_from_db)
    
    @pytest.mark.asyncio
    async def test_convert_same_currency_no_db(self):
        """Converting same currency should return same amount without DB."""
        from app.utils.currency import convert
        
        # Mock DB to ensure it's not called for same currency
        mock_db = AsyncMock()
        
        result = await convert(
            amount=Decimal("100.00"),
            from_currency="USD",
            to_currency="USD",
            db=mock_db
        )
        
        assert result == Decimal("100.00")
        # DB should not be called for same currency
        assert not mock_db.execute.called
    
    @pytest.mark.asyncio
    async def test_convert_with_mock_rate(self):
        """Converting should use rate from DB."""
        from app.utils.currency import convert
        
        # Create mock DB that returns a rate
        mock_db = AsyncMock()
        mock_rate = MagicMock()
        mock_rate.rate = Decimal("1.08")
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_rate
        mock_db.execute.return_value = mock_result
        
        result = await convert(
            amount=Decimal("100.00"),
            from_currency="EUR",
            to_currency="USD",
            db=mock_db
        )
        
        assert result == Decimal("108.00")


class TestPositionWithFx:
    """Integration tests for positions with FX handling."""
    
    def test_position_model_no_fx_fields(self):
        """Position model should NOT have deprecated FX fields."""
        from app.db.models.position import Position
        
        # These fields should have been removed
        assert not hasattr(Position, 'avg_cost_portfolio') or \
               Position.__table__.columns.get('avg_cost_portfolio') is None
        assert not hasattr(Position, 'entry_exchange_rate') or \
               Position.__table__.columns.get('entry_exchange_rate') is None
    
    def test_position_has_required_fields(self):
        """Position model should have required fields."""
        from app.db.models.position import Position
        
        assert hasattr(Position, 'avg_cost')  # Native currency cost
        assert hasattr(Position, 'current_price')  # Native currency price
        assert hasattr(Position, 'market_value')  # Portfolio currency value
        assert hasattr(Position, 'unrealized_pnl')  # Portfolio currency P&L


class TestTradingWithFx:
    """Integration tests for trading operations with FX."""
    
    def test_trade_model_has_fx_fields(self):
        """Trade model should have FX fields for audit trail."""
        from app.db.models.trade import Trade
        
        assert hasattr(Trade, 'exchange_rate')
        assert hasattr(Trade, 'native_currency')
    
    @pytest.mark.asyncio
    async def test_position_analytics_functions(self):
        """Position analytics functions should be available."""
        from app.services.position_analytics import (
            get_historical_cost_in_portfolio_currency,
            get_avg_entry_exchange_rate,
            get_position_cost_breakdown,
            calculate_forex_impact,
        )
        
        assert callable(get_historical_cost_in_portfolio_currency)
        assert callable(get_avg_entry_exchange_rate)
        assert callable(get_position_cost_breakdown)
        assert callable(calculate_forex_impact)


class TestGlobalPriceUpdaterWithFx:
    """Integration tests for GlobalPriceUpdater with FX support."""
    
    def test_price_updater_exists(self):
        """GlobalPriceUpdater should exist."""
        from app.bot.services.global_price_updater import GlobalPriceUpdater
        
        assert GlobalPriceUpdater is not None
    
    def test_update_position_price_accepts_currency(self):
        """update_position_price should accept portfolio_currency parameter."""
        from app.bot.services.global_price_updater import GlobalPriceUpdater
        import inspect
        
        # Get the update_position_price method signature
        sig = inspect.signature(GlobalPriceUpdater.update_position_price)
        params = list(sig.parameters.keys())
        
        # Should have portfolio_currency parameter
        assert 'portfolio_currency' in params


class TestApiSchemasNoDeprecatedFields:
    """Integration tests to verify API schemas don't expose deprecated fields."""
    
    def test_position_response_schema(self):
        """PositionResponse should not have deprecated FX fields."""
        from app.api.v1.endpoints.positions import PositionResponse
        
        fields = PositionResponse.model_fields
        
        # These should NOT be in the response
        assert 'avg_cost_portfolio' not in fields
        assert 'entry_exchange_rate' not in fields
        assert 'native_currency' not in fields  # Removed in refactoring
        
        # These SHOULD be in the response
        assert 'avg_cost' in fields
        assert 'current_price' in fields
        assert 'market_value' in fields
        assert 'unrealized_pnl' in fields


class TestFrankfurterApiIntegration:
    """Integration tests for Frankfurter API (live tests - skip if no network)."""
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires network access - run manually")
    async def test_fetch_rates_live(self):
        """Actually fetch rates from Frankfurter API."""
        from app.services.fx_rate_updater import FxRateUpdaterService
        
        service = FxRateUpdaterService(timeout=30.0)
        rates = await service.fetch_rates_from_api("EUR")
        
        assert rates is not None
        assert "USD" in rates
        assert "GBP" in rates
        assert "CHF" in rates
        
        # Sanity check on rates
        assert Decimal("0.5") < rates["USD"] < Decimal("2.0")
        assert Decimal("0.5") < rates["GBP"] < Decimal("2.0")
        assert Decimal("0.5") < rates["CHF"] < Decimal("2.0")
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires network access - run manually")
    async def test_fetch_all_rates_live(self):
        """Fetch all 12 currency pairs from API."""
        from app.services.fx_rate_updater import FxRateUpdaterService
        
        service = FxRateUpdaterService(timeout=30.0)
        rates = await service.fetch_all_rates()
        
        # Should get 12 pairs (4 currencies × 3 other currencies each)
        assert len(rates) == 12
        
        for rate_info in rates:
            assert rate_info["base_currency"] in ["EUR", "USD", "GBP", "CHF"]
            assert rate_info["quote_currency"] in ["EUR", "USD", "GBP", "CHF"]
            assert rate_info["base_currency"] != rate_info["quote_currency"]
            assert Decimal("0") < rate_info["rate"] < Decimal("10")
