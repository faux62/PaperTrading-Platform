"""
Financial Modeling Prep (FMP) Adapter

Provides access to FMP API for financial data.
Comprehensive coverage of stocks, fundamentals, and market data.

API Documentation: https://site.financialmodelingprep.com/developer/docs
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


FMP_BASE_URL = "https://financialmodelingprep.com/api/v3"
FMP_STABLE_URL = "https://financialmodelingprep.com/stable"


def create_fmp_config(api_key: str) -> ProviderConfig:
    """Create configuration for FMP adapter."""
    return ProviderConfig(
        name="fmp",
        api_key=api_key,
        base_url=FMP_BASE_URL,
        requests_per_minute=300,
        requests_per_day=250,  # Free tier
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
            MarketType.ASIA_STOCK,
            MarketType.FOREX,
            MarketType.CRYPTO,
            MarketType.ETF,
        ],
        supported_data_types=[DataType.QUOTE, DataType.OHLCV],
        priority=35,
    )


class FMPAdapter(BaseAdapter):
    """
    Financial Modeling Prep data provider adapter.
    
    Features:
    - Real-time and historical quotes
    - Comprehensive fundamentals
    - Financial statements
    - Company profiles
    - Batch requests
    
    Usage:
        config = create_fmp_config("your_api_key")
        adapter = FMPAdapter(config)
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
            logger.info("FMP adapter initialized")
    
    async def close(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
        logger.info("FMP adapter closed")
    
    async def health_check(self) -> bool:
        """Check API connectivity."""
        try:
            url = f"{FMP_STABLE_URL}/quote"
            params = {"symbol": "AAPL", "apikey": self.config.api_key}
            
            async with self._session.get(url, params=params) as response:
                if response.status == 200:
                    return True
                elif response.status == 401:
                    logger.error("FMP authentication failed")
                    return False
                return False
        except Exception as e:
            logger.error(f"FMP health check failed: {e}")
            return False
    
    # ==================== Quote Methods ====================
    
    async def get_quote(self, symbol: str) -> Quote:
        """Get real-time quote for a symbol."""
        symbol = symbol.upper()
        url = f"{FMP_STABLE_URL}/quote"
        params = {"symbol": symbol, "apikey": self.config.api_key}
        
        try:
            start_time = datetime.now()
            async with self._session.get(url, params=params) as response:
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    data = await response.json()
                    
                    if not data or len(data) == 0:
                        raise DataNotAvailableError("fmp", symbol, "quote")
                    
                    quote = self._parse_quote(data[0])
                    self._record_success(latency_ms)
                    return quote
                    
                elif response.status == 401:
                    raise AuthenticationError("fmp")
                elif response.status == 429:
                    raise RateLimitError("fmp", retry_after=60)
                else:
                    raise ProviderError("fmp", f"API error {response.status}")
                    
        except aiohttp.ClientError as e:
            self._record_error(e)
            raise ProviderError("fmp", f"Connection error: {e}")
    
    async def get_quotes(self, symbols: list[str]) -> list[Quote]:
        """Get quotes for multiple symbols."""
        if not symbols:
            return []
        
        symbols = [s.upper() for s in symbols]
        url = f"{FMP_STABLE_URL}/quote"
        params = {"symbol": ",".join(symbols), "apikey": self.config.api_key}
        
        try:
            start_time = datetime.now()
            async with self._session.get(url, params=params) as response:
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    data = await response.json()
                    
                    quotes = []
                    for item in data:
                        try:
                            quote = self._parse_quote(item)
                            quotes.append(quote)
                        except Exception as e:
                            logger.warning(f"Failed to parse quote: {e}")
                    
                    self._record_success(latency_ms)
                    return quotes
                    
                elif response.status == 429:
                    raise RateLimitError("fmp", retry_after=60)
                else:
                    return []
                    
        except aiohttp.ClientError as e:
            self._record_error(e)
            raise ProviderError("fmp", f"Connection error: {e}")
    
    # ==================== Historical Methods ====================
    
    async def get_historical(
        self,
        symbol: str,
        start_date: date,
        end_date: Optional[date] = None,
        timeframe: TimeFrame = TimeFrame.DAY,
    ) -> list[OHLCV]:
        """Get historical data."""
        symbol = symbol.upper()
        
        if end_date is None:
            end_date = date.today()
        
        # Map timeframe to FMP endpoint
        if timeframe == TimeFrame.DAY:
            url = f"{FMP_BASE_URL}/historical-price-full/{symbol}"
        elif timeframe in [TimeFrame.MINUTE, TimeFrame.FIVE_MIN, TimeFrame.FIFTEEN_MIN, TimeFrame.HOUR]:
            interval_map = {
                TimeFrame.MINUTE: "1min",
                TimeFrame.FIVE_MIN: "5min",
                TimeFrame.FIFTEEN_MIN: "15min",
                TimeFrame.HOUR: "1hour",
            }
            interval = interval_map.get(timeframe, "1hour")
            url = f"{FMP_BASE_URL}/historical-chart/{interval}/{symbol}"
        else:
            url = f"{FMP_BASE_URL}/historical-price-full/{symbol}"
        
        params = {
            "apikey": self.config.api_key,
            "from": start_date.isoformat(),
            "to": end_date.isoformat(),
        }
        
        try:
            start_time = datetime.now()
            async with self._session.get(url, params=params) as response:
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    data = await response.json()
                    
                    bars = []
                    
                    # Daily data has different structure
                    if timeframe == TimeFrame.DAY:
                        historical = data.get("historical", [])
                    else:
                        historical = data if isinstance(data, list) else []
                    
                    for item in historical:
                        try:
                            bar = self._parse_bar(symbol, item, timeframe)
                            bars.append(bar)
                        except Exception as e:
                            logger.warning(f"Failed to parse bar: {e}")
                    
                    self._record_success(latency_ms)
                    bars.sort(key=lambda x: x.timestamp)
                    return bars
                    
                elif response.status == 429:
                    raise RateLimitError("fmp", retry_after=60)
                else:
                    return []
                    
        except aiohttp.ClientError as e:
            self._record_error(e)
            raise ProviderError("fmp", f"Connection error: {e}")
    
    async def search_symbols(self, query: str) -> list[dict[str, Any]]:
        """Search for symbols."""
        url = f"{FMP_BASE_URL}/search"
        params = {
            "apikey": self.config.api_key,
            "query": query,
            "limit": 20,
        }
        
        try:
            async with self._session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    results = []
                    for item in data:
                        results.append({
                            "symbol": item.get("symbol"),
                            "name": item.get("name"),
                            "exchange": item.get("stockExchange"),
                            "type": item.get("type"),
                            "currency": item.get("currency"),
                        })
                    
                    return results
                return []
        except Exception as e:
            logger.warning(f"Search failed: {e}")
            return []
    
    # ==================== Company Info ====================
    
    async def get_company_profile(self, symbol: str) -> Optional[dict[str, Any]]:
        """Get company profile."""
        url = f"{FMP_BASE_URL}/profile/{symbol.upper()}"
        params = {"apikey": self.config.api_key}
        
        try:
            async with self._session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data and len(data) > 0:
                        profile = data[0]
                        return {
                            "symbol": profile.get("symbol"),
                            "name": profile.get("companyName"),
                            "sector": profile.get("sector"),
                            "industry": profile.get("industry"),
                            "description": profile.get("description"),
                            "ceo": profile.get("ceo"),
                            "website": profile.get("website"),
                            "employees": profile.get("fullTimeEmployees"),
                            "country": profile.get("country"),
                            "city": profile.get("city"),
                            "address": profile.get("address"),
                            "market_cap": profile.get("mktCap"),
                            "beta": profile.get("beta"),
                            "exchange": profile.get("exchange"),
                            "currency": profile.get("currency"),
                        }
                return None
        except Exception as e:
            logger.warning(f"Failed to get profile: {e}")
            return None
    
    # ==================== Parsing Methods ====================
    
    def _parse_quote(self, data: dict[str, Any]) -> Quote:
        """Parse quote response."""
        symbol = data.get("symbol", "").upper()
        
        price = Decimal(str(data.get("price", 0) or 0))
        change = Decimal(str(data.get("change", 0) or 0))
        change_pct = Decimal(str(data.get("changesPercentage", 0) or 0))
        
        timestamp = data.get("timestamp")
        if timestamp:
            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        else:
            dt = datetime.now(timezone.utc)
        
        exchange = data.get("exchange", "")
        market_type = self._determine_market_type(exchange)
        
        return Quote(
            symbol=symbol,
            price=price,
            bid=None,
            ask=None,
            bid_size=None,
            ask_size=None,
            volume=int(data.get("volume", 0) or 0),
            timestamp=dt,
            provider="fmp",
            market_type=market_type,
            change=change,
            change_percent=change_pct,
            day_high=Decimal(str(data.get("dayHigh", 0))) if data.get("dayHigh") else None,
            day_low=Decimal(str(data.get("dayLow", 0))) if data.get("dayLow") else None,
            day_open=Decimal(str(data.get("open", 0))) if data.get("open") else None,
            prev_close=Decimal(str(data.get("previousClose", 0))) if data.get("previousClose") else None,
        )
    
    def _parse_bar(self, symbol: str, data: dict[str, Any], timeframe: TimeFrame) -> OHLCV:
        """Parse historical bar."""
        # Handle both date formats
        date_str = data.get("date")
        if date_str:
            try:
                if "T" in date_str or " " in date_str:
                    dt = datetime.fromisoformat(date_str.replace("Z", "+00:00").replace(" ", "T"))
                else:
                    dt = datetime.strptime(date_str, "%Y-%m-%d")
                dt = dt.replace(tzinfo=timezone.utc)
            except ValueError:
                dt = datetime.now(timezone.utc)
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
            provider="fmp",
            timeframe=timeframe,
            adjusted_close=Decimal(str(data.get("adjClose", 0))) if data.get("adjClose") else None,
        )
    
    def _determine_market_type(self, exchange: str) -> MarketType:
        """Determine market type from exchange."""
        exchange = exchange.upper()
        us_exchanges = ["NYSE", "NASDAQ", "AMEX", "BATS"]
        eu_exchanges = ["LSE", "XETRA", "EURONEXT", "SIX", "BME"]
        asia_exchanges = ["TSE", "HKEX", "SSE", "SZSE", "NSE"]
        
        if exchange in us_exchanges:
            return MarketType.US_STOCK
        elif exchange in eu_exchanges:
            return MarketType.EU_STOCK
        elif exchange in asia_exchanges:
            return MarketType.ASIA_STOCK
        elif "CRYPTO" in exchange:
            return MarketType.CRYPTO
        
        return MarketType.US_STOCK
