"""
Frankfurter Adapter

Provides access to Frankfurter API for forex rates (ECB data).
Free, no API key required, no rate limits.

Data source: European Central Bank
Supports: Quote (latest rates) and Historical (daily rates)

Endpoints:
- /v1/latest - Latest rates
- /v1/{date} - Rates for specific date
- /v1/{start}..{end} - Historical rates range
"""
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from typing import Optional
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
    DataNotAvailableError,
)


BASE_URL = "https://api.frankfurter.dev/v1"

# Supported currency pairs (base/quote)
SUPPORTED_CURRENCIES = {
    "USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD",
    "SEK", "NOK", "DKK", "PLN", "CZK", "HUF", "RON", "BGN",
    "TRY", "ILS", "ZAR", "MXN", "BRL", "SGD", "HKD", "KRW",
    "CNY", "INR", "IDR", "MYR", "PHP", "THB",
}


def create_frankfurter_config() -> ProviderConfig:
    """Create configuration for Frankfurter adapter."""
    return ProviderConfig(
        name="frankfurter",
        api_key="",  # No API key needed
        base_url=BASE_URL,
        requests_per_minute=60,  # No official limit, be conservative
        requests_per_day=10000,
        max_symbols_per_request=10,
        cost_per_request=Decimal("0"),
        daily_budget=Decimal("0"),
        timeout_seconds=30.0,
        retry_attempts=3,
        retry_delay=1.0,
        supports_websocket=False,
        supports_batch=True,
        supports_historical=True,
        supported_markets=[MarketType.FOREX],
        supported_data_types=[DataType.QUOTE, DataType.OHLCV],
        priority=60,  # Good priority for forex
    )


