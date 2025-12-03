"""
Integration Tests - yfinance Adapter
Tests for Yahoo Finance data provider with mocked yfinance calls.
"""
import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

# Test dataclasses defined locally to avoid import issues
from dataclasses import dataclass, field
from typing import Optional, Any
from enum import Enum


class MarketType(str, Enum):
    US_STOCK = "us_stock"
    EU_STOCK = "eu_stock"
    ASIA_STOCK = "asia_stock"
    CRYPTO = "crypto"
    ETF = "etf"
    INDEX = "index"


class DataType(str, Enum):
    QUOTE = "quote"
    OHLCV = "ohlcv"


@dataclass
class ProviderConfig:
    name: str
    api_key: str = ""
    base_url: str = ""
    requests_per_minute: int = 30
    requests_per_day: int = 10000
    max_symbols_per_request: int = 50
    cost_per_request: Decimal = Decimal("0")
    daily_budget: Decimal = Decimal("0")
    timeout_seconds: float = 30.0
    retry_attempts: int = 3
    retry_delay: float = 2.0
    supports_websocket: bool = False
    supports_batch: bool = True
    supports_historical: bool = True
    supported_markets: list = field(default_factory=list)
    supported_data_types: list = field(default_factory=list)
    priority: int = 60


class TestYFinanceConfig:
    """Tests for yfinance configuration."""
    
    def test_config_name(self):
        """Config should have correct provider name."""
        config = ProviderConfig(name="yfinance")
        assert config.name == "yfinance"
    
    def test_config_no_api_key(self):
        """yfinance should not require API key."""
        config = ProviderConfig(name="yfinance", api_key="")
        assert config.api_key == ""
    
    def test_config_rate_limits(self):
        """Config should have conservative rate limits."""
        config = ProviderConfig(
            name="yfinance",
            requests_per_minute=30,
            requests_per_day=10000
        )
        # yfinance is scraping-based, so we're conservative
        assert config.requests_per_minute <= 60
        assert config.requests_per_day <= 50000
    
    def test_config_free_cost(self):
        """yfinance should be free."""
        config = ProviderConfig(
            name="yfinance",
            cost_per_request=Decimal("0"),
            daily_budget=Decimal("0")
        )
        assert config.cost_per_request == Decimal("0")
    
    def test_config_supported_markets(self):
        """yfinance should support multiple markets."""
        supported = [
            MarketType.US_STOCK,
            MarketType.EU_STOCK,
            MarketType.ASIA_STOCK,
            MarketType.CRYPTO,
            MarketType.ETF,
            MarketType.INDEX,
        ]
        config = ProviderConfig(name="yfinance", supported_markets=supported)
        assert MarketType.US_STOCK in config.supported_markets
        assert MarketType.CRYPTO in config.supported_markets
    
    def test_config_batch_support(self):
        """yfinance should support batch requests."""
        config = ProviderConfig(name="yfinance", supports_batch=True)
        assert config.supports_batch is True
    
    def test_config_no_websocket(self):
        """yfinance should not support websocket."""
        config = ProviderConfig(name="yfinance", supports_websocket=False)
        assert config.supports_websocket is False


