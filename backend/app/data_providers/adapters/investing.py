"""
Investing.com Adapter

Provides access to Investing.com data for European and global markets.
Uses investpy library for data retrieval.

Note: This is scraping-based, use responsibly with rate limiting.
"""
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from typing import Optional, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor
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


# Country to market mapping
COUNTRY_MARKETS = {
    "italy": MarketType.EU_STOCK,
    "spain": MarketType.EU_STOCK,
    "germany": MarketType.EU_STOCK,
    "france": MarketType.EU_STOCK,
    "united kingdom": MarketType.EU_STOCK,
    "netherlands": MarketType.EU_STOCK,
    "switzerland": MarketType.EU_STOCK,
    "belgium": MarketType.EU_STOCK,
    "portugal": MarketType.EU_STOCK,
    "united states": MarketType.US_STOCK,
    "japan": MarketType.ASIA_STOCK,
    "china": MarketType.ASIA_STOCK,
    "hong kong": MarketType.ASIA_STOCK,
    "india": MarketType.ASIA_STOCK,
    "australia": MarketType.ASIA_STOCK,
}


def create_investing_config() -> ProviderConfig:
    """Create configuration for Investing.com adapter."""
    return ProviderConfig(
        name="investing",
        api_key="",  # No API key needed
        base_url="",
        requests_per_minute=10,  # Conservative limit
        requests_per_day=1000,
        max_symbols_per_request=1,  # One at a time for scraping
        cost_per_request=Decimal("0"),
        daily_budget=Decimal("0"),
        timeout_seconds=30.0,
        retry_attempts=3,
        retry_delay=3.0,  # Longer delay for scraping
        supports_websocket=False,
        supports_batch=False,
        supports_historical=True,
        supported_markets=[
            MarketType.EU_STOCK,
            MarketType.US_STOCK,
            MarketType.ASIA_STOCK,
            MarketType.FOREX,
            MarketType.CRYPTO,
            MarketType.COMMODITY,
            MarketType.INDEX,
            MarketType.ETF,
        ],
        supported_data_types=[DataType.QUOTE, DataType.OHLCV],
        priority=70,  # Lower priority due to scraping
    )


