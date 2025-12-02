"""
Tiingo Adapter

Provides access to Tiingo market data API for US stocks.
Supports REST API for quotes and historical data.

API Documentation: https://api.tiingo.com/documentation
Free tier: 500 requests/day, end-of-day data
"""
from datetime import datetime, date, timezone
from decimal import Decimal
from typing import Optional, Any
import aiohttp
from loguru import logger

from app.data_providers.adapters.base import (
    BaseAdapter,
    ProviderConfig,
    MarketType,
    DataType,
    TimeFrame,
    Quote,
    OHLCV,
    ProviderError,
    RateLimitError,
    AuthenticationError,
    DataNotAvailableError,
)


TIINGO_BASE_URL = "https://api.tiingo.com"
TIINGO_IEX_URL = "https://api.tiingo.com/iex"


def create_tiingo_config(api_key: str) -> ProviderConfig:
    """Create configuration for Tiingo adapter."""
    return ProviderConfig(
        name="tiingo",
        api_key=api_key,
        base_url=TIINGO_BASE_URL,
        requests_per_minute=50,
        requests_per_day=500,  # Free tier daily limit
        max_symbols_per_request=100,
        cost_per_request=Decimal("0"),
        daily_budget=Decimal("0"),
        timeout_seconds=30.0,
        retry_attempts=3,
        retry_delay=1.0,
        supports_websocket=False,
        supports_batch=True,
        supports_historical=True,
        supported_markets=[MarketType.US_STOCK, MarketType.CRYPTO],
        supported_data_types=[DataType.QUOTE, DataType.OHLCV],
        priority=40,
    )


