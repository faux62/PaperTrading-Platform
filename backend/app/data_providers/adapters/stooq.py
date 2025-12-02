"""
Stooq Adapter

Provides access to Stooq.com market data via CSV bulk downloads.
Free access with comprehensive historical data.

Website: https://stooq.com/
"""
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from typing import Optional, Any
import aiohttp
from io import StringIO
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


STOOQ_BASE_URL = "https://stooq.com/q/d/l/"


# Symbol suffix mapping for different markets
STOOQ_MARKET_SUFFIXES = {
    "US": ".US",
    "UK": ".UK",
    "DE": ".DE",
    "FR": ".FR",
    "JP": ".JP",
    "HK": ".HK",
    "PL": "",  # Polish market is default (no suffix)
}


def create_stooq_config() -> ProviderConfig:
    """Create configuration for Stooq adapter."""
    return ProviderConfig(
        name="stooq",
        api_key="",  # No API key needed
        base_url=STOOQ_BASE_URL,
        requests_per_minute=30,  # Self-imposed limit
        requests_per_day=5000,
        max_symbols_per_request=1,  # CSV download is per symbol
        cost_per_request=Decimal("0"),
        daily_budget=Decimal("0"),
        timeout_seconds=60.0,  # Longer for bulk downloads
        retry_attempts=3,
        retry_delay=2.0,
        supports_websocket=False,
        supports_batch=False,
        supports_historical=True,
        supported_markets=[
            MarketType.US_STOCK,
            MarketType.EU_STOCK,
            MarketType.ASIA_STOCK,
            MarketType.INDEX,
            MarketType.FOREX,
            MarketType.COMMODITY,
        ],
        supported_data_types=[DataType.OHLCV],
        priority=65,  # Medium-low priority
    )


