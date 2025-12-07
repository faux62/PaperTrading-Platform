"""
NASDAQ Adapter

Provides access to NASDAQ official API for US stocks and ETFs.
Free, no API key required. Supports quotes and historical OHLCV data.

Endpoints:
- /api/quote/{symbol}/info - Real-time quote
- /api/quote/{symbol}/historical - Historical OHLCV data
"""
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from typing import Optional
import aiohttp
import re
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


BASE_URL = "https://api.nasdaq.com/api/quote"


def create_nasdaq_config() -> ProviderConfig:
    """Create configuration for NASDAQ adapter."""
    return ProviderConfig(
        name="nasdaq",
        api_key="",  # No API key needed
        base_url=BASE_URL,
        requests_per_minute=30,
        requests_per_day=5000,
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
            MarketType.US_STOCK,
            MarketType.ETF,
        ],
        supported_data_types=[DataType.QUOTE, DataType.OHLCV],
        priority=55,  # Good priority - free and reliable
    )


class NasdaqAdapter(BaseAdapter):
    """Adapter for NASDAQ official API."""
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None
    
    def _get_headers(self) -> dict:
        """Get headers for NASDAQ API requests."""
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
        }
    
    async def initialize(self) -> None:
        """Initialize HTTP session."""
        if not self._session:
            self._session = aiohttp.ClientSession(headers=self._get_headers())
        logger.info("NASDAQ adapter initialized")
    
    async def close(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
        logger.info("NASDAQ adapter closed")
    
    async def health_check(self) -> bool:
        """Check connectivity."""
        try:
            quote = await self.get_quote("AAPL")
            return quote is not None
        except Exception as e:
            logger.error(f"NASDAQ health check failed: {e}")
            return False
    
    def _get_asset_class(self, symbol: str) -> str:
        """Determine asset class for symbol."""
        # Common ETFs
        etf_symbols = {
            "SPY", "QQQ", "IWM", "DIA", "VTI", "VOO", "VEA", "VWO",
            "EEM", "GLD", "SLV", "TLT", "IEF", "LQD", "HYG", "XLF",
            "XLK", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLRE",
            "VNQ", "ARKK", "ARKG", "ARKW", "SOXX", "SMH", "XBI",
        }
        if symbol.upper() in etf_symbols:
            return "etf"
        return "stocks"
    
    def _parse_price(self, price_str: str) -> Optional[Decimal]:
        """Parse price string like '$278.78' to Decimal."""
        if not price_str or price_str == "N/A":
            return None
        # Remove $ and commas
        clean = re.sub(r'[$,]', '', price_str.strip())
        try:
            return Decimal(clean)
        except:
            return None
    
    def _parse_volume(self, vol_str: str) -> int:
        """Parse volume string like '47,265,845' to int."""
        if not vol_str or vol_str == "N/A":
            return 0
        clean = re.sub(r'[,]', '', vol_str.strip())
        try:
            return int(clean)
        except:
            return 0
    
    def _parse_change(self, change_str: str) -> Optional[Decimal]:
        """Parse change string like '+1.30' or '-1.92' to Decimal."""
        if not change_str or change_str == "N/A":
            return None
        clean = change_str.strip().replace('+', '')
        try:
            return Decimal(clean)
        except:
            return None
    
    def _parse_percent(self, pct_str: str) -> Optional[Decimal]:
        """Parse percentage string like '+0.19%' to Decimal."""
        if not pct_str or pct_str == "N/A":
            return None
        clean = re.sub(r'[%+]', '', pct_str.strip())
        try:
            return Decimal(clean)
        except:
            return None
    
    # ==================== Quote Methods ====================
    
    async def get_quote(self, symbol: str) -> Quote:
        """Get real-time quote for symbol."""
        symbol = symbol.upper()
        asset_class = self._get_asset_class(symbol)
        
        try:
            start_time = datetime.now()
            url = f"{BASE_URL}/{symbol}/info?assetclass={asset_class}"
            
            async with self._session.get(url) as response:
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    data = await response.json()
                    
                    if not data.get("data"):
                        raise DataNotAvailableError("nasdaq", symbol, "quote")
                    
                    quote_data = data["data"]
                    primary = quote_data.get("primaryData", {})
                    key_stats = quote_data.get("keyStats", {})
                    
                    price = self._parse_price(primary.get("lastSalePrice"))
                    if not price:
                        raise DataNotAvailableError("nasdaq", symbol, "quote")
                    
                    # Parse day range from keyStats
                    day_high = None
                    day_low = None
                    if key_stats and key_stats.get("dayrange"):
                        day_range = key_stats["dayrange"].get("value", "")
                        if " - " in day_range:
                            parts = day_range.split(" - ")
                            if len(parts) == 2:
                                day_low = self._parse_price(parts[0])
                                day_high = self._parse_price(parts[1])
                    
                    quote = Quote(
                        symbol=symbol,
                        price=price,
                        bid=self._parse_price(primary.get("bidPrice")),
                        ask=self._parse_price(primary.get("askPrice")),
                        bid_size=None,
                        ask_size=None,
                        volume=self._parse_volume(primary.get("volume")),
                        timestamp=datetime.now(timezone.utc),
                        provider="nasdaq",
                        market_type=MarketType.ETF if asset_class == "etf" else MarketType.US_STOCK,
                        change=self._parse_change(primary.get("netChange")),
                        change_percent=self._parse_percent(primary.get("percentageChange")),
                        day_high=day_high,
                        day_low=day_low,
                        day_open=None,  # Not provided in info endpoint
                        prev_close=None,  # Calculate from price - change if needed
                    )
                    
                    # Calculate prev_close from price and change
                    if quote.change is not None:
                        quote.prev_close = price - quote.change
                    
                    self._record_success(latency_ms)
                    return quote
                else:
                    raise ProviderError("nasdaq", f"API error {response.status}")
                    
        except DataNotAvailableError:
            raise
        except Exception as e:
            self._record_error(e)
            raise ProviderError("nasdaq", f"Error fetching quote: {e}")
    
    async def get_quotes(self, symbols: list[str]) -> list[Quote]:
        """Get quotes for multiple symbols."""
        quotes = []
        for symbol in symbols:
            try:
                quote = await self.get_quote(symbol)
                quotes.append(quote)
            except Exception as e:
                logger.warning(f"NASDAQ: Failed to get quote for {symbol}: {e}")
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
        asset_class = self._get_asset_class(symbol)
        
        # NASDAQ API only supports daily data
        if timeframe not in (TimeFrame.DAY, TimeFrame.WEEK, TimeFrame.MONTH):
            logger.warning(f"NASDAQ only supports daily data, requested: {timeframe}")
        
        try:
            start_time = datetime.now()
            
            # Calculate limit based on date range
            days = (end_date - start_date).days + 1
            limit = min(days * 2, 500)  # Account for weekends, max 500
            
            url = f"{BASE_URL}/{symbol}/historical"
            params = {
                "assetclass": asset_class,
                "fromdate": start_date.strftime("%Y-%m-%d"),
                "todate": end_date.strftime("%Y-%m-%d"),
                "limit": limit,
            }
            
            async with self._session.get(url, params=params) as response:
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    data = await response.json()
                    
                    if not data.get("data") or not data["data"].get("tradesTable"):
                        return []
                    
                    rows = data["data"]["tradesTable"].get("rows", [])
                    bars = []
                    
                    for row in rows:
                        try:
                            # Parse date (format: "12/05/2025")
                            date_str = row.get("date", "")
                            bar_date = datetime.strptime(date_str, "%m/%d/%Y")
                            
                            # Filter by date range
                            if bar_date.date() < start_date or bar_date.date() > end_date:
                                continue
                            
                            bar = OHLCV(
                                symbol=symbol,
                                timestamp=bar_date.replace(tzinfo=timezone.utc),
                                open=self._parse_price(row.get("open")) or Decimal("0"),
                                high=self._parse_price(row.get("high")) or Decimal("0"),
                                low=self._parse_price(row.get("low")) or Decimal("0"),
                                close=self._parse_price(row.get("close")) or Decimal("0"),
                                volume=self._parse_volume(row.get("volume")),
                                timeframe=TimeFrame.DAY,
                                provider="nasdaq",
                            )
                            bars.append(bar)
                        except Exception as e:
                            logger.warning(f"NASDAQ: Failed to parse row: {e}")
                    
                    # Sort by date ascending
                    bars.sort(key=lambda x: x.timestamp)
                    
                    self._record_success(latency_ms)
                    return bars
                else:
                    raise ProviderError("nasdaq", f"API error {response.status}")
                    
        except Exception as e:
            self._record_error(e)
            raise ProviderError("nasdaq", f"Error fetching historical: {e}")
    
    def _determine_market_type(self, symbol: str) -> MarketType:
        """Determine market type from symbol."""
        if self._get_asset_class(symbol) == "etf":
            return MarketType.ETF
        return MarketType.US_STOCK
