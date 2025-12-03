"""
Integration Tests - Data Provider Base Classes
Tests for provider adapters with mocked external calls.
"""
import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from app.data_providers.adapters.base import (
    ProviderType,
    MarketType,
    DataType,
    TimeFrame,
    ProviderConfig,
    Quote,
    OHLCV,
    ProviderStatus,
    ProviderError,
    RateLimitError,
    DataNotAvailableError,
)


class TestProviderEnums:
    """Tests for provider enumeration types."""
    
    def test_provider_type_values(self):
        """ProviderType should have REST, WEBSOCKET, HYBRID."""
        assert ProviderType.REST.value == "rest"
        assert ProviderType.WEBSOCKET.value == "websocket"
        assert ProviderType.HYBRID.value == "hybrid"
    
    def test_market_type_values(self):
        """MarketType should cover all major markets."""
        assert MarketType.US_STOCK.value == "us_stock"
        assert MarketType.EU_STOCK.value == "eu_stock"
        assert MarketType.ASIA_STOCK.value == "asia_stock"
        assert MarketType.CRYPTO.value == "crypto"
        assert MarketType.FOREX.value == "forex"
    
    def test_data_type_values(self):
        """DataType should include all data categories."""
        assert DataType.QUOTE.value == "quote"
        assert DataType.OHLCV.value == "ohlcv"
        assert DataType.TRADE.value == "trade"
        assert DataType.ORDER_BOOK.value == "order_book"
        assert DataType.NEWS.value == "news"
        assert DataType.FUNDAMENTALS.value == "fundamentals"
    
    def test_timeframe_values(self):
        """TimeFrame should cover common intervals."""
        assert TimeFrame.MINUTE_1.value == "1min"
        assert TimeFrame.HOUR_1.value == "1hour"
        assert TimeFrame.DAY.value == "1day"
        assert TimeFrame.WEEK.value == "1week"
        assert TimeFrame.MONTH.value == "1month"


class TestProviderConfig:
    """Tests for ProviderConfig dataclass."""
    
    def test_config_defaults(self):
        """Config should have sensible defaults."""
        config = ProviderConfig(name="test_provider")
        assert config.name == "test_provider"
        assert config.requests_per_minute == 60
        assert config.requests_per_day == 10000
        assert config.timeout_seconds == 30.0
        assert config.retry_attempts == 3
        assert config.supports_websocket is False
    
    def test_config_with_api_key(self):
        """Config should store API credentials."""
        config = ProviderConfig(
            name="premium_provider",
            api_key="test_key_123",
            api_secret="test_secret_456",
            base_url="https://api.provider.com"
        )
        assert config.api_key == "test_key_123"
        assert config.api_secret == "test_secret_456"
        assert config.base_url == "https://api.provider.com"
    
    def test_config_rate_limits(self):
        """Config should support custom rate limits."""
        config = ProviderConfig(
            name="limited_provider",
            requests_per_minute=10,
            requests_per_day=500,
            max_symbols_per_request=5
        )
        assert config.requests_per_minute == 10
        assert config.requests_per_day == 500
        assert config.max_symbols_per_request == 5
    
    def test_config_cost_tracking(self):
        """Config should track costs."""
        config = ProviderConfig(
            name="paid_provider",
            cost_per_request=Decimal("0.001"),
            daily_budget=Decimal("10.00")
        )
        assert config.cost_per_request == Decimal("0.001")
        assert config.daily_budget == Decimal("10.00")