class StooqAdapter(BaseAdapter):
    """
    Stooq.com data provider adapter.
    
    Features:
    - Free historical data
    - Global market coverage
    - CSV bulk downloads
    - Long historical periods
    
    Limitations:
    - No real-time quotes
    - Daily data only
    - One symbol per request
    
    Symbol formats:
    - US stocks: AAPL.US
    - UK stocks: BP.UK
    - German stocks: SAP.DE
    - Indices: ^SPX, ^DJI, ^FTSE
    - Forex: EURUSD
    
    Usage:
        config = create_stooq_config()
        adapter = StooqAdapter(config)
        await adapter.initialize()
        
        bars = await adapter.get_historical("AAPL.US", start_date, end_date)
    """
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self) -> None:
        """Initialize HTTP session."""
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            self._session = aiohttp.ClientSession(timeout=timeout)
            logger.info("Stooq adapter initialized")
    
    async def close(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
        logger.info("Stooq adapter closed")
    
    async def health_check(self) -> bool:
        """Check connectivity to Stooq."""
        try:
            # Test with a known symbol
            url = f"{STOOQ_BASE_URL}"
            params = {"s": "aapl.us", "d1": "20231201", "d2": "20231201"}
            
            async with self._session.get(url, params=params) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Stooq health check failed: {e}")
            return False
    
    # ==================== Historical Data ====================
    
    async def get_quote(self, symbol: str) -> Quote:
        """
        Get latest quote (uses most recent historical data).
        
        Stooq doesn't provide real-time quotes, so we fetch
        the most recent historical data point.
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=7)
        
        bars = await self.get_historical(symbol, start_date, end_date)
        
        if not bars:
            raise DataNotAvailableError("stooq", symbol, "quote")
        
        # Use latest bar as quote
        latest = bars[-1]
        
        prev_close = bars[-2].close if len(bars) > 1 else None
        change = latest.close - prev_close if prev_close else None
        change_pct = (change / prev_close * 100) if change and prev_close else None
        
        market_type = self._determine_market_type(symbol)
        
        return Quote(
            symbol=symbol.upper(),
            price=latest.close,
            bid=None,
            ask=None,
            bid_size=None,
            ask_size=None,
            volume=latest.volume,
            timestamp=latest.timestamp,
            provider="stooq",
            market_type=market_type,
            change=change,
            change_percent=change_pct,
            day_high=latest.high,
            day_low=latest.low,
            day_open=latest.open,
            prev_close=prev_close,
        )
    
    async def get_quotes(self, symbols: list[str]) -> list[Quote]:
        """Get quotes for multiple symbols (sequential)."""
        quotes = []
        
        for symbol in symbols:
            try:
                quote = await self.get_quote(symbol)
                quotes.append(quote)
            except (DataNotAvailableError, ProviderError) as e:
                logger.warning(f"Failed to get Stooq quote for {symbol}: {e}")
        
        return quotes
    
    async def get_historical(
        self,
        symbol: str,
        start_date: date,
        end_date: Optional[date] = None,
        timeframe: TimeFrame = TimeFrame.DAY,
    ) -> list[OHLCV]:
        """
        Get historical data via CSV download.
        
        Note: Stooq only provides daily data.
        """
        symbol = symbol.lower()
        
        if end_date is None:
            end_date = date.today()
        
        # Stooq only supports daily
        if timeframe != TimeFrame.DAY:
            logger.warning("Stooq only supports daily data")
        
        # Format dates for Stooq (YYYYMMDD)
        d1 = start_date.strftime("%Y%m%d")
        d2 = end_date.strftime("%Y%m%d")
        
        url = STOOQ_BASE_URL
        params = {
            "s": symbol,
            "d1": d1,
            "d2": d2,
        }
        
        try:
            start_time = datetime.now()
            async with self._session.get(url, params=params) as response:
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    csv_content = await response.text()
                    
                    if not csv_content or "No data" in csv_content or len(csv_content) < 50:
                        return []
                    
                    bars = self._parse_csv(symbol.upper(), csv_content)
                    self._record_success(latency_ms)
                    return bars
                    
                else:
                    logger.warning(f"Stooq returned status {response.status}")
                    return []
                    
        except aiohttp.ClientError as e:
            self._record_error(e)
            raise ProviderError("stooq", f"Connection error: {e}")
    
    def _parse_csv(self, symbol: str, csv_content: str) -> list[OHLCV]:
        """Parse Stooq CSV response."""
        bars = []
        
        try:
            lines = csv_content.strip().split('\n')
            
            if len(lines) < 2:
                return []
            
            # Skip header line
            for line in lines[1:]:
                if not line.strip():
                    continue
                
                try:
                    parts = line.split(',')
                    
                    if len(parts) < 5:
                        continue
                    
                    # Format: Date,Open,High,Low,Close,Volume
                    date_str = parts[0].strip()
                    
                    # Parse date (YYYY-MM-DD or YYYYMMDD)
                    if '-' in date_str:
                        timestamp = datetime.strptime(date_str, "%Y-%m-%d")
                    else:
                        timestamp = datetime.strptime(date_str, "%Y%m%d")
                    
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                    
                    open_price = Decimal(parts[1].strip()) if parts[1].strip() else Decimal(0)
                    high = Decimal(parts[2].strip()) if parts[2].strip() else Decimal(0)
                    low = Decimal(parts[3].strip()) if parts[3].strip() else Decimal(0)
                    close = Decimal(parts[4].strip()) if parts[4].strip() else Decimal(0)
                    volume = int(float(parts[5].strip())) if len(parts) > 5 and parts[5].strip() else 0
                    
                    bar = OHLCV(
                        symbol=symbol,
                        timestamp=timestamp,
                        open=open_price,
                        high=high,
                        low=low,
                        close=close,
                        volume=volume,
                        provider="stooq",
                        timeframe=TimeFrame.DAY,
                    )
                    bars.append(bar)
                    
                except (ValueError, IndexError) as e:
                    logger.debug(f"Failed to parse Stooq line: {line} - {e}")
                    continue
            
            # Sort by timestamp
            bars.sort(key=lambda x: x.timestamp)
            return bars
            
        except Exception as e:
            logger.warning(f"Failed to parse Stooq CSV: {e}")
            return []
    
    def _determine_market_type(self, symbol: str) -> MarketType:
        """Determine market type from symbol suffix."""
        symbol_upper = symbol.upper()
        
        if symbol_upper.endswith(".US"):
            return MarketType.US_STOCK
        elif symbol_upper.endswith(".UK"):
            return MarketType.EU_STOCK
        elif symbol_upper.endswith(".DE") or symbol_upper.endswith(".FR"):
            return MarketType.EU_STOCK
        elif symbol_upper.endswith(".JP") or symbol_upper.endswith(".HK"):
            return MarketType.ASIA_STOCK
        elif symbol_upper.startswith("^"):
            return MarketType.INDEX
        elif len(symbol_upper) == 6 and symbol_upper.isalpha():
            return MarketType.FOREX
        else:
            return MarketType.US_STOCK
    
    # ==================== Utility Methods ====================
    
    def format_symbol(self, symbol: str, market: str = "US") -> str:
        """
        Format symbol with appropriate market suffix.
        
        Args:
            symbol: Base symbol (e.g., "AAPL")
            market: Market code (US, UK, DE, FR, JP, HK, PL)
            
        Returns:
            Formatted symbol (e.g., "AAPL.US")
        """
        suffix = STOOQ_MARKET_SUFFIXES.get(market.upper(), ".US")
        return f"{symbol.upper()}{suffix}"
    
    async def search_symbols(self, query: str) -> list[dict[str, Any]]:
        """
        Search is not supported by Stooq.
        Returns empty list.
        """
        return []
    
    async def get_index_symbols(self) -> dict[str, str]:
        """
        Get common index symbols for Stooq.
        
        Returns:
            Dict mapping index names to Stooq symbols
        """
        return {
            "S&P 500": "^SPX",
            "Dow Jones": "^DJI",
            "NASDAQ": "^NDQ",
            "FTSE 100": "^FTM",
            "DAX": "^DAX",
            "CAC 40": "^CAC",
            "Nikkei 225": "^NKX",
            "Hang Seng": "^HSI",
            "FTSE MIB": "^MIB",
            "IBEX 35": "^IBEX",
            "Euro Stoxx 50": "^SX5E",
        }
    
    async def bulk_download(
        self,
        symbols: list[str],
        start_date: date,
        end_date: Optional[date] = None,
    ) -> dict[str, list[OHLCV]]:
        """
        Bulk download historical data for multiple symbols.
        
        Args:
            symbols: List of symbols
            start_date: Start date
            end_date: End date (defaults to today)
            
        Returns:
            Dict mapping symbols to their OHLCV data
        """
        import asyncio
        
        if end_date is None:
            end_date = date.today()
        
        results = {}
        
        # Process with delay to be respectful
        for symbol in symbols:
            try:
                bars = await self.get_historical(symbol, start_date, end_date)
                results[symbol] = bars
                await asyncio.sleep(0.3)  # Small delay between requests
            except Exception as e:
                logger.warning(f"Failed to download {symbol}: {e}")
                results[symbol] = []
        
        return results