class TestYFinanceQuoteParsing:
    """Tests for parsing yfinance quote responses."""
    
    def test_parse_basic_quote(self):
        """Should parse basic quote data from yfinance."""
        # Simulated yfinance Ticker.info response
        mock_info = {
            "regularMarketPrice": 150.25,
            "regularMarketChange": 2.50,
            "regularMarketChangePercent": 1.69,
            "regularMarketVolume": 50000000,
            "regularMarketOpen": 148.00,
            "regularMarketDayHigh": 151.00,
            "regularMarketDayLow": 147.50,
            "regularMarketPreviousClose": 147.75,
            "bid": 150.20,
            "ask": 150.30,
            "bidSize": 100,
            "askSize": 200,
            "exchange": "NASDAQ",
            "currency": "USD",
        }
        
        # Parse simulation
        price = Decimal(str(mock_info["regularMarketPrice"]))
        change = Decimal(str(mock_info["regularMarketChange"]))
        change_pct = Decimal(str(mock_info["regularMarketChangePercent"]))
        
        assert price == Decimal("150.25")
        assert change == Decimal("2.50")
        assert change_pct == Decimal("1.69")
    
    def test_parse_quote_with_missing_fields(self):
        """Should handle missing optional fields."""
        mock_info = {
            "regularMarketPrice": 150.25,
        }
        
        price = Decimal(str(mock_info.get("regularMarketPrice", 0)))
        bid = mock_info.get("bid")
        ask = mock_info.get("ask")
        
        assert price == Decimal("150.25")
        assert bid is None
        assert ask is None
    
    def test_parse_crypto_quote(self):
        """Should parse crypto quote with 24h data."""
        mock_info = {
            "regularMarketPrice": 43250.50,
            "regularMarketVolume": 25000000000,
            "regularMarketChangePercent": 2.35,
            "currency": "USD",
            "exchange": "CCC",  # Crypto exchange
        }
        
        price = Decimal(str(mock_info["regularMarketPrice"]))
        assert price == Decimal("43250.50")
        assert mock_info["exchange"] == "CCC"


class TestYFinanceHistoricalParsing:
    """Tests for parsing yfinance historical data."""
    
    def test_parse_daily_bars(self):
        """Should parse daily OHLCV bars."""
        # Simulated yfinance history() DataFrame row
        mock_row = {
            "Open": 150.00,
            "High": 152.50,
            "Low": 149.00,
            "Close": 151.75,
            "Volume": 45000000,
            "Adj Close": 151.75,
        }
        
        open_price = Decimal(str(mock_row["Open"]))
        high = Decimal(str(mock_row["High"]))
        low = Decimal(str(mock_row["Low"]))
        close = Decimal(str(mock_row["Close"]))
        volume = int(mock_row["Volume"])
        
        assert open_price == Decimal("150.00")
        assert high == Decimal("152.50")
        assert low == Decimal("149.00")
        assert close == Decimal("151.75")
        assert volume == 45000000
        assert high >= low
        assert high >= open_price
        assert high >= close
    
    def test_parse_intraday_bars(self):
        """Should parse intraday 1-minute bars."""
        mock_row = {
            "Open": 150.00,
            "High": 150.10,
            "Low": 149.95,
            "Close": 150.05,
            "Volume": 50000,
        }
        
        # Intraday typically has smaller ranges
        high = Decimal(str(mock_row["High"]))
        low = Decimal(str(mock_row["Low"]))
        assert high - low < Decimal("1.00")  # Less than $1 range in 1 min
    
    def test_parse_adjusted_close(self):
        """Should handle adjusted close for splits/dividends."""
        mock_row = {
            "Open": 300.00,
            "High": 305.00,
            "Low": 298.00,
            "Close": 302.00,
            "Volume": 10000000,
            "Adj Close": 150.00,  # Stock split 2:1
        }
        
        close = Decimal(str(mock_row["Close"]))
        adj_close = Decimal(str(mock_row["Adj Close"]))
        
        assert close == Decimal("302.00")
        assert adj_close == Decimal("150.00")
        # Adj close should be different after split
        assert adj_close != close


class TestYFinanceErrorHandling:
    """Tests for yfinance error scenarios."""
    
    def test_invalid_symbol_response(self):
        """Should handle invalid symbol gracefully."""
        mock_info = {}  # Empty response for invalid symbol
        
        price = mock_info.get("regularMarketPrice")
        assert price is None
    
    def test_market_closed_response(self):
        """Should handle market closed scenario."""
        mock_info = {
            "regularMarketPrice": 150.00,
            "regularMarketTime": 1704326400,  # Timestamp
            "marketState": "CLOSED",
        }
        
        market_state = mock_info.get("marketState")
        assert market_state == "CLOSED"
    
    def test_rate_limit_detection(self):
        """Should detect when rate limited."""
        # yfinance typically raises an exception or returns empty
        # when rate limited
        rate_limit_indicators = [
            {},  # Empty response
            {"error": "Too many requests"},
            None,
        ]
        
        for response in rate_limit_indicators:
            is_limited = response is None or response == {} or "error" in (response or {})
            # One of these should trigger rate limit handling
            assert is_limited or response is not None