class TestQuoteDataclass:
    """Tests for Quote data structure."""
    
    def test_quote_creation(self):
        """Quote should be creatable with required fields."""
        quote = Quote(
            symbol="AAPL",
            price=Decimal("150.25"),
            provider="test_provider"
        )
        assert quote.symbol == "AAPL"
        assert quote.price == Decimal("150.25")
        assert quote.provider == "test_provider"
    
    def test_quote_full_data(self):
        """Quote should support all market data fields."""
        quote = Quote(
            symbol="MSFT",
            price=Decimal("380.50"),
            bid=Decimal("380.45"),
            ask=Decimal("380.55"),
            bid_size=100,
            ask_size=150,
            volume=5000000,
            change=Decimal("5.25"),
            change_percent=Decimal("1.40"),
            day_high=Decimal("382.00"),
            day_low=Decimal("375.00"),
            day_open=Decimal("376.50"),
            prev_close=Decimal("375.25"),
            exchange="NASDAQ",
            currency="USD",
            provider="test"
        )
        assert quote.bid == Decimal("380.45")
        assert quote.ask == Decimal("380.55")
        assert quote.change_percent == Decimal("1.40")
    
    def test_quote_to_dict(self):
        """Quote.to_dict() should serialize all fields."""
        quote = Quote(
            symbol="AAPL",
            price=Decimal("150.00"),
            volume=1000000,
            provider="test"
        )
        d = quote.to_dict()
        
        assert d["symbol"] == "AAPL"
        assert d["price"] == 150.0
        assert d["volume"] == 1000000
        assert "timestamp" in d
    
    def test_quote_default_market_type(self):
        """Quote should default to US_STOCK market type."""
        quote = Quote(symbol="TEST", price=Decimal("100"))
        assert quote.market_type == MarketType.US_STOCK
    
    def test_quote_default_currency(self):
        """Quote should default to USD currency."""
        quote = Quote(symbol="TEST", price=Decimal("100"))
        assert quote.currency == "USD"


class TestOHLCVDataclass:
    """Tests for OHLCV data structure."""
    
    def test_ohlcv_creation(self):
        """OHLCV should be creatable with required fields."""
        ohlcv = OHLCV(
            symbol="AAPL",
            timestamp=datetime.utcnow(),
            open=Decimal("150.00"),
            high=Decimal("152.00"),
            low=Decimal("149.00"),
            close=Decimal("151.50"),
            volume=5000000,
            provider="test"
        )
        assert ohlcv.symbol == "AAPL"
        assert ohlcv.open == Decimal("150.00")
        assert ohlcv.close == Decimal("151.50")
    
    def test_ohlcv_valid_hloc_relationship(self):
        """OHLCV high should be >= low."""
        ohlcv = OHLCV(
            symbol="TEST",
            timestamp=datetime.utcnow(),
            open=Decimal("100"),
            high=Decimal("105"),
            low=Decimal("95"),
            close=Decimal("102"),
            volume=1000
        )
        assert ohlcv.high >= ohlcv.low
        assert ohlcv.high >= ohlcv.open
        assert ohlcv.high >= ohlcv.close
        assert ohlcv.low <= ohlcv.open
        assert ohlcv.low <= ohlcv.close
    
    def test_ohlcv_to_dict(self):
        """OHLCV.to_dict() should serialize all fields."""
        timestamp = datetime.utcnow()
        ohlcv = OHLCV(
            symbol="MSFT",
            timestamp=timestamp,
            open=Decimal("380.00"),
            high=Decimal("385.00"),
            low=Decimal("378.00"),
            close=Decimal("382.50"),
            volume=3000000,
            adjusted_close=Decimal("382.50"),
            provider="test"
        )
        d = ohlcv.to_dict()
        
        assert d["symbol"] == "MSFT"
        assert d["open"] == 380.0
        assert d["high"] == 385.0
        assert d["close"] == 382.5
        assert d["volume"] == 3000000
    
    def test_ohlcv_default_timeframe(self):
        """OHLCV should default to DAY timeframe."""
        ohlcv = OHLCV(
            symbol="TEST",
            timestamp=datetime.utcnow(),
            open=Decimal("100"),
            high=Decimal("100"),
            low=Decimal("100"),
            close=Decimal("100"),
            volume=0
        )
        assert ohlcv.timeframe == TimeFrame.DAY


