"""
Polygon.io Adapter

Provides access to Polygon.io market data API for US stocks.
Supports REST API with snapshot and historical endpoints.

API Documentation: https://polygon.io/docs
Free tier: 5 API calls/minute, end-of-day data
Basic tier: Unlimited calls, 15-min delayed data
"""
import asyncio
from datetime import datetime, date, timezone, timedelta
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


POLYGON_BASE_URL = "https://api.polygon.io"


def create_polygon_config(
    api_key: str,
    tier: str = "free",  # "free", "basic", "advanced"
) -> ProviderConfig:
    """Create configuration for Polygon adapter."""
    # Rate limits by tier
    rate_limits = {
        "free": 5,      # 5 calls/minute
        "basic": 0,     # Unlimited
        "advanced": 0,  # Unlimited
    }
    
    return ProviderConfig(
        name="polygon",
        api_key=api_key,
        base_url=POLYGON_BASE_URL,
        requests_per_minute=rate_limits.get(tier, 5),
        requests_per_day=0,
        max_symbols_per_request=50,  # Snapshot limit
        cost_per_request=Decimal("0"),
        daily_budget=Decimal("0"),
        timeout_seconds=30.0,
        retry_attempts=3,
        retry_delay=1.0,
        supports_websocket=False,  # WebSocket is paid only
        supports_batch=True,
        supports_historical=True,
        supported_markets=[MarketType.US_STOCK, MarketType.CRYPTO, MarketType.FOREX],
        supported_data_types=[DataType.QUOTE, DataType.OHLCV],
        priority=20,
    )


