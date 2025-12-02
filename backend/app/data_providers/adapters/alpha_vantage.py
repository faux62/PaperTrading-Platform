"""
Alpha Vantage Adapter

Provides access to Alpha Vantage API for market data.
Free tier with 25 requests/day, premium plans available.

API Documentation: https://www.alphavantage.co/documentation/
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


ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"


def create_alpha_vantage_config(api_key: str) -> ProviderConfig:
    """Create configuration for Alpha Vantage adapter."""
    return ProviderConfig(
        name="alpha_vantage",
        api_key=api_key,
        base_url=ALPHA_VANTAGE_BASE_URL,
        requests_per_minute=5,  # Free tier: 5/min
        requests_per_day=500,  # Free tier: 500/day
        max_symbols_per_request=1,
        cost_per_request=Decimal("0"),
        daily_budget=Decimal("0"),
        timeout_seconds=30.0,
        retry_attempts=3,
        retry_delay=12.0,  # Wait 12s between retries (rate limit)
        supports_websocket=False,
        supports_batch=False,
        supports_historical=True,
        supported_markets=[
            MarketType.US_STOCK,
            MarketType.FOREX,
            MarketType.CRYPTO,
        ],
        supported_data_types=[DataType.QUOTE, DataType.OHLCV],
        priority=55,  # Lower priority due to rate limits
    )


class AlphaVantageAdapter(BaseAdapter):
    """
    Alpha Vantage data provider adapter.
    
    Features:
    - Stock quotes and historical data
    - Forex rates
    - Cryptocurrency data
    - Technical indicators
    - Fundamental data
    
    Limitations:
    - Strict rate limiting (5 req/min free)
    - One symbol per request
    - JSON/CSV response formats
    
    Usage:
        config = create_alpha_vantage_config("your_api_key")
        adapter = AlphaVantageAdapter(config)
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
            logger.info("Alpha Vantage adapter initialized")
    
    async def close(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
        logger.info("Alpha Vantage adapter closed")
    
    async def health_check(self) -> bool:
        """Check API connectivity."""
        try:
            params = {
                "function": "TIME_SERIES_INTRADAY",
                "symbol": "IBM",
                "interval": "5min",
                "apikey": self.config.api_key,
            }
            
            async with self._session.get(ALPHA_VANTAGE_BASE_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    # Check for rate limit or error
                    if "Note" in data or "Error Message" in data:
                        return False
                    return True
                return False
        except Exception as e:
            logger.error(f"Alpha Vantage health check failed: {e}")
            return False
    
    # ==================== Quote Methods ====================
    
    async def get_quote(self, symbol: str) -> Quote:
        """Get real-time quote for a symbol."""
        symbol = symbol.upper()
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": self.config.api_key,
        }
        
        try:
            start_time = datetime.now()
            async with self._session.get(ALPHA_VANTAGE_BASE_URL, params=params) as response:
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    data = await response.json()
                    
                    # Check for rate limit
                    if "Note" in data:
                        raise RateLimitError("alpha_vantage", retry_after=60)
                    
                    if "Error Message" in data:
                        raise DataNotAvailableError("alpha_vantage", symbol, "quote")
                    
                    quote_data = data.get("Global Quote", {})
                    if not quote_data:
                        raise DataNotAvailableError("alpha_vantage", symbol, "quote")
                    
                    quote = self._parse_quote(quote_data)
                    self._record_success(latency_ms)
                    return quote
                    
                else:
                    raise ProviderError("alpha_vantage", f"API error {response.status}")
                    
        except aiohttp.ClientError as e:
            self._record_error(e)
            raise ProviderError("alpha_vantage", f"Connection error: {e}")
    
    async def get_quotes(self, symbols: list[str]) -> list[Quote]:
        """Get quotes for multiple symbols (sequential due to rate limits)."""
        import asyncio
        
        quotes = []
        for symbol in symbols:
            try:
                quote = await self.get_quote(symbol)
                quotes.append(quote)
                # Rate limiting delay
                await asyncio.sleep(12)  # 5 req/min = 12s between
            except (DataNotAvailableError, RateLimitError) as e:
                logger.warning(f"Failed to get quote for {symbol}: {e}")
        
        return quotes
    
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
        
        # Map timeframe to Alpha Vantage function
        if timeframe == TimeFrame.DAY:
            params = {
                "function": "TIME_SERIES_DAILY_ADJUSTED",
                "symbol": symbol,
                "outputsize": "full",
                "apikey": self.config.api_key,
            }
            time_series_key = "Time Series (Daily)"
        elif timeframe in [TimeFrame.MINUTE, TimeFrame.FIVE_MIN, TimeFrame.FIFTEEN_MIN, TimeFrame.HOUR]:
            interval_map = {
                TimeFrame.MINUTE: "1min",
                TimeFrame.FIVE_MIN: "5min",
                TimeFrame.FIFTEEN_MIN: "15min",
                TimeFrame.HOUR: "60min",
            }
            params = {
                "function": "TIME_SERIES_INTRADAY",
                "symbol": symbol,
                "interval": interval_map.get(timeframe, "5min"),
                "outputsize": "full",
                "apikey": self.config.api_key,
            }
            time_series_key = f"Time Series ({interval_map.get(timeframe, '5min')})"
        elif timeframe == TimeFrame.WEEK:
            params = {
                "function": "TIME_SERIES_WEEKLY_ADJUSTED",
                "symbol": symbol,
                "apikey": self.config.api_key,
            }
            time_series_key = "Weekly Adjusted Time Series"
        elif timeframe == TimeFrame.MONTH:
            params = {
                "function": "TIME_SERIES_MONTHLY_ADJUSTED",
                "symbol": symbol,
                "apikey": self.config.api_key,
            }
            time_series_key = "Monthly Adjusted Time Series"
        else:
            params = {
                "function": "TIME_SERIES_DAILY_ADJUSTED",
                "symbol": symbol,
                "outputsize": "full",
                "apikey": self.config.api_key,
            }
            time_series_key = "Time Series (Daily)"
        
        try:
            start_time = datetime.now()
            async with self._session.get(ALPHA_VANTAGE_BASE_URL, params=params) as response:
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    data = await response.json()
                    
                    if "Note" in data:
                        raise RateLimitError("alpha_vantage", retry_after=60)
                    
                    if "Error Message" in data:
                        raise DataNotAvailableError("alpha_vantage", symbol, "historical")
                    
                    time_series = data.get(time_series_key, {})
                    
                    bars = []
                    for date_str, values in time_series.items():
                        try:
                            bar_date = self._parse_date(date_str)
                            
                            # Filter by date range
                            if bar_date.date() < start_date or bar_date.date() > end_date:
                                continue
                            
                            bar = self._parse_bar(symbol, bar_date, values, timeframe)
                            bars.append(bar)
                        except Exception as e:
                            logger.debug(f"Failed to parse bar: {e}")
                    
                    self._record_success(latency_ms)
                    bars.sort(key=lambda x: x.timestamp)
                    return bars
                    
                else:
                    return []
                    
        except aiohttp.ClientError as e:
            self._record_error(e)
            raise ProviderError("alpha_vantage", f"Connection error: {e}")
    
    async def search_symbols(self, query: str) -> list[dict[str, Any]]:
        """Search for symbols."""
        params = {
            "function": "SYMBOL_SEARCH",
            "keywords": query,
            "apikey": self.config.api_key,
        }
        
        try:
            async with self._session.get(ALPHA_VANTAGE_BASE_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if "Note" in data:
                        return []  # Rate limited
                    
                    matches = data.get("bestMatches", [])
                    
                    results = []
                    for item in matches:
                        results.append({
                            "symbol": item.get("1. symbol"),
                            "name": item.get("2. name"),
                            "type": item.get("3. type"),
                            "region": item.get("4. region"),
                            "market_open": item.get("5. marketOpen"),
                            "market_close": item.get("6. marketClose"),
                            "timezone": item.get("7. timezone"),
                            "currency": item.get("8. currency"),
                        })
                    
                    return results
                return []
        except Exception as e:
            logger.warning(f"Search failed: {e}")
            return []
    
    # ==================== Forex Methods ====================
    
    async def get_forex_quote(self, from_currency: str, to_currency: str) -> Quote:
        """Get forex exchange rate."""
        params = {
            "function": "CURRENCY_EXCHANGE_RATE",
            "from_currency": from_currency.upper(),
            "to_currency": to_currency.upper(),
            "apikey": self.config.api_key,
        }
        
        try:
            async with self._session.get(ALPHA_VANTAGE_BASE_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if "Note" in data:
                        raise RateLimitError("alpha_vantage", retry_after=60)
                    
                    rate_data = data.get("Realtime Currency Exchange Rate", {})
                    if not rate_data:
                        raise DataNotAvailableError("alpha_vantage", f"{from_currency}/{to_currency}", "forex")
                    
                    rate = Decimal(str(rate_data.get("5. Exchange Rate", 0)))
                    bid = Decimal(str(rate_data.get("8. Bid Price", 0)))
                    ask = Decimal(str(rate_data.get("9. Ask Price", 0)))
                    
                    return Quote(
                        symbol=f"{from_currency}/{to_currency}",
                        price=rate,
                        bid=bid if bid else None,
                        ask=ask if ask else None,
                        bid_size=None,
                        ask_size=None,
                        volume=0,
                        timestamp=datetime.now(timezone.utc),
                        provider="alpha_vantage",
                        market_type=MarketType.FOREX,
                    )
                else:
                    raise ProviderError("alpha_vantage", f"API error {response.status}")
                    
        except aiohttp.ClientError as e:
            raise ProviderError("alpha_vantage", f"Connection error: {e}")
    
    # ==================== Parsing Methods ====================
    
    def _parse_quote(self, data: dict[str, Any]) -> Quote:
        """Parse Global Quote response."""
        symbol = data.get("01. symbol", "").upper()
        
        price = Decimal(str(data.get("05. price", 0) or 0))
        change = Decimal(str(data.get("09. change", 0) or 0))
        change_pct_str = data.get("10. change percent", "0%").replace("%", "")
        change_pct = Decimal(str(change_pct_str or 0))
        
        return Quote(
            symbol=symbol,
            price=price,
            bid=None,
            ask=None,
            bid_size=None,
            ask_size=None,
            volume=int(data.get("06. volume", 0) or 0),
            timestamp=datetime.now(timezone.utc),
            provider="alpha_vantage",
            market_type=MarketType.US_STOCK,
            change=change,
            change_percent=change_pct,
            day_high=Decimal(str(data.get("03. high", 0))) if data.get("03. high") else None,
            day_low=Decimal(str(data.get("04. low", 0))) if data.get("04. low") else None,
            day_open=Decimal(str(data.get("02. open", 0))) if data.get("02. open") else None,
            prev_close=Decimal(str(data.get("08. previous close", 0))) if data.get("08. previous close") else None,
        )
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime."""
        try:
            if " " in date_str:
                dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            else:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return datetime.now(timezone.utc)
    
    def _parse_bar(
        self,
        symbol: str,
        timestamp: datetime,
        data: dict[str, Any],
        timeframe: TimeFrame,
    ) -> OHLCV:
        """Parse historical bar data."""
        # Handle different key formats
        open_key = "1. open"
        high_key = "2. high"
        low_key = "3. low"
        close_key = "4. close"
        volume_key = "5. volume" if timeframe in [TimeFrame.MINUTE, TimeFrame.FIVE_MIN, TimeFrame.FIFTEEN_MIN, TimeFrame.HOUR] else "6. volume"
        adj_close_key = "5. adjusted close"
        
        return OHLCV(
            symbol=symbol,
            timestamp=timestamp,
            open=Decimal(str(data.get(open_key, 0) or 0)),
            high=Decimal(str(data.get(high_key, 0) or 0)),
            low=Decimal(str(data.get(low_key, 0) or 0)),
            close=Decimal(str(data.get(close_key, 0) or 0)),
            volume=int(float(data.get(volume_key, 0) or 0)),
            provider="alpha_vantage",
            timeframe=timeframe,
            adjusted_close=Decimal(str(data.get(adj_close_key, 0))) if data.get(adj_close_key) else None,
        )