class TestProviderStatus:
    """Tests for ProviderStatus dataclass."""
    
    def test_status_defaults(self):
        """ProviderStatus should have healthy defaults."""
        status = ProviderStatus(name="test_provider")
        assert status.is_healthy is True
        assert status.is_available is True
        assert status.error_count == 0
        assert status.success_count == 0
    
    def test_status_tracking(self):
        """ProviderStatus should track metrics."""
        status = ProviderStatus(
            name="provider",
            is_healthy=True,
            success_count=100,
            error_count=5,
            avg_latency_ms=150.5,
            requests_today=105,
            cost_today=Decimal("0.105")
        )
        assert status.success_count == 100
        assert status.error_count == 5
        assert status.avg_latency_ms == 150.5
        assert status.requests_today == 105
    
    def test_status_error_tracking(self):
        """ProviderStatus should track errors."""
        now = datetime.utcnow()
        status = ProviderStatus(
            name="failing_provider",
            is_healthy=False,
            last_error=now,
            last_error_message="Connection timeout",
            error_count=10
        )
        assert status.is_healthy is False
        assert status.last_error_message == "Connection timeout"


class TestProviderExceptions:
    """Tests for provider exception classes."""
    
    def test_provider_error(self):
        """ProviderError should store provider name and message."""
        error = ProviderError("yfinance", "Connection failed")
        assert "yfinance" in str(error) or error.args[0] == "yfinance"
    
    def test_rate_limit_error(self):
        """RateLimitError should be a ProviderError subclass."""
        error = RateLimitError("polygon", "Rate limit exceeded")
        assert isinstance(error, ProviderError)
    
    def test_data_not_available_error(self):
        """DataNotAvailableError should be a ProviderError subclass."""
        error = DataNotAvailableError("finnhub", "Symbol not found: XYZ")
        assert isinstance(error, ProviderError)


class TestQuoteBatchOperations:
    """Tests for batch quote operations."""
    
    def test_multiple_quotes_list(self):
        """Should handle list of quotes."""
        quotes = [
            Quote(symbol="AAPL", price=Decimal("150.00")),
            Quote(symbol="MSFT", price=Decimal("380.00")),
            Quote(symbol="GOOGL", price=Decimal("140.00")),
        ]
        assert len(quotes) == 3
        symbols = [q.symbol for q in quotes]
        assert "AAPL" in symbols
        assert "MSFT" in symbols
        assert "GOOGL" in symbols
    
    def test_quotes_to_dict_list(self):
        """Should serialize multiple quotes."""
        quotes = [
            Quote(symbol="AAPL", price=Decimal("150.00")),
            Quote(symbol="MSFT", price=Decimal("380.00")),
        ]
        data = [q.to_dict() for q in quotes]
        assert len(data) == 2
        assert all("symbol" in d for d in data)
        assert all("price" in d for d in data)


class TestOHLCVBatchOperations:
    """Tests for batch OHLCV operations."""
    
    def test_historical_bars_list(self):
        """Should handle list of OHLCV bars."""
        base_date = datetime.utcnow()
        bars = [
            OHLCV(
                symbol="AAPL",
                timestamp=base_date - timedelta(days=i),
                open=Decimal(f"{150 + i}"),
                high=Decimal(f"{152 + i}"),
                low=Decimal(f"{148 + i}"),
                close=Decimal(f"{151 + i}"),
                volume=1000000 * (i + 1)
            )
            for i in range(5)
        ]
        assert len(bars) == 5
        # Bars should be in reverse chronological order
        assert bars[0].timestamp > bars[4].timestamp
    
    def test_ohlcv_date_range(self):
        """Should represent a date range of bars."""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 5)
        bars = [
            OHLCV(
                symbol="TEST",
                timestamp=start + timedelta(days=i),
                open=Decimal("100"),
                high=Decimal("100"),
                low=Decimal("100"),
                close=Decimal("100"),
                volume=1000
            )
            for i in range(5)
        ]
        assert bars[0].timestamp == start
        assert bars[-1].timestamp == datetime(2024, 1, 5)
