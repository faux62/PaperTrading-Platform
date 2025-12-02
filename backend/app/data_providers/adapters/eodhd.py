"""
EODHD (End of Day Historical Data) Adapter

Provides access to EODHD API for global market data.
Supports bulk downloads and comprehensive historical data.

API Documentation: https://eodhistoricaldata.com/financial-apis/
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


EODHD_BASE_URL = "https://eodhistoricaldata.com/api"


def create_eodhd_config(api_key: str) -> ProviderConfig:
    """Create configuration for EODHD adapter."""
    return ProviderConfig(
        name="eodhd",
        api_key=api_key,
        base_url=EODHD_BASE_URL,
        requests_per_minute=1000,
        requests_per_day=100000,
        max_symbols_per_request=500,  # Bulk API
        cost_per_request=Decimal("0.001"),
        daily_budget=Decimal("100"),
        timeout_seconds=60.0,
        retry_attempts=3,
        retry_delay=1.0,
        supports_websocket=False,
        supports_batch=True,
        supports_historical=True,
        supported_markets=[
            MarketType.US_STOCK,
            MarketType.EU_STOCK,
            MarketType.ASIA_STOCK,
            MarketType.FOREX,
            MarketType.CRYPTO,
            MarketType.ETF,
            MarketType.INDEX,
        ],
        supported_data_types=[DataType.QUOTE, DataType.OHLCV],
        priority=25,
    )


class EODHDAdapter(BaseAdapter):
    """
    EODHD data provider adapter.
    
    Features:
    - Bulk historical data downloads
    - Global market coverage (70+ exchanges)
    - Fundamentals data
    - Splits and dividends
    - Real-time quotes (paid plans)
    
    Exchange codes:
    - US: AAPL.US, MSFT.US
    - London: BP.LSE
    - Frankfurt: SAP.XETRA
    - Milan: ENI.MI
    - Tokyo: 7203.TSE
    
    Usage:
        config = create_eodhd_config("your_api_key")
        adapter = EODHDAdapter(config)
        await adapter.initialize()
        
        quote = await adapter.get_quote("AAPL.US")
        bars = await adapter.get_historical("MSFT.US", start_date, end_date)
    """
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self) -> None:
        """Initialize HTTP session."""
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            self._session = aiohttp.ClientSession(timeout=timeout)
            logger.info("EODHD adapter initialized")
    
    async def close(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
        logger.info("EODHD adapter closed")
    
    async def health_check(self) -> bool:
        """Check API connectivity."""
        try:
            url = f"{EODHD_BASE_URL}/user"
            params = {"api_token": self.config.api_key, "fmt": "json"}
            
            async with self._session.get(url, params=params) as response:
                if response.status == 200:
                    return True
                elif response.status == 401:
                    logger.error("EODHD authentication failed")
                    return False
                return False
        except Exception as e:
            logger.error(f"EODHD health check failed: {e}")
            return False
    
    # ==================== Quote Methods ====================
    
    async def get_quote(self, symbol: str) -> Quote:
        """Get real-time quote for a symbol."""
        url = f"{EODHD_BASE_URL}/real-time/{symbol}"
        params = {
            "api_token": self.config.api_key,
            "fmt": "json",
        }
        
        try:
            start_time = datetime.now()
            async with self._session.get(url, params=params) as response:
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    data = await response.json()
                    
                    if not data or "code" not in data:
                        raise DataNotAvailableError("eodhd", symbol, "quote")
                    
                    quote = self._parse_quote(data)
                    self._record_success(latency_ms)
                    return quote
                    
                elif response.status == 401:
                    raise AuthenticationError("eodhd")
                elif response.status == 429:
                    raise RateLimitError("eodhd", retry_after=60)
                else:
                    raise ProviderError("eodhd", f"API error {response.status}")
                    
        except aiohttp.ClientError as e:
            self._record_error(e)
            raise ProviderError("eodhd", f"Connection error: {e}")
    
    async def get_quotes(self, symbols: list[str]) -> list[Quote]:
        """Get quotes for multiple symbols (bulk)."""
        if not symbols:
            return []
        
        # EODHD bulk endpoint
        url = f"{EODHD_BASE_URL}/real-time/{symbols[0].split('.')[1] if '.' in symbols[0] else 'US'}"
        params = {
            "api_token": self.config.api_key,
            "fmt": "json",
            "s": ",".join(symbols),
        }
        
        try:
            start_time = datetime.now()
            async with self._session.get(url, params=params) as response:
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    data = await response.json()
                    
                    quotes = []
                    items = data if isinstance(data, list) else [data]
                    
                    for item in items:
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
            raise ProviderError("eodhd", f"Connection error: {e}")
    
    # ==================== Historical Methods ====================
    
    async def get_historical(
        self,
        symbol: str,
        start_date: date,
        end_date: Optional[date] = None,
        timeframe: TimeFrame = TimeFrame.DAY,
    ) -> list[OHLCV]:
        """Get historical end-of-day data."""
        if end_date is None:
            end_date = date.today()
        
        # EODHD only supports daily historical
        if timeframe not in [TimeFrame.DAY, TimeFrame.WEEK, TimeFrame.MONTH]:
            logger.warning(f"EODHD: timeframe {timeframe} not supported, using daily")
        
        period_map = {
            TimeFrame.DAY: "d",
            TimeFrame.WEEK: "w",
            TimeFrame.MONTH: "m",
        }
        period = period_map.get(timeframe, "d")
        
        url = f"{EODHD_BASE_URL}/eod/{symbol}"
        params = {
            "api_token": self.config.api_key,
            "fmt": "json",
            "from": start_date.isoformat(),
            "to": end_date.isoformat(),
            "period": period,
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
                            bar = self._parse_bar(symbol, item, timeframe)
                            bars.append(bar)
                        except Exception as e:
                            logger.warning(f"Failed to parse bar: {e}")
                    
                    self._record_success(latency_ms)
                    bars.sort(key=lambda x: x.timestamp)
                    return bars
                    
                elif response.status == 429:
                    raise RateLimitError("eodhd", retry_after=60)
                else:
                    return []
                    
        except aiohttp.ClientError as e:
            self._record_error(e)
            raise ProviderError("eodhd", f"Connection error: {e}")
    
    async def search_symbols(self, query: str) -> list[dict[str, Any]]:
        """Search for symbols."""
        url = f"{EODHD_BASE_URL}/search/{query}"
        params = {
            "api_token": self.config.api_key,
        }
        
        try:
            async with self._session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    results = []
                    for item in data:
                        results.append({
                            "symbol": f"{item.get('Code')}.{item.get('Exchange')}",
                            "name": item.get("Name"),
                            "exchange": item.get("Exchange"),
                            "type": item.get("Type"),
                            "country": item.get("Country"),
                            "currency": item.get("Currency"),
                        })
                    
                    return results
                return []
        except Exception as e:
            logger.warning(f"Search failed: {e}")
            return []
    
    # ==================== Bulk Methods ====================
    
    async def get_bulk_eod(self, exchange: str = "US", date_: Optional[date] = None) -> list[OHLCV]:
        """
        Get bulk end-of-day data for entire exchange.
        
        Args:
            exchange: Exchange code (US, LSE, XETRA, etc.)
            date_: Date for EOD data (defaults to previous trading day)
        """
        if date_ is None:
            date_ = date.today()
        
        url = f"{EODHD_BASE_URL}/eod-bulk-last-day/{exchange}"
        params = {
            "api_token": self.config.api_key,
            "fmt": "json",
            "date": date_.isoformat(),
        }
        
        try:
            async with self._session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    bars = []
                    for item in data:
                        try:
                            symbol = f"{item.get('code')}.{exchange}"
                            bar = self._parse_bar(symbol, item, TimeFrame.DAY)
                            bars.append(bar)
                        except Exception:
                            pass
                    
                    return bars
                return []
        except Exception as e:
            logger.warning(f"Bulk EOD failed: {e}")
            return []
    
    # ==================== Parsing Methods ====================
    
    def _parse_quote(self, data: dict[str, Any]) -> Quote:
        """Parse quote response."""
        symbol = data.get("code", "")
        
        close = Decimal(str(data.get("close", 0) or 0))
        prev_close = Decimal(str(data.get("previousClose", 0) or 0))
        
        change = Decimal(str(data.get("change", 0) or 0))
        change_pct = Decimal(str(data.get("change_p", 0) or 0))
        
        timestamp = data.get("timestamp")
        if timestamp:
            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        else:
            dt = datetime.now(timezone.utc)
        
        market_type = self._determine_market_type(symbol)
        
        return Quote(
            symbol=symbol,
            price=close,
            bid=Decimal(str(data.get("bid", 0))) if data.get("bid") else None,
            ask=Decimal(str(data.get("ask", 0))) if data.get("ask") else None,
            bid_size=None,
            ask_size=None,
            volume=int(data.get("volume", 0) or 0),
            timestamp=dt,
            provider="eodhd",
            market_type=market_type,
            change=change,
            change_percent=change_pct,
            day_high=Decimal(str(data.get("high", 0))) if data.get("high") else None,
            day_low=Decimal(str(data.get("low", 0))) if data.get("low") else None,
            day_open=Decimal(str(data.get("open", 0))) if data.get("open") else None,
            prev_close=prev_close if prev_close else None,
        )
    
    def _parse_bar(self, symbol: str, data: dict[str, Any], timeframe: TimeFrame) -> OHLCV:
        """Parse historical bar."""
        date_str = data.get("date")
        if date_str:
            dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        else:
            dt = datetime.now(timezone.utc)
        
        return OHLCV(
            symbol=symbol,
            timestamp=dt,
            open=Decimal(str(data.get("open", 0) or 0)),
            high=Decimal(str(data.get("high", 0) or 0)),
            low=Decimal(str(data.get("low", 0) or 0)),
            close=Decimal(str(data.get("close", 0) or 0)),
            volume=int(data.get("volume", 0) or 0),
            provider="eodhd",
            timeframe=timeframe,
            adjusted_close=Decimal(str(data.get("adjusted_close", 0))) if data.get("adjusted_close") else None,
        )
    
    def _determine_market_type(self, symbol: str) -> MarketType:
        """Determine market type from symbol."""
        if "." in symbol:
            exchange = symbol.split(".")[-1].upper()
            us_exchanges = ["US", "NYSE", "NASDAQ"]
            eu_exchanges = ["LSE", "XETRA", "PA", "MI", "MC"]
            asia_exchanges = ["TSE", "HK", "SS", "SZ"]
            
            if exchange in us_exchanges:
                return MarketType.US_STOCK
            elif exchange in eu_exchanges:
                return MarketType.EU_STOCK
            elif exchange in asia_exchanges:
                return MarketType.ASIA_STOCK
            elif exchange == "CC":
                return MarketType.CRYPTO
            elif exchange == "FOREX":
                return MarketType.FOREX
        
        return MarketType.US_STOCK
