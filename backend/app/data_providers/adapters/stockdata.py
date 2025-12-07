"""
StockData.org Adapter

Provides access to StockData.org API for real-time market data.
Free tier: 100 requests/day.

API Documentation: https://www.stockdata.org/documentation
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


STOCKDATA_BASE_URL = "https://api.stockdata.org/v1"


def create_stockdata_config(api_key: str) -> ProviderConfig:
    """Create configuration for StockData.org adapter."""
    return ProviderConfig(
        name="stockdata",
        api_key=api_key,
        base_url=STOCKDATA_BASE_URL,
        requests_per_minute=10,
        requests_per_day=100,  # Free tier
        max_symbols_per_request=50,
        cost_per_request=Decimal("0"),
        daily_budget=Decimal("0"),
        timeout_seconds=30.0,
        retry_attempts=3,
        retry_delay=1.0,
        supports_websocket=False,
        supports_batch=True,
        supports_historical=True,
        supported_markets=[
            MarketType.US_STOCK,
            MarketType.EU_STOCK,
        ],
        supported_data_types=[DataType.QUOTE, DataType.OHLCV],
        priority=80,  # Lower priority due to limited free tier
    )


class StockDataAdapter(BaseAdapter):
    """
    StockData.org data provider adapter.
    
    Features:
    - Real-time stock quotes
    - Historical intraday data
    - News data
    - Batch requests
    
    Usage:
        config = create_stockdata_config("your_api_key")
        adapter = StockDataAdapter(config)
        await adapter.initialize()
        
        quote = await adapter.get_quote("AAPL")
        bars = await adapter.get_historical("MSFT", start_date, end_date)
    """
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self) -> None:
        """Initialize HTTP session."""
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            self._session = aiohttp.ClientSession(timeout=timeout)
            logger.info("StockData.org adapter initialized")
    
    async def close(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
        logger.info("StockData.org adapter closed")
    
    async def health_check(self) -> bool:
        """Check API connectivity."""
        try:
            url = f"{STOCKDATA_BASE_URL}/data/quote"
            params = {
                "api_token": self.config.api_key,
                "symbols": "AAPL",
            }
            
            async with self._session.get(url, params=params) as response:
                if response.status == 200:
                    return True
                elif response.status == 401:
                    logger.error("StockData.org authentication failed")
                    return False
                return False
        except Exception as e:
            logger.error(f"StockData.org health check failed: {e}")
            return False
    
    # ==================== Quote Methods ====================
    
    async def get_quote(self, symbol: str) -> Quote:
        """Get real-time quote for a symbol."""
        symbol = symbol.upper()
        url = f"{STOCKDATA_BASE_URL}/data/quote"
        params = {
            "api_token": self.config.api_key,
            "symbols": symbol,
        }
        
        try:
            start_time = datetime.now()
            async with self._session.get(url, params=params) as response:
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    data = await response.json()
                    
                    if "error" in data:
                        error = data["error"]
                        if "rate limit" in error.get("message", "").lower():
                            raise RateLimitError("stockdata", retry_after=60)
                        raise ProviderError("stockdata", error.get("message", "Unknown error"))
                    
                    quotes_data = data.get("data", [])
                    if not quotes_data:
                        raise DataNotAvailableError("stockdata", symbol, "quote")
                    
                    quote = self._parse_quote(quotes_data[0])
                    self._record_success(latency_ms)
                    return quote
                    
                elif response.status == 401:
                    raise AuthenticationError("stockdata")
                elif response.status == 429:
                    raise RateLimitError("stockdata", retry_after=60)
                else:
                    raise ProviderError("stockdata", f"API error {response.status}")
                    
        except aiohttp.ClientError as e:
            self._record_error(e)
            raise ProviderError("stockdata", f"Connection error: {e}")
    
    async def get_quotes(self, symbols: list[str]) -> list[Quote]:
        """Get quotes for multiple symbols."""
        if not symbols:
            return []
        
        symbols = [s.upper() for s in symbols]
        url = f"{STOCKDATA_BASE_URL}/data/quote"
        params = {
            "api_token": self.config.api_key,
            "symbols": ",".join(symbols),
        }
        
        try:
            start_time = datetime.now()
            async with self._session.get(url, params=params) as response:
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    data = await response.json()
                    
                    if "error" in data:
                        return []
                    
                    quotes = []
                    for item in data.get("data", []):
                        try:
                            quote = self._parse_quote(item)
                            quotes.append(quote)
                        except Exception as e:
                            logger.warning(f"Failed to parse quote: {e}")
                    
                    self._record_success(latency_ms)
                    return quotes
                    
                else:
                    return []
                    
        except aiohttp.ClientError as e:
            self._record_error(e)
            raise ProviderError("stockdata", f"Connection error: {e}")
    
    # ==================== Historical Methods ====================
    
    async def get_historical(
        self,
        symbol: str,
        start_date: date,
        end_date: Optional[date] = None,
        timeframe: TimeFrame = TimeFrame.DAY,
    ) -> list[OHLCV]:
        """Get historical intraday data."""
        symbol = symbol.upper()
        
        if end_date is None:
            end_date = date.today()
        
        # Map timeframe
        interval_map = {
            TimeFrame.MINUTE: "1",
            TimeFrame.FIVE_MIN: "5",
            TimeFrame.FIFTEEN_MIN: "15",
            TimeFrame.HOUR: "60",
            TimeFrame.DAY: "day",
        }
        interval = interval_map.get(timeframe, "day")
        
        url = f"{STOCKDATA_BASE_URL}/data/intraday"
        params = {
            "api_token": self.config.api_key,
            "symbols": symbol,
            "date_from": start_date.isoformat(),
            "date_to": end_date.isoformat(),
        }
        
        if interval != "day":
            params["interval"] = interval
        
        try:
            start_time = datetime.now()
            async with self._session.get(url, params=params) as response:
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    data = await response.json()
                    
                    if "error" in data:
                        return []
                    
                    bars = []
                    for item in data.get("data", []):
                        try:
                            bar = self._parse_bar(item, timeframe)
                            bars.append(bar)
                        except Exception as e:
                            logger.warning(f"Failed to parse bar: {e}")
                    
                    self._record_success(latency_ms)
                    bars.sort(key=lambda x: x.timestamp)
                    return bars
                    
                else:
                    return []
                    
        except aiohttp.ClientError as e:
            self._record_error(e)
            raise ProviderError("stockdata", f"Connection error: {e}")
    
    async def search_symbols(self, query: str) -> list[dict[str, Any]]:
        """Search for symbols."""
        url = f"{STOCKDATA_BASE_URL}/entity/search"
        params = {
            "api_token": self.config.api_key,
            "search": query,
        }
        
        try:
            async with self._session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if "error" in data:
                        return []
                    
                    results = []
                    for item in data.get("data", []):
                        results.append({
                            "symbol": item.get("symbol"),
                            "name": item.get("name"),
                            "exchange": item.get("exchange"),
                            "type": item.get("type"),
                            "country": item.get("country"),
                        })
                    
                    return results
                return []
        except Exception as e:
            logger.warning(f"Search failed: {e}")
            return []
    
    # ==================== News Methods ====================
    
    async def get_news(
        self,
        symbols: Optional[list[str]] = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get market news."""
        url = f"{STOCKDATA_BASE_URL}/news/all"
        params = {
            "api_token": self.config.api_key,
            "limit": limit,
        }
        
        if symbols:
            params["symbols"] = ",".join([s.upper() for s in symbols])
        
        try:
            async with self._session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if "error" in data:
                        return []
                    
                    news = []
                    for item in data.get("data", []):
                        news.append({
                            "title": item.get("title"),
                            "description": item.get("description"),
                            "url": item.get("url"),
                            "source": item.get("source"),
                            "published_at": item.get("published_at"),
                            "symbols": item.get("symbols", []),
                        })
                    
                    return news
                return []
        except Exception as e:
            logger.warning(f"Failed to get news: {e}")
            return []
    
    # ==================== Parsing Methods ====================
    
    def _parse_quote(self, data: dict[str, Any]) -> Quote:
        """Parse quote response."""
        symbol = data.get("ticker", "").upper()
        
        price = Decimal(str(data.get("price", 0) or 0))
        change = Decimal(str(data.get("day_change", 0) or 0))
        change_pct = Decimal(str(data.get("change_percent", 0) or 0))
        
        return Quote(
            symbol=symbol,
            price=price,
            bid=None,
            ask=None,
            bid_size=None,
            ask_size=None,
            volume=int(data.get("volume", 0) or 0),
            timestamp=datetime.now(timezone.utc),
            provider="stockdata",
            market_type=MarketType.US_STOCK,
            change=change,
            change_percent=change_pct,
            day_high=Decimal(str(data.get("day_high", 0))) if data.get("day_high") else None,
            day_low=Decimal(str(data.get("day_low", 0))) if data.get("day_low") else None,
            day_open=Decimal(str(data.get("day_open", 0))) if data.get("day_open") else None,
            prev_close=Decimal(str(data.get("previous_close_price", 0))) if data.get("previous_close_price") else None,
        )
    
    def _parse_bar(self, data: dict[str, Any], timeframe: TimeFrame) -> OHLCV:
        """Parse historical bar."""
        symbol = data.get("ticker", "").upper()
        
        date_str = data.get("date")
        if date_str:
            try:
                timestamp = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except ValueError:
                timestamp = datetime.now(timezone.utc)
        else:
            timestamp = datetime.now(timezone.utc)
        
        return OHLCV(
            symbol=symbol,
            timestamp=timestamp,
            open=Decimal(str(data.get("open", 0) or 0)),
            high=Decimal(str(data.get("high", 0) or 0)),
            low=Decimal(str(data.get("low", 0) or 0)),
            close=Decimal(str(data.get("close", 0) or 0)),
            volume=int(data.get("volume", 0) or 0),
            provider="stockdata",
            timeframe=timeframe,
        )