class InvestingAdapter(BaseAdapter):
    """
    Investing.com data provider adapter.
    
    Features:
    - European market coverage (MIB, IBEX, DAX, CAC40)
    - Global indices
    - Forex and commodities
    - Historical data
    
    Limitations:
    - Scraping-based, may break
    - No real-time data
    - Rate limiting essential
    
    Usage:
        config = create_investing_config()
        adapter = InvestingAdapter(config)
        await adapter.initialize()
        
        bars = await adapter.get_historical("ENI", start_date, end_date, country="italy")
    """
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._executor = ThreadPoolExecutor(max_workers=3)
        self._investpy = None
        self._stock_countries_cache: dict[str, list[str]] = {}
    
    async def initialize(self) -> None:
        """Initialize investpy."""
        try:
            import investpy
            self._investpy = investpy
            logger.info("Investing.com adapter initialized")
        except ImportError:
            raise ProviderError("investing", "investpy library not installed. Run: pip install investpy")
    
    async def close(self) -> None:
        """Close executor."""
        self._executor.shutdown(wait=False)
        logger.info("Investing.com adapter closed")
    
    async def health_check(self) -> bool:
        """Check investpy availability."""
        try:
            # Quick test
            def test():
                return self._investpy.get_stock_countries()
            
            countries = await self._run_sync(test)
            return len(countries) > 0
        except Exception as e:
            logger.error(f"Investing.com health check failed: {e}")
            return False
    
    async def _run_sync(self, func):
        """Run synchronous function in executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, func)
    
    # ==================== Stock Methods ====================
    
    async def get_quote(self, symbol: str, country: str = "united states") -> Quote:
        """
        Get latest quote for a stock.
        
        Note: investpy doesn't provide real-time quotes.
        Returns latest historical data point.
        """
        symbol = symbol.upper()
        country = country.lower()
        
        # Get recent historical data as "quote"
        end_date = date.today()
        start_date = end_date - timedelta(days=7)
        
        try:
            bars = await self.get_historical_stock(symbol, start_date, end_date, country)
            
            if not bars:
                raise DataNotAvailableError("investing", symbol, "quote")
            
            # Use latest bar as quote
            latest = bars[-1]
            
            prev_close = bars[-2].close if len(bars) > 1 else None
            change = latest.close - prev_close if prev_close else None
            change_pct = (change / prev_close * 100) if change and prev_close else None
            
            market_type = COUNTRY_MARKETS.get(country, MarketType.US_STOCK)
            
            return Quote(
                symbol=symbol,
                price=latest.close,
                bid=None,
                ask=None,
                bid_size=None,
                ask_size=None,
                volume=latest.volume,
                timestamp=latest.timestamp,
                provider="investing",
                market_type=market_type,
                change=change,
                change_percent=change_pct,
                day_high=latest.high,
                day_low=latest.low,
                day_open=latest.open,
                prev_close=prev_close,
            )
            
        except Exception as e:
            if isinstance(e, DataNotAvailableError):
                raise
            raise ProviderError("investing", f"Error fetching quote: {e}")
    
    async def get_quotes(self, symbols: list[str]) -> list[Quote]:
        """Get quotes for multiple symbols (one by one)."""
        quotes = []
        
        for symbol in symbols:
            try:
                # Add delay between requests
                await asyncio.sleep(0.5)
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
        country: str = "united states",
    ) -> list[OHLCV]:
        """Get historical data (daily only)."""
        # investpy only supports daily data
        if timeframe != TimeFrame.DAY:
            logger.warning("Investing.com only supports daily data")
        
        return await self.get_historical_stock(symbol, start_date, end_date, country)
    
    async def get_historical_stock(
        self,
        symbol: str,
        start_date: date,
        end_date: Optional[date] = None,
        country: str = "united states",
    ) -> list[OHLCV]:
        """Get historical stock data."""
        symbol = symbol.upper()
        country = country.lower()
        
        if end_date is None:
            end_date = date.today()
        
        try:
            start_time = datetime.now()
            
            def fetch_history():
                return self._investpy.get_stock_historical_data(
                    stock=symbol,
                    country=country,
                    from_date=start_date.strftime("%d/%m/%Y"),
                    to_date=end_date.strftime("%d/%m/%Y"),
                )
            
            df = await self._run_sync(fetch_history)
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            if df is None or df.empty:
                return []
            
            bars = []
            market_type = COUNTRY_MARKETS.get(country, MarketType.US_STOCK)
            
            for idx, row in df.iterrows():
                timestamp = idx.to_pydatetime()
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                
                bar = OHLCV(
                    symbol=symbol,
                    timestamp=timestamp,
                    open=Decimal(str(row.get("Open", 0))),
                    high=Decimal(str(row.get("High", 0))),
                    low=Decimal(str(row.get("Low", 0))),
                    close=Decimal(str(row.get("Close", 0))),
                    volume=int(row.get("Volume", 0) or 0),
                    provider="investing",
                    timeframe=TimeFrame.DAY,
                )
                bars.append(bar)
            
            self._record_success(latency_ms)
            return bars
            
        except Exception as e:
            self._record_error(e)
            if "not found" in str(e).lower() or "not available" in str(e).lower():
                raise DataNotAvailableError("investing", symbol, "historical")
            raise ProviderError("investing", f"Error fetching history: {e}")
    
    # ==================== Index Methods ====================
    
    async def get_index_historical(
        self,
        index_name: str,
        start_date: date,
        end_date: Optional[date] = None,
        country: str = "italy",
    ) -> list[OHLCV]:
        """Get historical index data."""
        country = country.lower()
        
        if end_date is None:
            end_date = date.today()
        
        try:
            start_time = datetime.now()
            
            def fetch_history():
                return self._investpy.get_index_historical_data(
                    index=index_name,
                    country=country,
                    from_date=start_date.strftime("%d/%m/%Y"),
                    to_date=end_date.strftime("%d/%m/%Y"),
                )
            
            df = await self._run_sync(fetch_history)
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            if df is None or df.empty:
                return []
            
            bars = []
            for idx, row in df.iterrows():
                timestamp = idx.to_pydatetime()
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                
                bar = OHLCV(
                    symbol=index_name.upper(),
                    timestamp=timestamp,
                    open=Decimal(str(row.get("Open", 0))),
                    high=Decimal(str(row.get("High", 0))),
                    low=Decimal(str(row.get("Low", 0))),
                    close=Decimal(str(row.get("Close", 0))),
                    volume=int(row.get("Volume", 0) or 0),
                    provider="investing",
                    timeframe=TimeFrame.DAY,
                )
                bars.append(bar)
            
            self._record_success(latency_ms)
            return bars
            
        except Exception as e:
            self._record_error(e)
            raise ProviderError("investing", f"Error fetching index history: {e}")
    
    # ==================== ETF Methods ====================
    
    async def get_etf_historical(
        self,
        etf_name: str,
        start_date: date,
        end_date: Optional[date] = None,
        country: str = "united states",
    ) -> list[OHLCV]:
        """Get historical ETF data."""
        country = country.lower()
        
        if end_date is None:
            end_date = date.today()
        
        try:
            def fetch_history():
                return self._investpy.get_etf_historical_data(
                    etf=etf_name,
                    country=country,
                    from_date=start_date.strftime("%d/%m/%Y"),
                    to_date=end_date.strftime("%d/%m/%Y"),
                )
            
            df = await self._run_sync(fetch_history)
            
            if df is None or df.empty:
                return []
            
            bars = []
            for idx, row in df.iterrows():
                timestamp = idx.to_pydatetime()
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                
                bar = OHLCV(
                    symbol=etf_name.upper(),
                    timestamp=timestamp,
                    open=Decimal(str(row.get("Open", 0))),
                    high=Decimal(str(row.get("High", 0))),
                    low=Decimal(str(row.get("Low", 0))),
                    close=Decimal(str(row.get("Close", 0))),
                    volume=int(row.get("Volume", 0) or 0),
                    provider="investing",
                    timeframe=TimeFrame.DAY,
                )
                bars.append(bar)
            
            return bars
            
        except Exception as e:
            raise ProviderError("investing", f"Error fetching ETF history: {e}")
    
    # ==================== Search Methods ====================
    
    async def search_symbols(self, query: str, country: str = "italy") -> list[dict[str, Any]]:
        """Search for stocks in a specific country."""
        country = country.lower()
        
        try:
            def search():
                return self._investpy.search_stocks(by="name", value=query)
            
            results_df = await self._run_sync(search)
            
            if results_df is None or results_df.empty:
                return []
            
            results = []
            for _, row in results_df.iterrows():
                if row.get("country", "").lower() == country or not country:
                    results.append({
                        "symbol": row.get("symbol"),
                        "name": row.get("name"),
                        "full_name": row.get("full_name"),
                        "country": row.get("country"),
                        "currency": row.get("currency"),
                        "type": "stock",
                    })
            
            return results[:20]  # Limit results
            
        except Exception as e:
            logger.warning(f"Search failed: {e}")
            return []
    
    async def get_stocks_list(self, country: str = "italy") -> list[dict[str, Any]]:
        """Get list of all stocks for a country."""
        country = country.lower()
        
        try:
            def get_stocks():
                return self._investpy.get_stocks(country=country)
            
            df = await self._run_sync(get_stocks)
            
            if df is None or df.empty:
                return []
            
            stocks = []
            for _, row in df.iterrows():
                stocks.append({
                    "symbol": row.get("symbol"),
                    "name": row.get("name"),
                    "full_name": row.get("full_name"),
                    "country": country,
                    "currency": row.get("currency"),
                })
            
            return stocks
            
        except Exception as e:
            logger.warning(f"Failed to get stocks list: {e}")
            return []
    
    async def get_indices_list(self, country: str = "italy") -> list[dict[str, Any]]:
        """Get list of indices for a country."""
        country = country.lower()
        
        try:
            def get_indices():
                return self._investpy.get_indices(country=country)
            
            df = await self._run_sync(get_indices)
            
            if df is None or df.empty:
                return []
            
            indices = []
            for _, row in df.iterrows():
                indices.append({
                    "name": row.get("name"),
                    "full_name": row.get("full_name"),
                    "symbol": row.get("symbol"),
                    "country": country,
                    "currency": row.get("currency"),
                })
            
            return indices
            
        except Exception as e:
            logger.warning(f"Failed to get indices list: {e}")
            return []
