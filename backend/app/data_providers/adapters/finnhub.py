"""
Finnhub Adapter

Provides access to Finnhub market data API for global stocks.
Supports REST API and WebSocket streaming.

API Documentation: https://finnhub.io/docs/api
Free tier: 60 API calls/minute, real-time US stock quotes
"""
import asyncio
import json
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from typing import Optional, AsyncIterator, Any
import aiohttp
import websockets
from websockets.asyncio.client import ClientConnection
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


FINNHUB_BASE_URL = "https://finnhub.io/api/v1"
FINNHUB_WS_URL = "wss://ws.finnhub.io"


def create_finnhub_config(api_key: str) -> ProviderConfig:
    """Create configuration for Finnhub adapter."""
    return ProviderConfig(
        name="finnhub",
        api_key=api_key,
        base_url=FINNHUB_BASE_URL,
        websocket_url=FINNHUB_WS_URL,
        requests_per_minute=60,  # Free tier limit
        requests_per_day=0,  # Unlimited
        max_symbols_per_request=1,  # No batch endpoint
        cost_per_request=Decimal("0"),
        daily_budget=Decimal("0"),
        timeout_seconds=30.0,
        retry_attempts=3,
        retry_delay=1.0,
        supports_websocket=True,
        supports_batch=False,
        supports_historical=True,
        supported_markets=[
            MarketType.US_STOCK,
            MarketType.EU_STOCK,
            MarketType.CRYPTO,
            MarketType.FOREX,
        ],
        supported_data_types=[DataType.QUOTE, DataType.OHLCV, DataType.NEWS],
        priority=30,
    )


