"""
yfinance Adapter

Provides access to Yahoo Finance data via yfinance library.
Free unlimited access but requires respectful rate limiting.

Note: yfinance is a scraping wrapper, use responsibly.
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
    RateLimitError,
    DataNotAvailableError,
)


def create_yfinance_config() -> ProviderConfig:
    """Create configuration for yfinance adapter."""
    return ProviderConfig(
        name="yfinance",
        api_key="",  # No API key needed
        base_url="",
        requests_per_minute=30,  # Self-imposed limit
        requests_per_day=10000,  # Self-imposed limit
        max_symbols_per_request=50,
        cost_per_request=Decimal("0"),
        daily_budget=Decimal("0"),
        timeout_seconds=30.0,
        retry_attempts=3,
        retry_delay=2.0,  # Longer delay for scraping
        supports_websocket=False,
        supports_batch=True,
        supports_historical=True,
        supported_markets=[
            MarketType.US_STOCK,
            MarketType.EU_STOCK,
            MarketType.ASIA_STOCK,
            MarketType.CRYPTO,
            MarketType.ETF,
            MarketType.INDEX,
        ],
        supported_data_types=[DataType.QUOTE, DataType.OHLCV],
        priority=60,  # Lower priority due to scraping nature
    )


class YFinanceAdapter(BaseAdapter):
    """
    yfinance data provider adapter.
    
    Features:
    - Free unlimited access
    - Historical data from 1962
    - Real-time quotes (delayed)
    - Company info and fundamentals
    - Global market coverage
    
    Limitations:
    - Scraping-based, may break
    - No official support
    - Rate limiting recommended
    
    Usage:
        config = create_yfinance_config()
        adapter = YFinanceAdapter(config)
        await adapter.initialize()
        
        quote = await adapter.get_quote("AAPL")
        bars = await adapter.get_historical("MSFT", start_date, end_date)
    """
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._executor = ThreadPoolExecutor(max_workers=5)
        self._yf = None
    
    async def initialize(self) -> None:
        """Initialize yfinance."""
        try:
            import yfinance as yf
            self._yf = yf
            logger.info("yfinance adapter initialized")
        except ImportError:
            raise ProviderError("yfinance", "yfinance library not installed. Run: pip install yfinance")
    
    async def close(self) -> None:
        """Close executor."""
        self._executor.shutdown(wait=False)
        logger.info("yfinance adapter closed")
    
    async def health_check(self) -> bool:
        """Check yfinance availability."""
        try:
            # Quick test with a known symbol
            ticker = self._yf.Ticker("AAPL")
            info = await self._run_sync(lambda: ticker.fast_info)
            return info is not None
        except Exception as e:
            logger.error(f"yfinance health check failed: {e}")
            return False
    
    async def _run_sync(self, func):
        """Run synchronous yfinance function in executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, func)
    
    # ==================== Quote Methods ====================
    
    async def get_quote(self, symbol: str) -> Quote:
        """Get latest quote for a symbol."""
        symbol = symbol.upper()
        
        try:
            start_time = datetime.now()
            
            def fetch_quote():
                ticker = self._yf.Ticker(symbol)
                return ticker.fast_info
            
            info = await self._run_sync(fetch_quote)
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            if info is None:
                raise DataNotAvailableError("yfinance", symbol, "quote")
            
            quote = self._parse_fast_info(symbol, info)
            self._record_success(latency_ms)
            return quote
            
        except Exception as e:
            self._record_error(e)
            if "No data found" in str(e) or "Invalid" in str(e):
                raise DataNotAvailableError("yfinance", symbol, "quote")
            raise ProviderError("yfinance", f"Error fetching quote: {e}")
    
    async def get_quotes(self, symbols: list[str]) -> list[Quote]:
        """Get quotes for multiple symbols."""
        if not symbols:
            return []
        
        symbols = [s.upper() for s in symbols]
        
        try:
            start_time = datetime.now()
            
            def fetch_quotes():
                tickers = self._yf.Tickers(" ".join(symbols))
                results = {}
                for symbol in symbols:
                    try:
                        ticker = tickers.tickers.get(symbol)
                        if ticker:
                            results[symbol] = ticker.fast_info
                    except Exception:
                        pass
                return results
            
            results = await self._run_sync(fetch_quotes)
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            quotes = []
            for symbol, info in results.items():
                try:
                    quote = self._parse_fast_info(symbol, info)
                    quotes.append(quote)
                except Exception as e:
                    logger.warning(f"Failed to parse quote for {symbol}: {e}")
            
            self._record_success(latency_ms)
            return quotes
            
        except Exception as e:
            self._record_error(e)
            raise ProviderError("yfinance", f"Error fetching quotes: {e}")
    
    # ==================== Historical Methods ====================
    
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
        
        # Map timeframe to yfinance interval
        interval_map = {
            TimeFrame.MINUTE: "1m",
            TimeFrame.FIVE_MIN: "5m",
            TimeFrame.FIFTEEN_MIN: "15m",
            TimeFrame.HOUR: "1h",
            TimeFrame.DAY: "1d",
            TimeFrame.WEEK: "1wk",
            TimeFrame.MONTH: "1mo",
        }
        
        interval = interval_map.get(timeframe, "1d")
        
        # Intraday data limited to last 60 days
        if timeframe in [TimeFrame.MINUTE, TimeFrame.FIVE_MIN, TimeFrame.FIFTEEN_MIN]:
            max_start = date.today() - timedelta(days=60)
            if start_date < max_start:
                start_date = max_start
                logger.warning(f"yfinance: Intraday data limited to 60 days, adjusted start date")
        
        try:
            start_time = datetime.now()
            
            def fetch_history():
                ticker = self._yf.Ticker(symbol)
                df = ticker.history(
                    start=start_date.isoformat(),
                    end=(end_date + timedelta(days=1)).isoformat(),
                    interval=interval,
                    auto_adjust=True,
                )
                return df
            
            df = await self._run_sync(fetch_history)
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            if df is None or df.empty:
                return []
            
            bars = []
            for idx, row in df.iterrows():
                try:
                    # Handle timezone-aware index
                    if hasattr(idx, 'to_pydatetime'):
                        timestamp = idx.to_pydatetime()
                    else:
                        timestamp = idx
                    
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
                        provider="yfinance",
                        timeframe=timeframe,
                    )
                    bars.append(bar)
                except Exception as e:
                    logger.warning(f"Failed to parse bar: {e}")
            
            self._record_success(latency_ms)
            return bars
            
        except Exception as e:
            self._record_error(e)
            raise ProviderError("yfinance", f"Error fetching history: {e}")
    
    # ==================== Info Methods ====================
    
    async def get_company_info(self, symbol: str) -> Optional[dict[str, Any]]:
        """Get company information."""
        symbol = symbol.upper()
        
        try:
            def fetch_info():
                ticker = self._yf.Ticker(symbol)
                return ticker.info
            
            info = await self._run_sync(fetch_info)
            
            if not info:
                return None
            
            return {
                "symbol": symbol,
                "name": info.get("longName") or info.get("shortName"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "description": info.get("longBusinessSummary"),
                "website": info.get("website"),
                "employees": info.get("fullTimeEmployees"),
                "country": info.get("country"),
                "city": info.get("city"),
                "address": info.get("address1"),
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "dividend_yield": info.get("dividendYield"),
                "beta": info.get("beta"),
                "52_week_high": info.get("fiftyTwoWeekHigh"),
                "52_week_low": info.get("fiftyTwoWeekLow"),
                "avg_volume": info.get("averageVolume"),
                "currency": info.get("currency"),
                "exchange": info.get("exchange"),
            }
            
        except Exception as e:
            logger.warning(f"Failed to get company info: {e}")
            return None
    
    async def search_symbols(self, query: str) -> list[dict[str, Any]]:
        """
        Search for symbols.
        
        Note: yfinance doesn't have native search.
        This is a limited implementation.
        """
        # yfinance doesn't support search directly
        # Try to get info for the exact symbol
        try:
            info = await self.get_company_info(query.upper())
            if info and info.get("name"):
                return [{
                    "symbol": query.upper(),
                    "name": info.get("name"),
                    "exchange": info.get("exchange"),
                    "type": "stock",
                }]
        except Exception:
            pass
        
        return []
    
    # ==================== Parsing Methods ====================
    
    def _parse_fast_info(self, symbol: str, info) -> Quote:
        """Parse fast_info to Quote."""
        # fast_info attributes use snake_case in modern yfinance
        try:
            last_price = Decimal(str(getattr(info, 'last_price', 0) or getattr(info, 'lastPrice', 0) or 0))
            prev_close = Decimal(str(getattr(info, 'previous_close', 0) or getattr(info, 'previousClose', 0) or 0))
            
            change = last_price - prev_close if prev_close else None
            change_pct = (change / prev_close * 100) if change and prev_close else None
            
            volume = int(getattr(info, 'last_volume', 0) or getattr(info, 'lastVolume', 0) or 0)
            
            day_high = Decimal(str(getattr(info, 'day_high', 0) or getattr(info, 'dayHigh', 0) or 0))
            day_low = Decimal(str(getattr(info, 'day_low', 0) or getattr(info, 'dayLow', 0) or 0))
            day_open = Decimal(str(getattr(info, 'open', 0) or 0))
            
            market_type = self._determine_market_type(symbol)
            
            return Quote(
                symbol=symbol,
                price=last_price,
                bid=None,
                ask=None,
                bid_size=None,
                ask_size=None,
                volume=volume,
                timestamp=datetime.now(timezone.utc),
                provider="yfinance",
                market_type=market_type,
                change=change,
                change_percent=change_pct,
                day_high=day_high if day_high else None,
                day_low=day_low if day_low else None,
                day_open=day_open if day_open else None,
                prev_close=prev_close if prev_close else None,
            )
            
        except Exception as e:
            logger.warning(f"Error parsing fast_info for {symbol}: {e}")
            # Return minimal quote
            return Quote(
                symbol=symbol,
                price=Decimal("0"),
                bid=None,
                ask=None,
                bid_size=None,
                ask_size=None,
                volume=0,
                timestamp=datetime.now(timezone.utc),
                provider="yfinance",
                market_type=MarketType.US_STOCK,
            )
    
    def _determine_market_type(self, symbol: str) -> MarketType:
        """Determine market type from symbol format."""
        # Basic heuristics
        if "-" in symbol and symbol.endswith("USD"):
            return MarketType.CRYPTO
        elif symbol.endswith(".L"):
            return MarketType.EU_STOCK  # London
        elif symbol.endswith(".PA") or symbol.endswith(".DE"):
            return MarketType.EU_STOCK  # Paris, Frankfurt
        elif symbol.endswith(".MI"):
            return MarketType.EU_STOCK  # Milan
        elif symbol.endswith(".T") or symbol.endswith(".HK"):
            return MarketType.ASIA_STOCK  # Tokyo, Hong Kong
        elif symbol.startswith("^"):
            return MarketType.INDEX
        else:
            return MarketType.US_STOCK