class TiingoAdapter(BaseAdapter):
    """
    Tiingo data provider adapter.
    
    Features:
    - Real-time IEX quotes
    - Historical end-of-day data
    - Batch quote requests
    - Crypto and Forex support
    
    Usage:
        config = create_tiingo_config("your_api_key")
        adapter = TiingoAdapter(config)
        await adapter.initialize()
        
        quote = await adapter.get_quote("AAPL")
        bars = await adapter.get_historical("AAPL", start_date, end_date)
    """
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None
    
    @property
    def _headers(self) -> dict[str, str]:
        """Get authentication headers."""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Token {self.config.api_key}",
        }
    
    async def initialize(self) -> None:
        """Initialize HTTP session."""
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            self._session = aiohttp.ClientSession(
                headers=self._headers,
                timeout=timeout,
            )
            logger.info("Tiingo adapter initialized")
    
    async def close(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
        logger.info("Tiingo adapter closed")
    
    async def health_check(self) -> bool:
        """Check API connectivity."""
        try:
            url = f"{TIINGO_IEX_URL}/AAPL"
            async with self._session.get(url) as response:
                if response.status == 200:
                    return True
                elif response.status == 401:
                    logger.error("Tiingo authentication failed")
                    return False
                else:
                    logger.warning(f"Tiingo health check status: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Tiingo health check failed: {e}")
            return False
    
    # ==================== REST API Methods ====================
    
    async def get_quote(self, symbol: str) -> Quote:
        """Get latest quote for a symbol from IEX."""
        symbol = symbol.upper()
        url = f"{TIINGO_IEX_URL}/{symbol}"
        
        try:
            start_time = datetime.now()
            async with self._session.get(url) as response:
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    data = await response.json()
                    
                    if not data or len(data) == 0:
                        raise DataNotAvailableError("tiingo", symbol, "quote")
                    
                    quote = self._parse_iex_quote(data[0])
                    self._record_success(latency_ms)
                    return quote
                    
                elif response.status == 401:
                    raise AuthenticationError("tiingo")
                elif response.status == 429:
                    raise RateLimitError("tiingo", retry_after=60)
                elif response.status == 404:
                    raise DataNotAvailableError("tiingo", symbol, "quote")
                else:
                    error_text = await response.text()
                    raise ProviderError("tiingo", f"API error {response.status}: {error_text}")
                    
        except aiohttp.ClientError as e:
            self._record_error(e)
            raise ProviderError("tiingo", f"Connection error: {e}")
    
    async def get_quotes(self, symbols: list[str]) -> list[Quote]:
        """Get quotes for multiple symbols."""
        if not symbols:
            return []
        
        symbols = [s.upper() for s in symbols]
        url = f"{TIINGO_IEX_URL}/"
        params = {"tickers": ",".join(symbols)}
        
        try:
            start_time = datetime.now()
            async with self._session.get(url, params=params) as response:
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    data = await response.json()
                    
                    quotes = []
                    for item in data:
                        try:
                            quote = self._parse_iex_quote(item)
                            quotes.append(quote)
                        except Exception as e:
                            logger.warning(f"Failed to parse Tiingo quote: {e}")
                    
                    self._record_success(latency_ms)
                    return quotes
                    
                elif response.status == 429:
                    raise RateLimitError("tiingo", retry_after=60)
                else:
                    error_text = await response.text()
                    raise ProviderError("tiingo", f"API error {response.status}: {error_text}")
                    
        except aiohttp.ClientError as e:
            self._record_error(e)
            raise ProviderError("tiingo", f"Connection error: {e}")
    
    async def get_historical(
        self,
        symbol: str,
        start_date: date,
        end_date: Optional[date] = None,
        timeframe: TimeFrame = TimeFrame.DAY,
    ) -> list[OHLCV]:
        """Get historical end-of-day data."""
        symbol = symbol.upper()
        
        if end_date is None:
            end_date = date.today()
        
        # Tiingo only supports daily for free tier
        if timeframe not in [TimeFrame.DAY, TimeFrame.WEEK, TimeFrame.MONTH]:
            logger.warning(f"Tiingo: timeframe {timeframe} not supported, using daily")
        
        url = f"{TIINGO_BASE_URL}/tiingo/daily/{symbol}/prices"
        params = {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
        }
        
        try:
            start_time = datetime.now()
            async with self._session.get(url, params=params) as response:
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    data = await response.json()
                    
                    bars = []
                    for item in data:
                        try:
                            bar = self._parse_daily_bar(symbol, item)
                            bars.append(bar)
                        except Exception as e:
                            logger.warning(f"Failed to parse Tiingo bar: {e}")
                    
                    self._record_success(latency_ms)
                    bars.sort(key=lambda x: x.timestamp)
                    return bars
                    
                elif response.status == 429:
                    raise RateLimitError("tiingo", retry_after=60)
                elif response.status == 404:
                    return []
                else:
                    error_text = await response.text()
                    raise ProviderError("tiingo", f"API error {response.status}: {error_text}")
                    
        except aiohttp.ClientError as e:
            self._record_error(e)
            raise ProviderError("tiingo", f"Connection error: {e}")
    
    # ==================== Parsing Methods ====================
    
    def _parse_iex_quote(self, data: dict[str, Any]) -> Quote:
        """Parse IEX quote response."""
        symbol = data.get("ticker", "").upper()
        
        # Parse timestamp
        timestamp_str = data.get("timestamp")
        if timestamp_str:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        else:
            timestamp = datetime.now(timezone.utc)
        
        last = Decimal(str(data.get("last", 0) or data.get("tngoLast", 0) or 0))
        prev_close = Decimal(str(data.get("prevClose", 0) or 0))
        
        change = last - prev_close if prev_close else None
        change_pct = (change / prev_close * 100) if change and prev_close else None
        
        return Quote(
            symbol=symbol,
            price=last,
            bid=Decimal(str(data.get("bidPrice", 0))) if data.get("bidPrice") else None,
            ask=Decimal(str(data.get("askPrice", 0))) if data.get("askPrice") else None,
            bid_size=data.get("bidSize"),
            ask_size=data.get("askSize"),
            volume=int(data.get("volume", 0) or 0),
            timestamp=timestamp,
            provider="tiingo",
            market_type=MarketType.US_STOCK,
            change=change,
            change_percent=change_pct,
            day_high=Decimal(str(data.get("high", 0))) if data.get("high") else None,
            day_low=Decimal(str(data.get("low", 0))) if data.get("low") else None,
            day_open=Decimal(str(data.get("open", 0))) if data.get("open") else None,
            prev_close=prev_close if prev_close else None,
        )
    
    def _parse_daily_bar(self, symbol: str, data: dict[str, Any]) -> OHLCV:
        """Parse daily historical bar."""
        timestamp_str = data.get("date")
        if timestamp_str:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        else:
            timestamp = datetime.now(timezone.utc)
        
        return OHLCV(
            symbol=symbol,
            timestamp=timestamp,
            open=Decimal(str(data.get("open", 0))),
            high=Decimal(str(data.get("high", 0))),
            low=Decimal(str(data.get("low", 0))),
            close=Decimal(str(data.get("close", 0))),
            volume=int(data.get("volume", 0)),
            provider="tiingo",
            timeframe=TimeFrame.DAY,
            adjusted_close=Decimal(str(data.get("adjClose", 0))) if data.get("adjClose") else None,
        )
