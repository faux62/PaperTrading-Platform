"""
Base Provider Adapter Interface

Defines the abstract interface that all data provider adapters must implement.
Provides common functionality for rate limiting, error handling, and data normalization.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional, Any, AsyncIterator
import asyncio
from loguru import logger


class ProviderType(str, Enum):
    """Types of data providers."""
    REST = "rest"
    WEBSOCKET = "websocket"
    HYBRID = "hybrid"  # Supports both REST and WebSocket


class MarketType(str, Enum):
    """Supported market types."""
    US_STOCK = "us_stock"
    EU_STOCK = "eu_stock"
    ASIA_STOCK = "asia_stock"
    CRYPTO = "crypto"
    FOREX = "forex"
    COMMODITY = "commodity"
    INDEX = "index"
    ETF = "etf"
    US_OPTION = "us_option"


class DataType(str, Enum):
    """Types of data a provider can supply."""
    QUOTE = "quote"
    OHLCV = "ohlcv"
    TRADE = "trade"
    ORDER_BOOK = "order_book"
    NEWS = "news"
    FUNDAMENTALS = "fundamentals"
    OPTIONS = "options"


class TimeFrame(str, Enum):
    """Supported timeframes for historical data."""
    TICK = "tick"
    MINUTE_1 = "1min"
    MINUTE_5 = "5min"
    MINUTE_15 = "15min"
    MINUTE_30 = "30min"
    HOUR_1 = "1hour"
    HOUR_4 = "4hour"
    DAY = "1day"
    WEEK = "1week"
    MONTH = "1month"


@dataclass
class ProviderConfig:
    """Configuration for a data provider."""
    name: str
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    base_url: str = ""
    websocket_url: Optional[str] = None
    
    # Rate limiting
    requests_per_minute: int = 60
    requests_per_day: int = 10000
    max_symbols_per_request: int = 100
    
    # Costs
    cost_per_request: Decimal = Decimal("0")
    daily_budget: Decimal = Decimal("0")
    
    # Timeouts
    timeout_seconds: float = 30.0
    retry_attempts: int = 3
    retry_delay: float = 1.0
    
    # Feature flags
    supports_websocket: bool = False
    supports_batch: bool = False
    supports_historical: bool = True
    
    # Market coverage
    supported_markets: list[MarketType] = field(default_factory=list)
    supported_data_types: list[DataType] = field(default_factory=list)
    
    # Priority (lower = higher priority)
    priority: int = 100


@dataclass
class Quote:
    """Normalized quote data structure."""
    symbol: str
    price: Decimal
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None
    volume: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    provider: str = ""
    market_type: MarketType = MarketType.US_STOCK
    
    # Change metrics
    change: Optional[Decimal] = None
    change_percent: Optional[Decimal] = None
    
    # Day range
    day_high: Optional[Decimal] = None
    day_low: Optional[Decimal] = None
    day_open: Optional[Decimal] = None
    prev_close: Optional[Decimal] = None
    
    # Additional info
    exchange: Optional[str] = None
    currency: str = "USD"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "symbol": self.symbol,
            "price": float(self.price),
            "bid": float(self.bid) if self.bid else None,
            "ask": float(self.ask) if self.ask else None,
            "bid_size": self.bid_size,
            "ask_size": self.ask_size,
            "volume": self.volume,
            "timestamp": self.timestamp.isoformat(),
            "provider": self.provider,
            "market_type": self.market_type.value,
            "change": float(self.change) if self.change else None,
            "change_percent": float(self.change_percent) if self.change_percent else None,
            "day_high": float(self.day_high) if self.day_high else None,
            "day_low": float(self.day_low) if self.day_low else None,
            "day_open": float(self.day_open) if self.day_open else None,
            "prev_close": float(self.prev_close) if self.prev_close else None,
            "exchange": self.exchange,
            "currency": self.currency,
        }


@dataclass
class OHLCV:
    """Normalized OHLCV (candlestick) data structure."""
    symbol: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    provider: str = ""
    timeframe: TimeFrame = TimeFrame.DAY
    
    # Optional
    adjusted_close: Optional[Decimal] = None
    vwap: Optional[Decimal] = None
    trade_count: Optional[int] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "open": float(self.open),
            "high": float(self.high),
            "low": float(self.low),
            "close": float(self.close),
            "volume": self.volume,
            "provider": self.provider,
            "timeframe": self.timeframe.value,
            "adjusted_close": float(self.adjusted_close) if self.adjusted_close else None,
            "vwap": float(self.vwap) if self.vwap else None,
            "trade_count": self.trade_count,
        }


@dataclass
class ProviderStatus:
    """Status information for a provider."""
    name: str
    is_healthy: bool = True
    is_available: bool = True
    last_success: Optional[datetime] = None
    last_error: Optional[datetime] = None
    last_error_message: Optional[str] = None
    error_count: int = 0
    success_count: int = 0
    avg_latency_ms: float = 0.0
    requests_today: int = 0
    cost_today: Decimal = Decimal("0")


class ProviderError(Exception):
    """Base exception for provider errors."""
    def __init__(self, provider: str, message: str, recoverable: bool = True):
        self.provider = provider
        self.message = message
        self.recoverable = recoverable
        super().__init__(f"[{provider}] {message}")


class RateLimitError(ProviderError):
    """Rate limit exceeded error."""
    def __init__(self, provider: str, retry_after: Optional[float] = None):
        self.retry_after = retry_after
        super().__init__(provider, f"Rate limit exceeded. Retry after: {retry_after}s", recoverable=True)


class AuthenticationError(ProviderError):
    """Authentication failed error."""
    def __init__(self, provider: str, message: str = "Authentication failed"):
        super().__init__(provider, message, recoverable=False)


class DataNotAvailableError(ProviderError):
    """Requested data not available."""
    def __init__(self, provider: str, symbol: str, data_type: str):
        super().__init__(provider, f"Data not available for {symbol} ({data_type})", recoverable=False)


class BaseAdapter(ABC):
    """
    Abstract base class for all data provider adapters.
    
    Each provider adapter must implement:
    - get_quote(): Get real-time quote for a symbol
    - get_quotes(): Get quotes for multiple symbols (batch)
    - get_historical(): Get historical OHLCV data
    - health_check(): Verify provider connectivity
    """
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.name = config.name
        self._status = ProviderStatus(name=config.name)
        self._session = None
        self._ws_connection = None
        
    @property
    def status(self) -> ProviderStatus:
        """Get current provider status."""
        return self._status
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the adapter (create sessions, validate credentials)."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Clean up resources."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is healthy and accessible."""
        pass
    
    @abstractmethod
    async def get_quote(self, symbol: str) -> Quote:
        """
        Get real-time quote for a single symbol.
        
        Args:
            symbol: The ticker symbol (e.g., "AAPL")
            
        Returns:
            Quote object with normalized data
            
        Raises:
            ProviderError: If the request fails
        """
        pass
    
    @abstractmethod
    async def get_quotes(self, symbols: list[str]) -> list[Quote]:
        """
        Get quotes for multiple symbols (batch request).
        
        Args:
            symbols: List of ticker symbols
            
        Returns:
            List of Quote objects
        """
        pass
    
    @abstractmethod
    async def get_historical(
        self,
        symbol: str,
        start_date: date,
        end_date: Optional[date] = None,
        timeframe: TimeFrame = TimeFrame.DAY,
    ) -> list[OHLCV]:
        """
        Get historical OHLCV data.
        
        Args:
            symbol: The ticker symbol
            start_date: Start date for historical data
            end_date: End date (defaults to today)
            timeframe: Data timeframe/interval
            
        Returns:
            List of OHLCV objects sorted by timestamp
        """
        pass
    
    # Optional WebSocket methods (override in WebSocket-capable adapters)
    async def connect_websocket(self) -> None:
        """Connect to WebSocket stream."""
        raise NotImplementedError(f"{self.name} does not support WebSocket")
    
    async def disconnect_websocket(self) -> None:
        """Disconnect from WebSocket stream."""
        pass
    
    async def subscribe(self, symbols: list[str]) -> None:
        """Subscribe to real-time updates for symbols."""
        raise NotImplementedError(f"{self.name} does not support WebSocket subscriptions")
    
    async def unsubscribe(self, symbols: list[str]) -> None:
        """Unsubscribe from real-time updates."""
        raise NotImplementedError(f"{self.name} does not support WebSocket subscriptions")
    
    async def stream_quotes(self) -> AsyncIterator[Quote]:
        """Stream real-time quotes from WebSocket."""
        raise NotImplementedError(f"{self.name} does not support quote streaming")
        yield  # Make this an async generator
    
    # Helper methods
    def _record_success(self, latency_ms: float) -> None:
        """Record a successful request."""
        self._status.success_count += 1
        self._status.last_success = datetime.utcnow()
        self._status.requests_today += 1
        
        # Update average latency (exponential moving average)
        alpha = 0.1
        self._status.avg_latency_ms = (
            alpha * latency_ms + (1 - alpha) * self._status.avg_latency_ms
        )
        
        # Reset error count on success
        self._status.error_count = 0
        self._status.is_healthy = True
    
    def _record_error(self, error: Exception) -> None:
        """Record a failed request."""
        self._status.error_count += 1
        self._status.last_error = datetime.utcnow()
        self._status.last_error_message = str(error)
        
        # Mark as unhealthy after too many consecutive errors
        if self._status.error_count >= 5:
            self._status.is_healthy = False
            logger.warning(f"Provider {self.name} marked as unhealthy after {self._status.error_count} errors")
    
    def _record_cost(self, cost: Decimal) -> None:
        """Record the cost of a request."""
        self._status.cost_today += cost
    
    def supports_market(self, market_type: MarketType) -> bool:
        """Check if this provider supports a market type."""
        return market_type in self.config.supported_markets
    
    def supports_data_type(self, data_type: DataType) -> bool:
        """Check if this provider supports a data type."""
        return data_type in self.config.supported_data_types
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name}, healthy={self._status.is_healthy})>"