class PolygonAdapter(BaseAdapter):
    """
    Polygon.io data provider adapter.
    
    Features:
    - Real-time and delayed quotes
    - Snapshot endpoint for batch quotes
    - Historical aggregates (bars)
    - Multi-market support (stocks, crypto, forex)
    
    Usage:
        config = create_polygon_config("your_api_key")
        adapter = PolygonAdapter(config)
        await adapter.initialize()
        
        quote = await adapter.get_quote("AAPL")
        bars = await adapter.get_historical("AAPL", start_date, end_date)
    """
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self) -> None:
        """Initialize HTTP session."""
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            self._session = aiohttp.ClientSession(timeout=timeout)
            logger.info("Polygon adapter initialized")
    
    async def close(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
        logger.info("Polygon adapter closed")
    
    async def health_check(self) -> bool:
        """Check API connectivity."""
        try:
            url = f"{self.config.base_url}/v3/reference/tickers"
            params = {
                "apiKey": self.config.api_key,
                "limit": 1,
            }
            async with self._session.get(url, params=params) as response:
                if response.status == 200:
                    return True
                elif response.status == 401:
                    logger.error("Polygon authentication failed")
                    return False
                else:
                    logger.warning(f"Polygon health check status: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Polygon health check failed: {e}")
            return False
    
    # ==================== REST API Methods ====================
    
    async def get_quote(self, symbol: str) -> Quote:
        """Get latest quote for a symbol using previous close endpoint."""
        symbol = symbol.upper()
        
        # Use previous close for latest price (available on free tier)
        url = f"{self.config.base_url}/v2/aggs/ticker/{symbol}/prev"
        params = {"apiKey": self.config.api_key}
        
        try:
            start_time = datetime.now()
            async with self._session.get(url, params=params) as response:
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    data = await response.json()
                    results = data.get("results", [])
                    
                    if results:
                        quote = self._parse_agg_to_quote(symbol, results[0])
                        self._record_success(latency_ms)
                        return quote
                    else:
                        raise DataNotAvailableError("polygon", symbol, "quote")
                        
                elif response.status == 401:
                    raise AuthenticationError("polygon")
                elif response.status == 429:
                    raise RateLimitError("polygon", retry_after=60)
                elif response.status == 404:
                    raise DataNotAvailableError("polygon", symbol, "quote")
                else:
                    error_text = await response.text()
                    raise ProviderError("polygon", f"API error {response.status}: {error_text}")
                    
        except aiohttp.ClientError as e:
            self._record_error(e)
            raise ProviderError("polygon", f"Connection error: {e}")
    
    async def get_quotes(self, symbols: list[str]) -> list[Quote]:
        """Get quotes for multiple symbols using snapshot endpoint."""
        if not symbols:
            return []
        
        symbols = [s.upper() for s in symbols]
        
        # Polygon snapshot endpoint (requires paid tier for real-time)
        # For free tier, we'll fetch previous close for each
        url = f"{self.config.base_url}/v2/snapshot/locale/us/markets/stocks/tickers"
        params = {
            "apiKey": self.config.api_key,
            "tickers": ",".join(symbols),
        }
        
        try:
            start_time = datetime.now()
            async with self._session.get(url, params=params) as response:
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    data = await response.json()
                    tickers = data.get("tickers", [])
                    
                    quotes = []
                    for ticker_data in tickers:
                        try:
                            quote = self._parse_snapshot(ticker_data)
                            quotes.append(quote)
                        except Exception as e:
                            logger.warning(f"Failed to parse snapshot: {e}")
                    
                    self._record_success(latency_ms)
                    return quotes
                    
                elif response.status == 403:
                    # Snapshot might require paid tier, fallback to individual requests
                    logger.warning("Polygon snapshot requires paid tier, falling back to individual requests")
                    return await self._get_quotes_individual(symbols)
                    
                elif response.status == 429:
                    raise RateLimitError("polygon", retry_after=60)
                else:
                    error_text = await response.text()
                    raise ProviderError("polygon", f"API error {response.status}: {error_text}")
                    
        except aiohttp.ClientError as e:
            self._record_error(e)
            raise ProviderError("polygon", f"Connection error: {e}")
    
    async def _get_quotes_individual(self, symbols: list[str]) -> list[Quote]:
        """Fallback: get quotes one by one."""
        quotes = []
        for symbol in symbols:
            try:
                quote = await self.get_quote(symbol)
                quotes.append(quote)
            except Exception as e:
                logger.warning(f"Failed to get quote for {symbol}: {e}")
        return quotes
    
    async def get_historical(
        self,
        symbol: str,
        start_date: date,
        end_date: Optional[date] = None,
        timeframe: TimeFrame = TimeFrame.DAY,
    ) -> list[OHLCV]:
        """Get historical bar data (aggregates)."""
        symbol = symbol.upper()
        
        if end_date is None:
            end_date = date.today()
        
        # Convert timeframe to Polygon format
        tf_map = {
            TimeFrame.MINUTE_1: ("minute", 1),
            TimeFrame.MINUTE_5: ("minute", 5),
            TimeFrame.MINUTE_15: ("minute", 15),
            TimeFrame.MINUTE_30: ("minute", 30),
            TimeFrame.HOUR_1: ("hour", 1),
            TimeFrame.HOUR_4: ("hour", 4),
            TimeFrame.DAY: ("day", 1),
            TimeFrame.WEEK: ("week", 1),
            TimeFrame.MONTH: ("month", 1),
        }
        multiplier_unit = tf_map.get(timeframe, ("day", 1))
        
        url = (
            f"{self.config.base_url}/v2/aggs/ticker/{symbol}/range/"
            f"{multiplier_unit[1]}/{multiplier_unit[0]}/"
            f"{start_date.isoformat()}/{end_date.isoformat()}"
        )
        
        params = {
            "apiKey": self.config.api_key,
            "adjusted": "true",
            "sort": "asc",
            "limit": 50000,
        }
        
        all_bars: list[OHLCV] = []
        
        try:
            start_time = datetime.now()
            async with self._session.get(url, params=params) as response:
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    data = await response.json()
                    results = data.get("results", [])
                    
                    for bar in results:
                        try:
                            ohlcv = self._parse_aggregate(symbol, bar, timeframe)
                            all_bars.append(ohlcv)
                        except Exception as e:
                            logger.warning(f"Failed to parse bar for {symbol}: {e}")
                    
                    self._record_success(latency_ms)
                    
                elif response.status == 429:
                    raise RateLimitError("polygon", retry_after=60)
                else:
                    error_text = await response.text()
                    raise ProviderError("polygon", f"API error {response.status}: {error_text}")
            
            # Sort by timestamp
            all_bars.sort(key=lambda x: x.timestamp)
            return all_bars
            
        except aiohttp.ClientError as e:
            self._record_error(e)
            raise ProviderError("polygon", f"Connection error: {e}")
    
    # ==================== Parsing Methods ====================
    
    def _parse_agg_to_quote(self, symbol: str, data: dict[str, Any]) -> Quote:
        """Parse aggregate data as a quote (for previous close endpoint)."""
        # Timestamp is in milliseconds
        timestamp_ms = data.get("t", 0)
        timestamp = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
        
        close = Decimal(str(data.get("c", 0)))
        open_price = Decimal(str(data.get("o", 0)))
        prev_close = open_price  # Use open as prev close approximation
        
        change = close - prev_close if prev_close else None
        change_pct = (change / prev_close * 100) if change and prev_close else None
        
        return Quote(
            symbol=symbol,
            price=close,
            volume=int(data.get("v", 0)),
            timestamp=timestamp,
            provider="polygon",
            market_type=MarketType.US_STOCK,
            change=change,
            change_percent=change_pct,
            day_high=Decimal(str(data.get("h", 0))) if data.get("h") else None,
            day_low=Decimal(str(data.get("l", 0))) if data.get("l") else None,
            day_open=open_price if open_price else None,
            prev_close=prev_close if prev_close else None,
        )
    
    def _parse_snapshot(self, data: dict[str, Any]) -> Quote:
        """Parse snapshot ticker data."""
        ticker = data.get("ticker", "")
        day = data.get("day", {})
        prev_day = data.get("prevDay", {})
        last_quote = data.get("lastQuote", {})
        
        # Get price from various sources
        price = Decimal(str(day.get("c", 0)))
        if price == 0:
            price = Decimal(str(last_quote.get("p", 0)))
        
        prev_close = Decimal(str(prev_day.get("c", 0)))
        change = price - prev_close if prev_close else None
        change_pct = (change / prev_close * 100) if change and prev_close else None
        
        # Get timestamp
        timestamp_ms = data.get("updated", 0)
        if timestamp_ms:
            timestamp = datetime.fromtimestamp(timestamp_ms / 1_000_000_000, tz=timezone.utc)
        else:
            timestamp = datetime.now(timezone.utc)
        
        return Quote(
            symbol=ticker,
            price=price,
            bid=Decimal(str(last_quote.get("P", 0))) if last_quote.get("P") else None,
            ask=Decimal(str(last_quote.get("p", 0))) if last_quote.get("p") else None,
            bid_size=last_quote.get("S"),
            ask_size=last_quote.get("s"),
            volume=int(day.get("v", 0)),
            timestamp=timestamp,
            provider="polygon",
            market_type=MarketType.US_STOCK,
            change=change,
            change_percent=change_pct,
            day_high=Decimal(str(day.get("h", 0))) if day.get("h") else None,
            day_low=Decimal(str(day.get("l", 0))) if day.get("l") else None,
            day_open=Decimal(str(day.get("o", 0))) if day.get("o") else None,
            prev_close=prev_close if prev_close else None,
        )
    
    def _parse_aggregate(self, symbol: str, data: dict[str, Any], timeframe: TimeFrame) -> OHLCV:
        """Parse aggregate bar data."""
        # Timestamp is in milliseconds
        timestamp_ms = data.get("t", 0)
        timestamp = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
        
        return OHLCV(
            symbol=symbol,
            timestamp=timestamp,
            open=Decimal(str(data.get("o", 0))),
            high=Decimal(str(data.get("h", 0))),
            low=Decimal(str(data.get("l", 0))),
            close=Decimal(str(data.get("c", 0))),
            volume=int(data.get("v", 0)),
            provider="polygon",
            timeframe=timeframe,
            vwap=Decimal(str(data.get("vw", 0))) if data.get("vw") else None,
            trade_count=data.get("n"),
        )