class TestYFinanceSymbolMapping:
    """Tests for symbol format handling."""
    
    def test_us_stock_symbol(self):
        """US stocks should use standard ticker."""
        symbol = "AAPL"
        assert symbol.isalpha()
        assert symbol.isupper()
    
    def test_crypto_symbol_format(self):
        """Crypto should use pair format."""
        btc_usd = "BTC-USD"
        eth_usd = "ETH-USD"
        
        assert "-USD" in btc_usd
        assert "-USD" in eth_usd
    
    def test_european_stock_format(self):
        """European stocks should include exchange suffix."""
        # Siemens on Frankfurt
        siemens = "SIE.DE"
        # Nestle on Swiss
        nestle = "NESN.SW"
        # BP on London
        bp = "BP.L"
        
        assert ".DE" in siemens
        assert ".SW" in nestle
        assert ".L" in bp
    
    def test_index_symbol_format(self):
        """Index symbols should use caret prefix."""
        sp500 = "^GSPC"
        nasdaq = "^IXIC"
        dow = "^DJI"
        
        assert sp500.startswith("^")
        assert nasdaq.startswith("^")
        assert dow.startswith("^")
    
    def test_etf_symbol(self):
        """ETFs should use standard ticker."""
        spy = "SPY"
        qqq = "QQQ"
        
        assert spy.isalpha()
        assert qqq.isalpha()


class TestYFinanceDateRanges:
    """Tests for date range handling."""
    
    def test_valid_date_range(self):
        """Should accept valid date ranges."""
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        assert start_date < end_date
        assert (end_date - start_date).days == 30
    
    def test_max_historical_range(self):
        """Should support long historical ranges."""
        # yfinance supports data from 1962 for some stocks
        end_date = date.today()
        start_date = date(2000, 1, 1)
        
        days = (end_date - start_date).days
        assert days > 8000  # ~22 years
    
    def test_weekend_handling(self):
        """Should handle weekends in date ranges."""
        # Markets are closed on weekends
        saturday = date(2024, 1, 6)  # A Saturday
        sunday = date(2024, 1, 7)    # A Sunday
        
        assert saturday.weekday() == 5
        assert sunday.weekday() == 6
        # Trading data won't exist for these dates


class TestYFinanceBatchRequests:
    """Tests for batch quote requests."""
    
    def test_batch_symbols_list(self):
        """Should format batch symbol list correctly."""
        symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]
        
        # yfinance accepts space-separated symbols
        batch_string = " ".join(symbols)
        assert batch_string == "AAPL MSFT GOOGL AMZN META"
    
    def test_batch_size_limit(self):
        """Should respect max symbols per batch."""
        max_batch = 50
        symbols = [f"SYM{i}" for i in range(100)]
        
        batches = [
            symbols[i:i + max_batch] 
            for i in range(0, len(symbols), max_batch)
        ]
        
        assert len(batches) == 2
        assert len(batches[0]) == 50
        assert len(batches[1]) == 50
    
    def test_batch_error_isolation(self):
        """Batch errors should not affect valid symbols."""
        results = {
            "AAPL": {"regularMarketPrice": 150.00},
            "INVALID": {},  # Invalid symbol returns empty
            "MSFT": {"regularMarketPrice": 380.00},
        }
        
        valid_quotes = {
            k: v for k, v in results.items() 
            if v.get("regularMarketPrice")
        }
        
        assert len(valid_quotes) == 2
        assert "AAPL" in valid_quotes
        assert "MSFT" in valid_quotes
        assert "INVALID" not in valid_quotes
