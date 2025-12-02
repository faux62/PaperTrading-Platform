"""
Nasdaq Data Link (formerly Quandl) Adapter

Provides access to Nasdaq Data Link API for financial data.
Comprehensive historical data from multiple sources.

API Documentation: https://docs.data.nasdaq.com/
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


NASDAQ_BASE_URL = "https://data.nasdaq.com/api/v3"


def create_nasdaq_datalink_config(api_key: str) -> ProviderConfig:
    """Create configuration for Nasdaq Data Link adapter."""
    return ProviderConfig(
        name="nasdaq_datalink",
        api_key=api_key,
        base_url=NASDAQ_BASE_URL,
        requests_per_minute=300,
        requests_per_day=50000,
        max_symbols_per_request=1,
        cost_per_request=Decimal("0"),
        daily_budget=Decimal("0"),
        timeout_seconds=30.0,
        retry_attempts=3,
        retry_delay=1.0,
        supports_websocket=False,
        supports_batch=False,
        supports_historical=True,
        supported_markets=[
            MarketType.US_STOCK,
            MarketType.COMMODITY,
            MarketType.INDEX,
        ],
        supported_data_types=[DataType.OHLCV],
        priority=45,
    )


class NasdaqDataLinkAdapter(BaseAdapter):
    """
    Nasdaq Data Link data provider adapter.
    
    Features:
    - Historical end-of-day data
    - Multiple data sources (WIKI, EOD, etc.)
    - Commodity futures
    - Economic indicators
    
    Data codes:
    - WIKI/AAPL - Wiki EOD Stock Prices
    - EOD/AAPL - End of Day US Stock Prices
    - CHRIS/CME_CL1 - Crude Oil Futures
    
    Usage:
        config = create_nasdaq_datalink_config("your_api_key")
        adapter = NasdaqDataLinkAdapter(config)
        await adapter.initialize()
        
        bars = await adapter.get_historical("WIKI/AAPL", start_date, end_date)
    """
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self) -> None:
        """Initialize HTTP session."""
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            self._session = aiohttp.ClientSession(timeout=timeout)
            logger.info("Nasdaq Data Link adapter initialized")
    
    async def close(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
        logger.info("Nasdaq Data Link adapter closed")
    
    async def health_check(self) -> bool:
        """Check API connectivity."""
        try:
            url = f"{NASDAQ_BASE_URL}/datasets/WIKI/AAPL/metadata.json"
            params = {"api_key": self.config.api_key}
            
            async with self._session.get(url, params=params) as response:
                if response.status == 200:
                    return True
                elif response.status == 401:
                    logger.error("Nasdaq Data Link authentication failed")
                    return False
                return False
        except Exception as e:
            logger.error(f"Nasdaq Data Link health check failed: {e}")
            return False
    
    # ==================== Historical Methods ====================
    
    async def get_quote(self, symbol: str) -> Quote:
        """
        Get latest data point as quote.
        
        Note: Nasdaq Data Link doesn't provide real-time quotes.
        Returns most recent historical data.
        """
        from datetime import timedelta
        
        end_date = date.today()
        start_date = end_date - timedelta(days=7)
        
        bars = await self.get_historical(symbol, start_date, end_date)
        
        if not bars:
            raise DataNotAvailableError("nasdaq_datalink", symbol, "quote")
        
        latest = bars[-1]
        prev_close = bars[-2].close if len(bars) > 1 else None
        change = latest.close - prev_close if prev_close else None
        change_pct = (change / prev_close * 100) if change and prev_close else None
        
        return Quote(
            symbol=symbol,
            price=latest.close,
            bid=None,
            ask=None,
            bid_size=None,
            ask_size=None,
            volume=latest.volume,
            timestamp=latest.timestamp,
            provider="nasdaq_datalink",
            market_type=MarketType.US_STOCK,
            change=change,
            change_percent=change_pct,
            day_high=latest.high,
            day_low=latest.low,
            day_open=latest.open,
            prev_close=prev_close,
        )
    
    async def get_quotes(self, symbols: list[str]) -> list[Quote]:
        """Get quotes for multiple symbols."""
        quotes = []
        for symbol in symbols:
            try:
                quote = await self.get_quote(symbol)
                quotes.append(quote)
            except (DataNotAvailableError, ProviderError) as e:
                logger.warning(f"Failed to get quote for {symbol}: {e}")
        return quotes
    
    async def get_historical(
        self,
        symbol: str,
        start_date: date,
        end_date: Optional[date] = None,
        timeframe: TimeFrame = TimeFrame.DAY,
    ) -> list[OHLCV]:
        """
        Get historical data.
        
        Symbol format: DATABASE/DATASET (e.g., WIKI/AAPL, EOD/AAPL)
        """
        if end_date is None:
            end_date = date.today()
        
        # Parse symbol into database/dataset
        if "/" in symbol:
            database, dataset = symbol.split("/", 1)
        else:
            # Default to EOD database
            database = "EOD"
            dataset = symbol.upper()
        
        url = f"{NASDAQ_BASE_URL}/datasets/{database}/{dataset}.json"
        params = {
            "api_key": self.config.api_key,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }
        
        try:
            start_time = datetime.now()
            async with self._session.get(url, params=params) as response:
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    data = await response.json()
                    
                    dataset_data = data.get("dataset", {})
                    column_names = dataset_data.get("column_names", [])
                    rows = dataset_data.get("data", [])
                    
                    bars = []
                    for row in rows:
                        try:
                            bar = self._parse_row(symbol, column_names, row, timeframe)
                            if bar:
                                bars.append(bar)
                        except Exception as e:
                            logger.debug(f"Failed to parse row: {e}")
                    
                    self._record_success(latency_ms)
                    bars.sort(key=lambda x: x.timestamp)
                    return bars
                    
                elif response.status == 401:
                    raise AuthenticationError("nasdaq_datalink")
                elif response.status == 429:
                    raise RateLimitError("nasdaq_datalink", retry_after=60)
                elif response.status == 404:
                    raise DataNotAvailableError("nasdaq_datalink", symbol, "historical")
                else:
                    return []
                    
        except aiohttp.ClientError as e:
            self._record_error(e)
            raise ProviderError("nasdaq_datalink", f"Connection error: {e}")
    
    async def search_symbols(self, query: str) -> list[dict[str, Any]]:
        """Search for datasets."""
        url = f"{NASDAQ_BASE_URL}/datasets.json"
        params = {
            "api_key": self.config.api_key,
            "query": query,
            "per_page": 20,
        }
        
        try:
            async with self._session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    datasets = data.get("datasets", [])
                    
                    results = []
                    for item in datasets:
                        results.append({
                            "symbol": f"{item.get('database_code')}/{item.get('dataset_code')}",
                            "name": item.get("name"),
                            "description": item.get("description"),
                            "database": item.get("database_code"),
                            "type": item.get("type"),
                            "frequency": item.get("frequency"),
                        })
                    
                    return results
                return []
        except Exception as e:
            logger.warning(f"Search failed: {e}")
            return []
    
    # ==================== Specific Data Methods ====================
    
    async def get_wiki_eod(
        self,
        symbol: str,
        start_date: date,
        end_date: Optional[date] = None,
    ) -> list[OHLCV]:
        """Get WIKI end-of-day stock data."""
        return await self.get_historical(f"WIKI/{symbol.upper()}", start_date, end_date)
    
    async def get_commodity_futures(
        self,
        exchange: str,
        symbol: str,
        start_date: date,
        end_date: Optional[date] = None,
    ) -> list[OHLCV]:
        """
        Get commodity futures data.
        
        Example: get_commodity_futures("CME", "CL1") for Crude Oil
        """
        return await self.get_historical(f"CHRIS/{exchange}_{symbol}", start_date, end_date)
    
    # ==================== Parsing Methods ====================
    
    def _parse_row(
        self,
        symbol: str,
        columns: list[str],
        row: list[Any],
        timeframe: TimeFrame,
    ) -> Optional[OHLCV]:
        """Parse a data row into OHLCV."""
        if len(columns) != len(row):
            return None
        
        data = dict(zip(columns, row))
        
        # Common column name variations
        date_keys = ["Date", "date", "DATE"]
        open_keys = ["Open", "open", "OPEN", "Adj. Open"]
        high_keys = ["High", "high", "HIGH", "Adj. High"]
        low_keys = ["Low", "low", "LOW", "Adj. Low"]
        close_keys = ["Close", "close", "CLOSE", "Adj. Close", "Last"]
        volume_keys = ["Volume", "volume", "VOLUME", "Adj. Volume"]
        
        def get_value(keys: list[str], default: Any = None) -> Any:
            for key in keys:
                if key in data:
                    return data[key]
            return default
        
        date_str = get_value(date_keys)
        if not date_str:
            return None
        
        try:
            timestamp = datetime.strptime(str(date_str), "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            return None
        
        open_val = get_value(open_keys, 0)
        high_val = get_value(high_keys, 0)
        low_val = get_value(low_keys, 0)
        close_val = get_value(close_keys, 0)
        volume_val = get_value(volume_keys, 0)
        
        return OHLCV(
            symbol=symbol,
            timestamp=timestamp,
            open=Decimal(str(open_val or 0)),
            high=Decimal(str(high_val or 0)),
            low=Decimal(str(low_val or 0)),
            close=Decimal(str(close_val or 0)),
            volume=int(float(volume_val or 0)),
            provider="nasdaq_datalink",
            timeframe=timeframe,
        )
