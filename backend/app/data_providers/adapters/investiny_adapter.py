"""
Investiny Adapter

Provides access to Investing.com data using tvc6.investing.com API directly.
This is a custom implementation inspired by investiny library but without
the dependency conflicts (httpx/pydantic version issues).

Uses UUID in URL path to bypass Cloudflare (same technique as investiny).

Supports historical data and quotes for global markets.
"""
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from typing import Optional, Any
from uuid import uuid4
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


# TradingView-compatible API endpoint used by Investing.com
TVC_BASE_URL = "https://tvc6.investing.com"
SEARCH_URL = "https://api.investing.com/api/search/v2/search"

# Cache for investing IDs (symbol -> investing_id)
_ID_CACHE: dict[str, int] = {}


def create_investiny_config() -> ProviderConfig:
    """Create configuration for Investiny adapter."""
    return ProviderConfig(
        name="investiny",
        api_key="",  # No API key needed
        base_url=TVC_BASE_URL,
        requests_per_minute=30,
        requests_per_day=2000,
        max_symbols_per_request=1,
        cost_per_request=Decimal("0"),
        daily_budget=Decimal("0"),
        timeout_seconds=30.0,
        retry_attempts=3,
        retry_delay=2.0,
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
        priority=65,
    )


class InvestinyAdapter(BaseAdapter):
    """Adapter for Investing.com data via TVC API."""
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None
    
    def _get_headers(self) -> dict:
        """Get headers that bypass Cloudflare."""
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.102 Safari/537.36",
            "Referer": "https://tvc-invdn-com.investing.com/",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
    
    def _get_tvc_url(self, endpoint: str) -> str:
        """Generate TVC URL with random UUID to bypass caching/blocking."""
        return f"{TVC_BASE_URL}/{uuid4().hex}/0/0/0/0/{endpoint}"
    
    async def initialize(self) -> None:
        """Initialize HTTP session."""
        if not self._session:
            self._session = aiohttp.ClientSession(headers=self._get_headers())
        logger.info("Investiny adapter initialized")
    
    async def close(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
        logger.info("Investiny adapter closed")
    
    async def health_check(self) -> bool:
        """Check connectivity."""
        try:
            investing_id = await self._get_investing_id("AAPL")
            return investing_id is not None
        except Exception as e:
            logger.error(f"Investiny health check failed: {e}")
            return False
    
    async def _search_asset(self, query: str) -> list[dict]:
        """Search for an asset on Investing.com."""
        try:
            params = {"q": query, "t": "Equities"}
            async with self._session.get(SEARCH_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    # Extract quotes from search results
                    quotes = data.get("quotes", [])
                    return quotes
                return []
        except Exception as e:
            logger.warning(f"Search failed for {query}: {e}")
            return []
    
    async def _get_investing_id(self, symbol: str, asset_type: str = "Stock") -> Optional[int]:
        """Get Investing.com ID for a symbol."""
        cache_key = f"{symbol}:{asset_type}"
        
        if cache_key in _ID_CACHE:
            return _ID_CACHE[cache_key]
        
        try:
            results = await self._search_asset(symbol)
            if results:
                # Find best match
                for r in results:
                    r_symbol = r.get("symbol", "").upper()
                    if r_symbol == symbol.upper():
                        investing_id = r.get("id")
                        if investing_id:
                            _ID_CACHE[cache_key] = int(investing_id)
                            return int(investing_id)
                
                # Use first result
                investing_id = results[0].get("id")
                if investing_id:
                    _ID_CACHE[cache_key] = int(investing_id)
                    return int(investing_id)
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to get investing ID for {symbol}: {e}")
            return None
    
    async def _request_history(self, investing_id: int, from_ts: int, to_ts: int, resolution: str = "D") -> dict:
        """Make request to TVC history endpoint with UUID bypass."""
        url = self._get_tvc_url("history")
        params = {
            "symbol": investing_id,
            "from": from_ts,
            "to": to_ts,
            "resolution": resolution,
        }
        
        async with self._session.get(url, params=params) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise ProviderError("investiny", f"API error {response.status}")
    
    # ==================== Quote Methods ====================
    
    async def get_quote(self, symbol: str) -> Quote:
        """Get latest quote using historical data endpoint."""
        symbol = symbol.upper()
        
        try:
            start_time = datetime.now()
            
            investing_id = await self._get_investing_id(symbol)
            if not investing_id:
                raise DataNotAvailableError("investiny", symbol, "quote")
            
            # Get last few days to ensure we have data
            to_ts = int(datetime.now().timestamp())
            from_ts = int((datetime.now() - timedelta(days=5)).timestamp())
            
            data = await self._request_history(investing_id, from_ts, to_ts, "D")
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            if data.get("s") != "ok" or not data.get("c"):
                raise DataNotAvailableError("investiny", symbol, "quote")
            
            # Get most recent data
            closes = data.get("c", [])
            opens = data.get("o", [])
            highs = data.get("h", [])
            lows = data.get("l", [])
            volumes = data.get("v", [])
            
            if not closes:
                raise DataNotAvailableError("investiny", symbol, "quote")
            
            idx = -1  # Last data point
            quote = Quote(
                symbol=symbol,
                price=Decimal(str(closes[idx])),
                bid=None,
                ask=None,
                bid_size=None,
                ask_size=None,
                volume=int(volumes[idx]) if volumes else 0,
                timestamp=datetime.now(timezone.utc),
                provider="investiny",
                market_type=self._determine_market_type(symbol),
                change=Decimal(str(closes[idx] - opens[idx])) if opens else None,
                change_percent=Decimal(str((closes[idx] - opens[idx]) / opens[idx] * 100)) if opens and opens[idx] else None,
                day_high=Decimal(str(highs[idx])) if highs else None,
                day_low=Decimal(str(lows[idx])) if lows else None,
                day_open=Decimal(str(opens[idx])) if opens else None,
                prev_close=Decimal(str(closes[idx-1])) if len(closes) > 1 else None,
            )
            
            self._record_success(latency_ms)
            return quote
                    
        except DataNotAvailableError:
            raise
        except Exception as e:
            self._record_error(e)
            raise ProviderError("investiny", f"Error fetching quote: {e}")
    
    async def get_quotes(self, symbols: list[str]) -> list[Quote]:
        """Get quotes for multiple symbols."""
        quotes = []
        for symbol in symbols:
            try:
                quote = await self.get_quote(symbol)
                quotes.append(quote)
            except Exception as e:
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
        """Get historical OHLCV data."""
        symbol = symbol.upper()
        end_date = end_date or date.today()
        
        try:
            start_time = datetime.now()
            
            investing_id = await self._get_investing_id(symbol)
            if not investing_id:
                raise DataNotAvailableError("investiny", symbol, "historical")
            
            from_ts = int(datetime.combine(start_date, datetime.min.time()).timestamp())
            to_ts = int(datetime.combine(end_date, datetime.max.time()).timestamp())
            
            interval = self._map_timeframe(timeframe)
            
            # Use the UUID bypass method
            data = await self._request_history(investing_id, from_ts, to_ts, interval)
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            if data.get("s") != "ok":
                return []
            
            bars = self._parse_tvc_data(symbol, data, timeframe)
            self._record_success(latency_ms)
            return bars
                    
        except DataNotAvailableError:
            raise
        except Exception as e:
            self._record_error(e)
            raise ProviderError("investiny", f"Error fetching historical: {e}")
    
    def _map_timeframe(self, timeframe: TimeFrame) -> str:
        """Map TimeFrame to TVC interval."""
        mapping = {
            TimeFrame.MINUTE_1: "1",
            TimeFrame.MINUTE_5: "5",
            TimeFrame.MINUTE_15: "15",
            TimeFrame.MINUTE_30: "30",
            TimeFrame.HOUR: "60",
            TimeFrame.HOUR_4: "240",
            TimeFrame.DAY: "D",
            TimeFrame.WEEK: "W",
            TimeFrame.MONTH: "M",
        }
        return mapping.get(timeframe, "D")
    
    def _parse_tvc_data(self, symbol: str, data: dict, timeframe: TimeFrame) -> list[OHLCV]:
        """Parse TVC API response to OHLCV list."""
        bars = []
        
        timestamps = data.get("t", [])
        opens = data.get("o", [])
        highs = data.get("h", [])
        lows = data.get("l", [])
        closes = data.get("c", [])
        volumes = data.get("v", [])
        
        for i in range(len(timestamps)):
            try:
                bar = OHLCV(
                    symbol=symbol,
                    timestamp=datetime.fromtimestamp(timestamps[i], tz=timezone.utc),
                    open=Decimal(str(opens[i] if i < len(opens) else 0)),
                    high=Decimal(str(highs[i] if i < len(highs) else 0)),
                    low=Decimal(str(lows[i] if i < len(lows) else 0)),
                    close=Decimal(str(closes[i] if i < len(closes) else 0)),
                    volume=int(volumes[i] if i < len(volumes) else 0),
                    timeframe=timeframe,
                    provider="investiny",
                )
                bars.append(bar)
            except Exception as e:
                logger.warning(f"Failed to parse bar at index {i}: {e}")
        
        return bars
    
    def _determine_market_type(self, symbol: str) -> MarketType:
        """Determine market type from symbol format."""
        symbol_upper = symbol.upper()
        
        if ".MI" in symbol_upper or ".PA" in symbol_upper or ".DE" in symbol_upper:
            return MarketType.EU_STOCK
        elif ".L" in symbol_upper or ".AS" in symbol_upper or ".MC" in symbol_upper:
            return MarketType.EU_STOCK
        elif ".HK" in symbol_upper or ".T" in symbol_upper:
            return MarketType.ASIA_STOCK
        elif "/" in symbol_upper:
            return MarketType.FOREX
        elif "-USD" in symbol_upper or "BTC" in symbol_upper or "ETH" in symbol_upper:
            return MarketType.CRYPTO
        elif symbol_upper.startswith("^"):
            return MarketType.INDEX
        else:
            return MarketType.US_STOCK
