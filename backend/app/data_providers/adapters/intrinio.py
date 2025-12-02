"""
Intrinio Adapter

Provides access to Intrinio market data API for US stocks.
Supports REST API for quotes and historical data.

API Documentation: https://docs.intrinio.com/
Requires subscription for real-time data.
"""
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


INTRINIO_BASE_URL = "https://api-v2.intrinio.com"


def create_intrinio_config(api_key: str) -> ProviderConfig:
    """Create configuration for Intrinio adapter."""
    return ProviderConfig(
        name="intrinio",
        api_key=api_key,
        base_url=INTRINIO_BASE_URL,
        requests_per_minute=100,
        requests_per_day=10000,
        max_symbols_per_request=100,
        cost_per_request=Decimal("0.001"),
        daily_budget=Decimal("50"),
        timeout_seconds=30.0,
        retry_attempts=3,
        retry_delay=1.0,
        supports_websocket=True,  # Available with subscription
        supports_batch=True,
        supports_historical=True,
        supported_markets=[MarketType.US_STOCK, MarketType.US_OPTION],
        supported_data_types=[DataType.QUOTE, DataType.OHLCV],
        priority=50,
    )


class IntrinioAdapter(BaseAdapter):
    """
    Intrinio data provider adapter.
    
    Features:
    - Real-time quotes (with subscription)
    - Historical stock prices
    - Fundamentals data
    - Options data
    
    Usage:
        config = create_intrinio_config("your_api_key")
        adapter = IntrinioAdapter(config)
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
            logger.info("Intrinio adapter initialized")
    
    async def close(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
        logger.info("Intrinio adapter closed")
    
    async def health_check(self) -> bool:
        """Check API connectivity."""
        try:
            url = f"{INTRINIO_BASE_URL}/securities/AAPL"
            params = {"api_key": self.config.api_key}
            
            async with self._session.get(url, params=params) as response:
                if response.status == 200:
                    return True
                elif response.status == 401:
                    logger.error("Intrinio authentication failed")
                    return False
                else:
                    logger.warning(f"Intrinio health check status: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Intrinio health check failed: {e}")
            return False
    
    # ==================== REST API Methods ====================
    
    async def get_quote(self, symbol: str) -> Quote:
        """
        Get latest quote for a symbol.
        
        Uses realtime price endpoint for subscribed users,
        falls back to security info for others.
        """
        symbol = symbol.upper()
        
        # Try realtime price first
        quote = await self._get_realtime_price(symbol)
        if quote:
            return quote
        
        # Fallback to security with latest price
        return await self._get_security_price(symbol)
    
    async def _get_realtime_price(self, symbol: str) -> Optional[Quote]:
        """Get real-time price (requires subscription)."""
        url = f"{INTRINIO_BASE_URL}/securities/{symbol}/prices/realtime"
        params = {"api_key": self.config.api_key}
        
        try:
            start_time = datetime.now()
            async with self._session.get(url, params=params) as response:
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    data = await response.json()
                    quote = self._parse_realtime_quote(symbol, data)
                    self._record_success(latency_ms)
                    return quote
                elif response.status == 403:
                    # Subscription required
                    return None
                elif response.status == 429:
                    raise RateLimitError("intrinio", retry_after=60)
                else:
                    return None
                    
        except aiohttp.ClientError:
            return None
    
    async def _get_security_price(self, symbol: str) -> Quote:
        """Get security info with latest price."""
        url = f"{INTRINIO_BASE_URL}/securities/{symbol}/prices"
        params = {
            "api_key": self.config.api_key,
            "page_size": 1,
        }
        
        try:
            start_time = datetime.now()
            async with self._session.get(url, params=params) as response:
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    data = await response.json()
                    
                    prices = data.get("stock_prices", [])
                    if not prices:
                        raise DataNotAvailableError("intrinio", symbol, "quote")
                    
                    quote = self._parse_eod_quote(symbol, prices[0])
                    self._record_success(latency_ms)
                    return quote
                    
                elif response.status == 401:
                    raise AuthenticationError("intrinio")
                elif response.status == 429:
                    raise RateLimitError("intrinio", retry_after=60)
                elif response.status == 404:
                    raise DataNotAvailableError("intrinio", symbol, "quote")
                else:
                    error_text = await response.text()
                    raise ProviderError("intrinio", f"API error {response.status}: {error_text}")
                    
        except aiohttp.ClientError as e:
            self._record_error(e)
            raise ProviderError("intrinio", f"Connection error: {e}")
    
    async def get_quotes(self, symbols: list[str]) -> list[Quote]:
        """Get quotes for multiple symbols."""
        if not symbols:
            return []
        
        # Intrinio doesn't have native batch endpoint for quotes
        # Process in parallel with limited concurrency
        quotes = []
        
        for symbol in symbols:
            try:
                quote = await self.get_quote(symbol)
                quotes.append(quote)
            except (DataNotAvailableError, ProviderError) as e:
                logger.warning(f"Failed to get Intrinio quote for {symbol}: {e}")
        
        return quotes
    
    async def get_historical(
        self,
        symbol: str,
        start_date: date,
        end_date: Optional[date] = None,
        timeframe: TimeFrame = TimeFrame.DAY,
    ) -> list[OHLCV]:
        """Get historical stock prices."""
        symbol = symbol.upper()
        
        if end_date is None:
            end_date = date.today()
        
        # Map timeframe to Intrinio frequency
        frequency_map = {
            TimeFrame.MINUTE: "none",  # Not supported
            TimeFrame.FIVE_MIN: "none",
            TimeFrame.FIFTEEN_MIN: "none",
            TimeFrame.HOUR: "none",
            TimeFrame.DAY: "daily",
            TimeFrame.WEEK: "weekly",
            TimeFrame.MONTH: "monthly",
        }
        
        frequency = frequency_map.get(timeframe, "daily")
        if frequency == "none":
            logger.warning(f"Intrinio: timeframe {timeframe} not supported, using daily")
            frequency = "daily"
        
        url = f"{INTRINIO_BASE_URL}/securities/{symbol}/prices"
        all_bars = []
        page_size = 100
        next_page = None
        
        while True:
            params = {
                "api_key": self.config.api_key,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "frequency": frequency,
                "page_size": page_size,
            }
            
            if next_page:
                params["next_page"] = next_page
            
            try:
                start_time = datetime.now()
                async with self._session.get(url, params=params) as response:
                    latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        prices = data.get("stock_prices", [])
                        for item in prices:
                            try:
                                bar = self._parse_historical_bar(symbol, item, timeframe)
                                all_bars.append(bar)
                            except Exception as e:
                                logger.warning(f"Failed to parse Intrinio bar: {e}")
                        
                        self._record_success(latency_ms)
                        
                        # Check for pagination
                        next_page = data.get("next_page")
                        if not next_page:
                            break
                            
                    elif response.status == 429:
                        raise RateLimitError("intrinio", retry_after=60)
                    elif response.status == 404:
                        break
                    else:
                        error_text = await response.text()
                        raise ProviderError("intrinio", f"API error {response.status}: {error_text}")
                        
            except aiohttp.ClientError as e:
                self._record_error(e)
                raise ProviderError("intrinio", f"Connection error: {e}")
        
        # Sort by timestamp
        all_bars.sort(key=lambda x: x.timestamp)
        return all_bars
    
    async def search_symbols(self, query: str) -> list[dict[str, Any]]:
        """Search for securities by name or ticker."""
        url = f"{INTRINIO_BASE_URL}/securities/search"
        params = {
            "api_key": self.config.api_key,
            "query": query,
        }
        
        try:
            async with self._session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    results = []
                    for security in data.get("securities", []):
                        results.append({
                            "symbol": security.get("ticker"),
                            "name": security.get("name"),
                            "exchange": security.get("stock_exchange", {}).get("name"),
                            "type": "stock",
                        })
                    
                    return results
                    
                else:
                    return []
                    
        except Exception as e:
            logger.warning(f"Intrinio symbol search failed: {e}")
            return []
    
    # ==================== Fundamentals Methods ====================
    
    async def get_company_info(self, symbol: str) -> Optional[dict[str, Any]]:
        """Get company fundamental information."""
        url = f"{INTRINIO_BASE_URL}/companies/{symbol}"
        params = {"api_key": self.config.api_key}
        
        try:
            async with self._session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    return {
                        "ticker": data.get("ticker"),
                        "name": data.get("name"),
                        "legal_name": data.get("legal_name"),
                        "cik": data.get("cik"),
                        "lei": data.get("lei"),
                        "sector": data.get("sector"),
                        "industry_category": data.get("industry_category"),
                        "industry_group": data.get("industry_group"),
                        "template": data.get("template"),
                        "short_description": data.get("short_description"),
                        "long_description": data.get("long_description"),
                        "ceo": data.get("ceo"),
                        "company_url": data.get("company_url"),
                        "business_address": data.get("business_address"),
                        "mailing_address": data.get("mailing_address"),
                        "business_phone_no": data.get("business_phone_no"),
                        "hq_address1": data.get("hq_address1"),
                        "hq_city": data.get("hq_city"),
                        "hq_state": data.get("hq_state"),
                        "hq_country": data.get("hq_country"),
                        "inc_country": data.get("inc_country"),
                        "employees": data.get("employees"),
                    }
                else:
                    return None
                    
        except Exception as e:
            logger.warning(f"Failed to get Intrinio company info: {e}")
            return None
    
    # ==================== Parsing Methods ====================
    
    def _parse_realtime_quote(self, symbol: str, data: dict[str, Any]) -> Quote:
        """Parse real-time quote response."""
        last = Decimal(str(data.get("last_price", 0) or 0))
        open_price = Decimal(str(data.get("open_price", 0) or 0))
        
        change = last - open_price if open_price else None
        change_pct = (change / open_price * 100) if change and open_price else None
        
        timestamp_str = data.get("last_time")
        if timestamp_str:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        else:
            timestamp = datetime.now(timezone.utc)
        
        return Quote(
            symbol=symbol,
            price=last,
            bid=Decimal(str(data.get("bid_price", 0))) if data.get("bid_price") else None,
            ask=Decimal(str(data.get("ask_price", 0))) if data.get("ask_price") else None,
            bid_size=data.get("bid_size"),
            ask_size=data.get("ask_size"),
            volume=int(data.get("volume", 0) or 0),
            timestamp=timestamp,
            provider="intrinio",
            market_type=MarketType.US_STOCK,
            change=change,
            change_percent=change_pct,
            day_high=Decimal(str(data.get("high_price", 0))) if data.get("high_price") else None,
            day_low=Decimal(str(data.get("low_price", 0))) if data.get("low_price") else None,
            day_open=open_price if open_price else None,
        )
    
    def _parse_eod_quote(self, symbol: str, data: dict[str, Any]) -> Quote:
        """Parse end-of-day price as quote."""
        close = Decimal(str(data.get("close", 0) or data.get("adj_close", 0) or 0))
        open_price = Decimal(str(data.get("open", 0) or 0))
        
        change = close - open_price if open_price else None
        change_pct = (change / open_price * 100) if change and open_price else None
        
        date_str = data.get("date")
        if date_str:
            timestamp = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        else:
            timestamp = datetime.now(timezone.utc)
        
        return Quote(
            symbol=symbol,
            price=close,
            bid=None,
            ask=None,
            bid_size=None,
            ask_size=None,
            volume=int(data.get("volume", 0) or 0),
            timestamp=timestamp,
            provider="intrinio",
            market_type=MarketType.US_STOCK,
            change=change,
            change_percent=change_pct,
            day_high=Decimal(str(data.get("high", 0))) if data.get("high") else None,
            day_low=Decimal(str(data.get("low", 0))) if data.get("low") else None,
            day_open=open_price if open_price else None,
        )
    
    def _parse_historical_bar(
        self,
        symbol: str,
        data: dict[str, Any],
        timeframe: TimeFrame,
    ) -> OHLCV:
        """Parse historical price bar."""
        date_str = data.get("date")
        if date_str:
            timestamp = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
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
            provider="intrinio",
            timeframe=timeframe,
            adjusted_close=Decimal(str(data.get("adj_close", 0))) if data.get("adj_close") else None,
        )
