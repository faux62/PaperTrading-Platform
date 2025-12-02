"""
Marketstack Adapter

Provides access to Marketstack API for global market data.
Free tier: 100 requests/month.

API Documentation: https://marketstack.com/documentation
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


MARKETSTACK_BASE_URL = "http://api.marketstack.com/v1"  # Note: HTTPS requires paid plan


def create_marketstack_config(api_key: str) -> ProviderConfig:
    """Create configuration for Marketstack adapter."""
    return ProviderConfig(
        name="marketstack",
        api_key=api_key,
        base_url=MARKETSTACK_BASE_URL,
        requests_per_minute=10,
        requests_per_day=100,  # Free tier monthly limit used as daily
        max_symbols_per_request=100,
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
            MarketType.ASIA_STOCK,
        ],
        supported_data_types=[DataType.QUOTE, DataType.OHLCV],
        priority=75,  # Lower priority due to limited free tier
    )


class MarketstackAdapter(BaseAdapter):
    """
    Marketstack data provider adapter.
    
    Features:
    - End-of-day data
    - Intraday data (paid)
    - 70+ global stock exchanges
    - Batch requests
    
    Usage:
        config = create_marketstack_config("your_api_key")
        adapter = MarketstackAdapter(config)
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
            logger.info("Marketstack adapter initialized")
    
    async def close(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
        logger.info("Marketstack adapter closed")
    
    async def health_check(self) -> bool:
        """Check API connectivity."""
        try:
            url = f"{MARKETSTACK_BASE_URL}/tickers"
            params = {
                "access_key": self.config.api_key,
                "limit": 1,
            }
            
            async with self._session.get(url, params=params) as response:
                if response.status == 200:
                    return True
                elif response.status == 401:
                    logger.error("Marketstack authentication failed")
                    return False
                return False
        except Exception as e:
            logger.error(f"Marketstack health check failed: {e}")
            return False
    
    # ==================== Quote Methods ====================
    
    async def get_quote(self, symbol: str) -> Quote:
        """Get latest end-of-day data as quote."""
        symbol = symbol.upper()
        url = f"{MARKETSTACK_BASE_URL}/eod/latest"
        params = {
            "access_key": self.config.api_key,
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
                        if error.get("code") == "validation_error":
                            raise DataNotAvailableError("marketstack", symbol, "quote")
                        elif error.get("code") == "usage_limit_reached":
                            raise RateLimitError("marketstack", retry_after=86400)
                        raise ProviderError("marketstack", error.get("message", "Unknown error"))
                    
                    eod_data = data.get("data", [])
                    if not eod_data:
                        raise DataNotAvailableError("marketstack", symbol, "quote")
                    
                    quote = self._parse_eod_quote(eod_data[0])
                    self._record_success(latency_ms)
                    return quote
                    
                elif response.status == 401:
                    raise AuthenticationError("marketstack")
                else:
                    raise ProviderError("marketstack", f"API error {response.status}")
                    
        except aiohttp.ClientError as e:
            self._record_error(e)
            raise ProviderError("marketstack", f"Connection error: {e}")
    
    async def get_quotes(self, symbols: list[str]) -> list[Quote]:
        """Get quotes for multiple symbols."""
        if not symbols:
            return []
        
        symbols = [s.upper() for s in symbols]
        url = f"{MARKETSTACK_BASE_URL}/eod/latest"
        params = {
            "access_key": self.config.api_key,
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
                            quote = self._parse_eod_quote(item)
                            quotes.append(quote)
                        except Exception as e:
                            logger.warning(f"Failed to parse quote: {e}")
                    
                    self._record_success(latency_ms)
                    return quotes
                    
                else:
                    return []
                    
        except aiohttp.ClientError as e:
            self._record_error(e)
            raise ProviderError("marketstack", f"Connection error: {e}")
    
    # ==================== Historical Methods ====================
    
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
        
        # Marketstack free tier only supports daily
        if timeframe != TimeFrame.DAY:
            logger.warning("Marketstack free tier only supports daily data")
        
        url = f"{MARKETSTACK_BASE_URL}/eod"
        params = {
            "access_key": self.config.api_key,
            "symbols": symbol,
            "date_from": start_date.isoformat(),
            "date_to": end_date.isoformat(),
            "limit": 1000,
        }
        
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
            raise ProviderError("marketstack", f"Connection error: {e}")
    
    async def search_symbols(self, query: str) -> list[dict[str, Any]]:
        """Search for symbols."""
        url = f"{MARKETSTACK_BASE_URL}/tickers"
        params = {
            "access_key": self.config.api_key,
            "search": query,
            "limit": 20,
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
                            "exchange": item.get("stock_exchange", {}).get("name"),
                            "mic": item.get("stock_exchange", {}).get("mic"),
                            "country": item.get("stock_exchange", {}).get("country"),
                        })
                    
                    return results
                return []
        except Exception as e:
            logger.warning(f"Search failed: {e}")
            return []
    
    # ==================== Exchange Methods ====================
    
    async def get_exchanges(self) -> list[dict[str, Any]]:
        """Get list of supported exchanges."""
        url = f"{MARKETSTACK_BASE_URL}/exchanges"
        params = {
            "access_key": self.config.api_key,
        }
        
        try:
            async with self._session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    exchanges = []
                    for item in data.get("data", []):
                        exchanges.append({
                            "name": item.get("name"),
                            "mic": item.get("mic"),
                            "acronym": item.get("acronym"),
                            "country": item.get("country"),
                            "city": item.get("city"),
                            "timezone": item.get("timezone", {}).get("timezone"),
                        })
                    
                    return exchanges
                return []
        except Exception as e:
            logger.warning(f"Failed to get exchanges: {e}")
            return []
    
    # ==================== Parsing Methods ====================
    
    def _parse_eod_quote(self, data: dict[str, Any]) -> Quote:
        """Parse EOD data as quote."""
        symbol = data.get("symbol", "").upper()
        
        close = Decimal(str(data.get("close", 0) or 0))
        open_price = Decimal(str(data.get("open", 0) or 0))
        
        change = close - open_price if open_price else None
        change_pct = (change / open_price * 100) if change and open_price else None
        
        date_str = data.get("date")
        if date_str:
            try:
                timestamp = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except ValueError:
                timestamp = datetime.now(timezone.utc)
        else:
            timestamp = datetime.now(timezone.utc)
        
        exchange = data.get("exchange", "")
        market_type = self._determine_market_type(exchange)
        
        return Quote(
            symbol=symbol,
            price=close,
            bid=None,
            ask=None,
            bid_size=None,
            ask_size=None,
            volume=int(data.get("volume", 0) or 0),
            timestamp=timestamp,
            provider="marketstack",
            market_type=market_type,
            change=change,
            change_percent=change_pct,
            day_high=Decimal(str(data.get("high", 0))) if data.get("high") else None,
            day_low=Decimal(str(data.get("low", 0))) if data.get("low") else None,
            day_open=open_price if open_price else None,
        )
    
    def _parse_bar(self, data: dict[str, Any], timeframe: TimeFrame) -> OHLCV:
        """Parse historical bar."""
        symbol = data.get("symbol", "").upper()
        
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
            provider="marketstack",
            timeframe=timeframe,
            adjusted_close=Decimal(str(data.get("adj_close", 0))) if data.get("adj_close") else None,
        )
    
    def _determine_market_type(self, exchange: str) -> MarketType:
        """Determine market type from exchange."""
        us_exchanges = ["XNYS", "XNAS", "XASE", "NYSE", "NASDAQ"]
        eu_exchanges = ["XLON", "XETR", "XPAR", "XMIL", "XMAD", "LSE"]
        asia_exchanges = ["XTKS", "XHKG", "XSHG", "XSHE"]
        
        if exchange in us_exchanges:
            return MarketType.US_STOCK
        elif exchange in eu_exchanges:
            return MarketType.EU_STOCK
        elif exchange in asia_exchanges:
            return MarketType.ASIA_STOCK
        
        return MarketType.US_STOCK