class FinnhubAdapter(BaseAdapter):
    """
    Finnhub data provider adapter.
    
    Features:
    - Real-time quotes via REST and WebSocket
    - Historical candle data
    - Multi-market support (US, EU, Crypto, Forex)
    - Company news and fundamentals
    
    Usage:
        config = create_finnhub_config("your_api_key")
        adapter = FinnhubAdapter(config)
        await adapter.initialize()
        
        quote = await adapter.get_quote("AAPL")
        bars = await adapter.get_historical("AAPL", start_date, end_date)
    """
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[ClientConnection] = None
        self._ws_subscriptions: set[str] = set()
    
    async def initialize(self) -> None:
        """Initialize HTTP session."""
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            self._session = aiohttp.ClientSession(timeout=timeout)
            logger.info("Finnhub adapter initialized")
    
    async def close(self) -> None:
        """Close all connections."""
        if self._ws:
            await self._ws.close()
            self._ws = None
        
        if self._session:
            await self._session.close()
            self._session = None
        
        logger.info("Finnhub adapter closed")
    
    async def health_check(self) -> bool:
        """Check API connectivity."""
        try:
            url = f"{self.config.base_url}/quote"
            params = {"symbol": "AAPL", "token": self.config.api_key}
            
            async with self._session.get(url, params=params) as response:
                if response.status == 200:
                    return True
                elif response.status == 401:
                    logger.error("Finnhub authentication failed")
                    return False
                else:
                    logger.warning(f"Finnhub health check status: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Finnhub health check failed: {e}")
            return False
    
    # ==================== REST API Methods ====================
    
    async def get_quote(self, symbol: str) -> Quote:
        """Get latest quote for a symbol."""
        symbol = symbol.upper()
        url = f"{self.config.base_url}/quote"
        params = {"symbol": symbol, "token": self.config.api_key}
        
        try:
            start_time = datetime.now()
            async with self._session.get(url, params=params) as response:
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    data = await response.json()
                    
                    # Check if we got valid data
                    if data.get("c") is None or data.get("c") == 0:
                        raise DataNotAvailableError("finnhub", symbol, "quote")
                    
                    quote = self._parse_quote(symbol, data)
                    self._record_success(latency_ms)
                    return quote
                    
                elif response.status == 401:
                    raise AuthenticationError("finnhub")
                elif response.status == 429:
                    raise RateLimitError("finnhub", retry_after=60)
                else:
                    error_text = await response.text()
                    raise ProviderError("finnhub", f"API error {response.status}: {error_text}")
                    
        except aiohttp.ClientError as e:
            self._record_error(e)
            raise ProviderError("finnhub", f"Connection error: {e}")
    
    async def get_quotes(self, symbols: list[str]) -> list[Quote]:
        """Get quotes for multiple symbols (sequential, no batch API)."""
        quotes = []
        for symbol in symbols:
            try:
                quote = await self.get_quote(symbol)
                quotes.append(quote)
                # Small delay to respect rate limit
                await asyncio.sleep(0.1)
            except DataNotAvailableError:
                logger.warning(f"No data available for {symbol}")
            except Exception as e:
                logger.warning(f"Failed to get quote for {symbol}: {e}")
        return quotes
    
    async def get_historical(
        self,
        symbol: str,
        start_date: date,
        end_date: Optional[date] = None,
        timeframe: TimeFrame = TimeFrame.DAY,
    ) -> list[OHLCV]:
        """Get historical candle data."""
        symbol = symbol.upper()
        
        if end_date is None:
            end_date = date.today()
        
        # Convert to Unix timestamps
        start_ts = int(datetime.combine(start_date, datetime.min.time()).timestamp())
        end_ts = int(datetime.combine(end_date, datetime.max.time()).timestamp())
        
        # Convert timeframe to Finnhub resolution
        resolution_map = {
            TimeFrame.MINUTE_1: "1",
            TimeFrame.MINUTE_5: "5",
            TimeFrame.MINUTE_15: "15",
            TimeFrame.MINUTE_30: "30",
            TimeFrame.HOUR_1: "60",
            TimeFrame.DAY: "D",
            TimeFrame.WEEK: "W",
            TimeFrame.MONTH: "M",
        }
        resolution = resolution_map.get(timeframe, "D")
        
        url = f"{self.config.base_url}/stock/candle"
        params = {
            "symbol": symbol,
            "resolution": resolution,
            "from": start_ts,
            "to": end_ts,
            "token": self.config.api_key,
        }
        
        try:
            start_time = datetime.now()
            async with self._session.get(url, params=params) as response:
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get("s") == "no_data":
                        return []
                    
                    bars = self._parse_candles(symbol, data, timeframe)
                    self._record_success(latency_ms)
                    return bars
                    
                elif response.status == 429:
                    raise RateLimitError("finnhub", retry_after=60)
                else:
                    error_text = await response.text()
                    raise ProviderError("finnhub", f"API error {response.status}: {error_text}")
                    
        except aiohttp.ClientError as e:
            self._record_error(e)
            raise ProviderError("finnhub", f"Connection error: {e}")
    
    # ==================== WebSocket Methods ====================
    
    async def connect_websocket(self) -> None:
        """Connect to Finnhub WebSocket stream."""
        if self._ws and not self._ws.closed:
            return
        
        try:
            ws_url = f"{FINNHUB_WS_URL}?token={self.config.api_key}"
            self._ws = await websockets.connect(ws_url)
            logger.info("Connected to Finnhub WebSocket")
            
        except Exception as e:
            logger.error(f"Failed to connect to Finnhub WebSocket: {e}")
            raise ProviderError("finnhub", f"WebSocket connection failed: {e}")
    
    async def disconnect_websocket(self) -> None:
        """Disconnect from WebSocket."""
        if self._ws:
            await self._ws.close()
            self._ws = None
        
        self._ws_subscriptions.clear()
        logger.info("Disconnected from Finnhub WebSocket")
    
    async def subscribe(self, symbols: list[str]) -> None:
        """Subscribe to trade updates for symbols."""
        if not self._ws:
            await self.connect_websocket()
        
        for symbol in symbols:
            symbol = symbol.upper()
            if symbol not in self._ws_subscriptions:
                msg = {"type": "subscribe", "symbol": symbol}
                await self._ws.send(json.dumps(msg))
                self._ws_subscriptions.add(symbol)
        
        logger.info(f"Subscribed to Finnhub trades: {symbols}")
    
    async def unsubscribe(self, symbols: list[str]) -> None:
        """Unsubscribe from trade updates."""
        if not self._ws:
            return
        
        for symbol in symbols:
            symbol = symbol.upper()
            if symbol in self._ws_subscriptions:
                msg = {"type": "unsubscribe", "symbol": symbol}
                await self._ws.send(json.dumps(msg))
                self._ws_subscriptions.discard(symbol)
        
        logger.info(f"Unsubscribed from Finnhub trades: {symbols}")
    
    async def stream_quotes(self) -> AsyncIterator[Quote]:
        """Stream real-time trades from WebSocket (converted to quotes)."""
        if not self._ws:
            await self.connect_websocket()
        
        try:
            async for message in self._ws:
                try:
                    data = json.loads(message)
                    
                    if data.get("type") == "trade":
                        # Finnhub sends trades, we convert to quotes
                        for trade in data.get("data", []):
                            quote = self._parse_ws_trade(trade)
                            yield quote
                    elif data.get("type") == "ping":
                        # Respond to ping
                        await self._ws.send(json.dumps({"type": "pong"}))
                    elif data.get("type") == "error":
                        logger.error(f"Finnhub WS error: {data}")
                        
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from Finnhub WS: {message}")
                except Exception as e:
                    logger.error(f"Error processing Finnhub WS message: {e}")
                    
        except websockets.ConnectionClosed:
            logger.warning("Finnhub WebSocket connection closed")
    
    # ==================== Parsing Methods ====================
    
    def _parse_quote(self, symbol: str, data: dict[str, Any]) -> Quote:
        """Parse REST API quote response."""
        price = Decimal(str(data.get("c", 0)))
        prev_close = Decimal(str(data.get("pc", 0)))
        change = Decimal(str(data.get("d", 0))) if data.get("d") else None
        change_pct = Decimal(str(data.get("dp", 0))) if data.get("dp") else None
        
        # Timestamp is Unix timestamp
        timestamp_ts = data.get("t", 0)
        if timestamp_ts:
            timestamp = datetime.fromtimestamp(timestamp_ts, tz=timezone.utc)
        else:
            timestamp = datetime.now(timezone.utc)
        
        return Quote(
            symbol=symbol,
            price=price,
            timestamp=timestamp,
            provider="finnhub",
            market_type=MarketType.US_STOCK,
            change=change,
            change_percent=change_pct,
            day_high=Decimal(str(data.get("h", 0))) if data.get("h") else None,
            day_low=Decimal(str(data.get("l", 0))) if data.get("l") else None,
            day_open=Decimal(str(data.get("o", 0))) if data.get("o") else None,
            prev_close=prev_close if prev_close else None,
        )
    
    def _parse_ws_trade(self, data: dict[str, Any]) -> Quote:
        """Parse WebSocket trade message as a quote."""
        symbol = data.get("s", "")
        price = Decimal(str(data.get("p", 0)))
        volume = int(data.get("v", 0))
        
        timestamp_ms = data.get("t", 0)
        if timestamp_ms:
            timestamp = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
        else:
            timestamp = datetime.now(timezone.utc)
        
        return Quote(
            symbol=symbol,
            price=price,
            volume=volume,
            timestamp=timestamp,
            provider="finnhub",
            market_type=MarketType.US_STOCK,
        )
    
    def _parse_candles(
        self, 
        symbol: str, 
        data: dict[str, Any], 
        timeframe: TimeFrame
    ) -> list[OHLCV]:
        """Parse candle response into OHLCV list."""
        bars = []
        
        opens = data.get("o", [])
        highs = data.get("h", [])
        lows = data.get("l", [])
        closes = data.get("c", [])
        volumes = data.get("v", [])
        timestamps = data.get("t", [])
        
        for i in range(len(timestamps)):
            try:
                timestamp = datetime.fromtimestamp(timestamps[i], tz=timezone.utc)
                
                bar = OHLCV(
                    symbol=symbol,
                    timestamp=timestamp,
                    open=Decimal(str(opens[i])),
                    high=Decimal(str(highs[i])),
                    low=Decimal(str(lows[i])),
                    close=Decimal(str(closes[i])),
                    volume=int(volumes[i]) if i < len(volumes) else 0,
                    provider="finnhub",
                    timeframe=timeframe,
                )
                bars.append(bar)
            except (IndexError, ValueError) as e:
                logger.warning(f"Failed to parse candle at index {i}: {e}")
        
        # Sort by timestamp
        bars.sort(key=lambda x: x.timestamp)
        return bars