class FrankfurterAdapter(BaseAdapter):
    """Adapter for Frankfurter API (ECB forex data)."""
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self) -> None:
        """Initialize HTTP session."""
        if not self._session:
            self._session = aiohttp.ClientSession()
        logger.info("Frankfurter adapter initialized")
    
    async def close(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
        logger.info("Frankfurter adapter closed")
    
    async def health_check(self) -> bool:
        """Check connectivity."""
        try:
            url = f"{BASE_URL}/latest?base=USD&symbols=EUR"
            async with self._session.get(url) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Frankfurter health check failed: {e}")
            return False
    
    def _parse_forex_symbol(self, symbol: str) -> tuple[str, str]:
        """
        Parse forex symbol to base and quote currencies.
        Supports formats: EURUSD, EUR/USD, EUR-USD
        """
        symbol = symbol.upper().replace("/", "").replace("-", "")
        
        if len(symbol) == 6:
            base = symbol[:3]
            quote = symbol[3:]
            return base, quote
        
        raise ValueError(f"Invalid forex symbol: {symbol}")
    
    def _format_symbol(self, base: str, quote: str) -> str:
        """Format currency pair as standard symbol."""
        return f"{base}/{quote}"
    
    # ==================== Quote Methods ====================
    
    async def get_quote(self, symbol: str) -> Quote:
        """Get latest forex rate."""
        try:
            base, quote_curr = self._parse_forex_symbol(symbol)
            
            if base not in SUPPORTED_CURRENCIES or quote_curr not in SUPPORTED_CURRENCIES:
                raise DataNotAvailableError("frankfurter", symbol, "quote")
            
            start_time = datetime.now()
            url = f"{BASE_URL}/latest?base={base}&symbols={quote_curr}"
            
            async with self._session.get(url) as response:
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    data = await response.json()
                    
                    rate = data.get("rates", {}).get(quote_curr)
                    if rate is None:
                        raise DataNotAvailableError("frankfurter", symbol, "quote")
                    
                    # Get previous day rate for change calculation
                    prev_rate = None
                    change = None
                    change_pct = None
                    
                    try:
                        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
                        prev_url = f"{BASE_URL}/{yesterday}?base={base}&symbols={quote_curr}"
                        async with self._session.get(prev_url) as prev_response:
                            if prev_response.status == 200:
                                prev_data = await prev_response.json()
                                prev_rate = prev_data.get("rates", {}).get(quote_curr)
                                if prev_rate:
                                    change = Decimal(str(rate)) - Decimal(str(prev_rate))
                                    change_pct = (change / Decimal(str(prev_rate))) * 100
                    except:
                        pass  # Ignore errors in previous rate fetch
                    
                    quote = Quote(
                        symbol=self._format_symbol(base, quote_curr),
                        price=Decimal(str(rate)),
                        bid=None,  # ECB doesn't provide bid/ask
                        ask=None,
                        bid_size=None,
                        ask_size=None,
                        volume=0,
                        timestamp=datetime.now(timezone.utc),
                        provider="frankfurter",
                        market_type=MarketType.FOREX,
                        change=change,
                        change_percent=change_pct,
                        day_high=None,
                        day_low=None,
                        day_open=Decimal(str(prev_rate)) if prev_rate else None,
                        prev_close=Decimal(str(prev_rate)) if prev_rate else None,
                    )
                    
                    self._record_success(latency_ms)
                    return quote
                else:
                    raise ProviderError("frankfurter", f"API error {response.status}")
                    
        except DataNotAvailableError:
            raise
        except ValueError as e:
            raise DataNotAvailableError("frankfurter", symbol, "quote")
        except Exception as e:
            self._record_error(e)
            raise ProviderError("frankfurter", f"Error fetching quote: {e}")
    
    async def get_quotes(self, symbols: list[str]) -> list[Quote]:
        """Get quotes for multiple forex pairs."""
        quotes = []
        for symbol in symbols:
            try:
                quote = await self.get_quote(symbol)
                quotes.append(quote)
            except Exception as e:
                logger.warning(f"Frankfurter: Failed to get quote for {symbol}: {e}")
        return quotes
    
    # ==================== Historical Methods ====================
    
    async def get_historical(
        self,
        symbol: str,
        start_date: date,
        end_date: Optional[date] = None,
        timeframe: TimeFrame = TimeFrame.DAY,
    ) -> list[OHLCV]:
        """
        Get historical forex rates.
        Note: ECB data is daily only, no intraday data available.
        """
        end_date = end_date or date.today()
        
        # ECB only provides daily data
        if timeframe not in (TimeFrame.DAY, TimeFrame.WEEK, TimeFrame.MONTH):
            logger.warning(f"Frankfurter only supports daily data, requested: {timeframe}")
        
        try:
            base, quote_curr = self._parse_forex_symbol(symbol)
            
            if base not in SUPPORTED_CURRENCIES or quote_curr not in SUPPORTED_CURRENCIES:
                raise DataNotAvailableError("frankfurter", symbol, "historical")
            
            start_time = datetime.now()
            
            # Use date range endpoint
            url = f"{BASE_URL}/{start_date}..{end_date}?base={base}&symbols={quote_curr}"
            
            async with self._session.get(url) as response:
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    data = await response.json()
                    
                    rates = data.get("rates", {})
                    bars = []
                    
                    # Sort dates
                    sorted_dates = sorted(rates.keys())
                    
                    for date_str in sorted_dates:
                        try:
                            rate = rates[date_str].get(quote_curr)
                            if rate is None:
                                continue
                            
                            bar_date = datetime.strptime(date_str, "%Y-%m-%d")
                            rate_decimal = Decimal(str(rate))
                            
                            # For forex daily data, OHLC are all the same (daily close rate)
                            bar = OHLCV(
                                symbol=self._format_symbol(base, quote_curr),
                                timestamp=bar_date.replace(tzinfo=timezone.utc),
                                open=rate_decimal,
                                high=rate_decimal,
                                low=rate_decimal,
                                close=rate_decimal,
                                volume=0,  # No volume for ECB rates
                                timeframe=TimeFrame.DAY,
                                provider="frankfurter",
                            )
                            bars.append(bar)
                        except Exception as e:
                            logger.warning(f"Frankfurter: Failed to parse rate for {date_str}: {e}")
                    
                    self._record_success(latency_ms)
                    return bars
                else:
                    raise ProviderError("frankfurter", f"API error {response.status}")
                    
        except DataNotAvailableError:
            raise
        except ValueError as e:
            raise DataNotAvailableError("frankfurter", symbol, "historical")
        except Exception as e:
            self._record_error(e)
            raise ProviderError("frankfurter", f"Error fetching historical: {e}")
    
    def _determine_market_type(self, symbol: str) -> MarketType:
        """Always returns FOREX for this adapter."""
        return MarketType.FOREX
