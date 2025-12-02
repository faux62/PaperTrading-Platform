"""
Twelve Data Adapter

Provides access to Twelve Data API for global market data.
Supports batch requests up to 120 symbols.

API Documentation: https://twelvedata.com/docs
Free tier: 800 API credits/day, 8 requests/minute
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


TWELVE_DATA_BASE_URL = "https://api.twelvedata.com"


def create_twelve_data_config(api_key: str) -> ProviderConfig:
    """Create configuration for Twelve Data adapter."""
    return ProviderConfig(
        name="twelve_data",
        api_key=api_key,
        base_url=TWELVE_DATA_BASE_URL,
        requests_per_minute=8,  # Free tier
        requests_per_day=800,  # Credits per day
        max_symbols_per_request=120,  # Batch limit
        cost_per_request=Decimal("1"),  # 1 credit per call
        daily_budget=Decimal("800"),
        timeout_seconds=30.0,
        retry_attempts=3,
        retry_delay=1.0,
        supports_websocket=True,
        supports_batch=True,
        supports_historical=True,
        supported_markets=[
            MarketType.US_STOCK,
            MarketType.EU_STOCK,
            MarketType.ASIA_STOCK,
            MarketType.FOREX,
            MarketType.CRYPTO,
        ],
        supported_data_types=[DataType.QUOTE, DataType.OHLCV],
        priority=15,  # High priority for global coverage
    )


class TwelveDataAdapter(BaseAdapter):
    """
    Twelve Data provider adapter.
    
    Features:
    - Batch quotes up to 120 symbols
    - Historical data (intraday + daily)
    - Real-time WebSocket (paid plans)
    - Global market coverage
    - Forex and crypto support
    
    Usage:
        config = create_twelve_data_config("your_api_key")
        adapter = TwelveDataAdapter(config)
        await adapter.initialize()
        
        quote = await adapter.get_quote("AAPL")
        quotes = await adapter.get_quotes(["AAPL", "MSFT", "GOOGL"])
    """
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self) -> None:
        """Initialize HTTP session."""
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            self._session = aiohttp.ClientSession(timeout=timeout)
            logger.info("Twelve Data adapter initialized")
    
    async def close(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
        logger.info("Twelve Data adapter closed")
    
    async def health_check(self) -> bool:
        """Check API connectivity."""
        try:
            url = f"{TWELVE_DATA_BASE_URL}/api_usage"
            params = {"apikey": self.config.api_key}
            
            async with self._session.get(url, params=params) as response:
                if response.status == 200:
                    return True
                elif response.status == 401:
                    logger.error("Twelve Data authentication failed")
                    return False
                else:
                    return False
        except Exception as e:
            logger.error(f"Twelve Data health check failed: {e}")
            return False
    
    # ==================== REST API Methods ====================
    
    async def get_quote(self, symbol: str) -> Quote:
        """Get latest quote for a symbol."""
        symbol = symbol.upper()
        url = f"{TWELVE_DATA_BASE_URL}/quote"
        params = {
            "symbol": symbol,
            "apikey": self.config.api_key,
        }
        
        try:
            start_time = datetime.now()
            async with self._session.get(url, params=params) as response:
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    data = await response.json()
                    
                    if "code" in data:  # Error response
                        if data.get("code") == 429:
                            raise RateLimitError("twelve_data", retry_after=60)
                        elif data.get("code") == 401:
                            raise AuthenticationError("twelve_data")
                        else:
                            raise ProviderError("twelve_data", data.get("message", "Unknown error"))
                    
                    quote = self._parse_quote(data)
                    self._record_success(latency_ms)
                    return quote
                    
                elif response.status == 429:
                    raise RateLimitError("twelve_data", retry_after=60)
                else:
                    error_text = await response.text()
                    raise ProviderError("twelve_data", f"API error {response.status}: {error_text}")
                    
        except aiohttp.ClientError as e:
            self._record_error(e)
            raise ProviderError("twelve_data", f"Connection error: {e}")
    
    async def get_quotes(self, symbols: list[str]) -> list[Quote]:
        """Get quotes for multiple symbols (batch up to 120)."""
        if not symbols:
            return []
        
        # Process in batches of 120
        all_quotes = []
        batch_size = self.config.max_symbols_per_request
        
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            batch_quotes = await self._get_batch_quotes(batch)
            all_quotes.extend(batch_quotes)
        
        return all_quotes
    
    async def _get_batch_quotes(self, symbols: list[str]) -> list[Quote]:
        """Get batch quotes for up to 120 symbols."""
        symbols = [s.upper() for s in symbols]
        url = f"{TWELVE_DATA_BASE_URL}/quote"
        params = {
            "symbol": ",".join(symbols),
            "apikey": self.config.api_key,
        }
        
        try:
            start_time = datetime.now()
            async with self._session.get(url, params=params) as response:
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    data = await response.json()
                    
                    quotes = []
                    
                    # Single symbol returns object, multiple returns dict with symbol keys
                    if isinstance(data, dict) and "symbol" in data:
                        # Single symbol response
                        if "code" not in data:
                            quotes.append(self._parse_quote(data))
                    elif isinstance(data, dict):
                        # Multiple symbols response
                        for symbol, quote_data in data.items():
                            if isinstance(quote_data, dict) and "code" not in quote_data:
                                try:
                                    quotes.append(self._parse_quote(quote_data))
                                except Exception as e:
                                    logger.warning(f"Failed to parse quote for {symbol}: {e}")
                    
                    self._record_success(latency_ms)
                    return quotes
                    
                elif response.status == 429:
                    raise RateLimitError("twelve_data", retry_after=60)
                else:
                    return []
                    
        except aiohttp.ClientError as e:
            self._record_error(e)
            raise ProviderError("twelve_data", f"Connection error: {e}")
    
    async def get_historical(
        self,
        symbol: str,
        start_date: date,
        end_date: Optional[date] = None,
        timeframe: TimeFrame = TimeFrame.DAY,
    ) -> list[OHLCV]:
        """Get historical data for a symbol."""
        symbol = symbol.upper()
        
        if end_date is None:
            end_date = date.today()
        
        # Map timeframe to Twelve Data interval
        interval_map = {
            TimeFrame.MINUTE: "1min",
            TimeFrame.FIVE_MIN: "5min",
            TimeFrame.FIFTEEN_MIN: "15min",
            TimeFrame.HOUR: "1h",
            TimeFrame.DAY: "1day",
            TimeFrame.WEEK: "1week",
            TimeFrame.MONTH: "1month",
        }
        
        interval = interval_map.get(timeframe, "1day")
        
        url = f"{TWELVE_DATA_BASE_URL}/time_series"
        params = {
            "symbol": symbol,
            "interval": interval,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "apikey": self.config.api_key,
            "outputsize": 5000,  # Max output
        }
        
        try:
            start_time = datetime.now()
            async with self._session.get(url, params=params) as response:
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    data = await response.json()
                    
                    if "code" in data:
                        if data.get("code") == 429:
                            raise RateLimitError("twelve_data", retry_after=60)
                        else:
                            raise ProviderError("twelve_data", data.get("message", "Unknown error"))
                    
                    bars = []
                    values = data.get("values", [])
                    
                    for item in values:
                        try:
                            bar = self._parse_bar(symbol, item, timeframe)
                            bars.append(bar)
                        except Exception as e:
                            logger.warning(f"Failed to parse bar: {e}")
                    
                    self._record_success(latency_ms)
                    bars.sort(key=lambda x: x.timestamp)
                    return bars
                    
                elif response.status == 429:
                    raise RateLimitError("twelve_data", retry_after=60)
                else:
                    return []
                    
        except aiohttp.ClientError as e:
            self._record_error(e)
            raise ProviderError("twelve_data", f"Connection error: {e}")
    
    async def search_symbols(self, query: str) -> list[dict[str, Any]]:
        """Search for symbols by name or ticker."""
        url = f"{TWELVE_DATA_BASE_URL}/symbol_search"
        params = {
            "symbol": query,
            "apikey": self.config.api_key,
        }
        
        try:
            async with self._session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    results = []
                    for item in data.get("data", []):
                        results.append({
                            "symbol": item.get("symbol"),
                            "name": item.get("instrument_name"),
                            "exchange": item.get("exchange"),
                            "type": item.get("instrument_type"),
                            "country": item.get("country"),
                            "currency": item.get("currency"),
                        })
                    
                    return results
                else:
                    return []
                    
        except Exception as e:
            logger.warning(f"Symbol search failed: {e}")
            return []
    
    # ==================== Forex Methods ====================
    
    async def get_forex_quote(self, pair: str) -> Quote:
        """Get forex pair quote (e.g., EUR/USD)."""
        url = f"{TWELVE_DATA_BASE_URL}/exchange_rate"
        params = {
            "symbol": pair,
            "apikey": self.config.api_key,
        }
        
        try:
            async with self._session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if "code" in data:
                        raise ProviderError("twelve_data", data.get("message", "Unknown error"))
                    
                    rate = Decimal(str(data.get("rate", 0)))
                    
                    return Quote(
                        symbol=pair,
                        price=rate,
                        bid=None,
                        ask=None,
                        bid_size=None,
                        ask_size=None,
                        volume=0,
                        timestamp=datetime.now(timezone.utc),
                        provider="twelve_data",
                        market_type=MarketType.FOREX,
                    )
                else:
                    raise DataNotAvailableError("twelve_data", pair, "forex_quote")
                    
        except aiohttp.ClientError as e:
            raise ProviderError("twelve_data", f"Connection error: {e}")
    
    # ==================== Parsing Methods ====================
    
    def _parse_quote(self, data: dict[str, Any]) -> Quote:
        """Parse quote response."""
        symbol = data.get("symbol", "").upper()
        
        close = Decimal(str(data.get("close", 0) or 0))
        open_price = Decimal(str(data.get("open", 0) or 0))
        prev_close = Decimal(str(data.get("previous_close", 0) or 0))
        
        change = Decimal(str(data.get("change", 0) or 0))
        change_pct = Decimal(str(data.get("percent_change", 0) or 0))
        
        # Parse timestamp
        timestamp_str = data.get("datetime")
        if timestamp_str:
            try:
                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            except ValueError:
                try:
                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d")
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                except ValueError:
                    timestamp = datetime.now(timezone.utc)
        else:
            timestamp = datetime.now(timezone.utc)
        
        # Determine market type from exchange
        exchange = data.get("exchange", "").upper()
        market_type = self._get_market_type(exchange)
        
        return Quote(
            symbol=symbol,
            price=close,
            bid=None,
            ask=None,
            bid_size=None,
            ask_size=None,
            volume=int(data.get("volume", 0) or 0),
            timestamp=timestamp,
            provider="twelve_data",
            market_type=market_type,
            change=change,
            change_percent=change_pct,
            day_high=Decimal(str(data.get("high", 0))) if data.get("high") else None,
            day_low=Decimal(str(data.get("low", 0))) if data.get("low") else None,
            day_open=open_price if open_price else None,
            prev_close=prev_close if prev_close else None,
            fifty_two_week_high=Decimal(str(data.get("fifty_two_week", {}).get("high", 0))) if data.get("fifty_two_week", {}).get("high") else None,
            fifty_two_week_low=Decimal(str(data.get("fifty_two_week", {}).get("low", 0))) if data.get("fifty_two_week", {}).get("low") else None,
        )
    
    def _parse_bar(self, symbol: str, data: dict[str, Any], timeframe: TimeFrame) -> OHLCV:
        """Parse historical bar."""
        timestamp_str = data.get("datetime")
        if timestamp_str:
            try:
                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d")
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        else:
            timestamp = datetime.now(timezone.utc)
        
        return OHLCV(
            symbol=symbol,
            timestamp=timestamp,
            open=Decimal(str(data.get("open", 0))),
            high=Decimal(str(data.get("high", 0))),
            low=Decimal(str(data.get("low", 0))),
            close=Decimal(str(data.get("close", 0))),
            volume=int(data.get("volume", 0) or 0),
            provider="twelve_data",
            timeframe=timeframe,
        )
    
    def _get_market_type(self, exchange: str) -> MarketType:
        """Determine market type from exchange."""
        us_exchanges = ["NYSE", "NASDAQ", "AMEX", "BATS", "ARCA"]
        eu_exchanges = ["LSE", "XETRA", "EURONEXT", "SIX", "BME", "BIT"]
        asia_exchanges = ["TSE", "HKEX", "SSE", "SZSE", "NSE", "BSE", "KRX"]
        
        if exchange in us_exchanges:
            return MarketType.US_STOCK
        elif exchange in eu_exchanges:
            return MarketType.EU_STOCK
        elif exchange in asia_exchanges:
            return MarketType.ASIA_STOCK
        else:
            return MarketType.US_STOCK  # Default
