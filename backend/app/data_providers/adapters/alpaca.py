"""
Alpaca Markets Adapter

Provides access to Alpaca's market data API for US stocks.
Supports both REST API and WebSocket streaming.

API Documentation: https://docs.alpaca.markets/docs/market-data-api
Free tier: Unlimited API calls, 15-min delayed data (IEX)
Paid tier: Real-time data from all US exchanges
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
    ProviderType,
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


# Alpaca API endpoints
ALPACA_DATA_URL = "https://data.alpaca.markets"
ALPACA_PAPER_URL = "https://paper-api.alpaca.markets"
ALPACA_LIVE_URL = "https://api.alpaca.markets"
ALPACA_STREAM_URL = "wss://stream.data.alpaca.markets/v2"


def create_alpaca_config(
    api_key: str,
    api_secret: str,
    paper: bool = True,
    data_feed: str = "iex",  # "iex" (free) or "sip" (paid)
) -> ProviderConfig:
    """Create configuration for Alpaca adapter."""
    return ProviderConfig(
        name="alpaca",
        api_key=api_key,
        api_secret=api_secret,
        base_url=ALPACA_DATA_URL,
        websocket_url=f"{ALPACA_STREAM_URL}/{data_feed}",
        requests_per_minute=200,  # Alpaca limit
        requests_per_day=0,  # Unlimited
        max_symbols_per_request=100,
        cost_per_request=Decimal("0"),  # Free
        daily_budget=Decimal("0"),
        timeout_seconds=30.0,
        retry_attempts=3,
        retry_delay=1.0,
        supports_websocket=True,
        supports_batch=True,
        supports_historical=True,
        supported_markets=[MarketType.US_STOCK],
        supported_data_types=[DataType.QUOTE, DataType.OHLCV, DataType.TRADE],
        priority=10,  # High priority (low number = preferred)
    )


class AlpacaAdapter(BaseAdapter):
    """
    Alpaca Markets data provider adapter.
    
    Features:
    - Real-time quotes via REST and WebSocket
    - Historical OHLCV data (bars)
    - Batch quote requests
    - Paper trading support
    
    Usage:
        config = create_alpaca_config("your_api_key", "your_api_secret")
        adapter = AlpacaAdapter(config)
        await adapter.initialize()
        
        quote = await adapter.get_quote("AAPL")
        bars = await adapter.get_historical("AAPL", start_date, end_date)
    """
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[ClientConnection] = None
        self._ws_authenticated = False
        self._ws_subscriptions: set[str] = set()
        self._ws_task: Optional[asyncio.Task] = None
        self._quote_queue: asyncio.Queue[Quote] = asyncio.Queue()
        self._data_feed = "iex"  # Default to free feed
        
        # Extract data feed from websocket URL
        if config.websocket_url:
            if "/sip" in config.websocket_url:
                self._data_feed = "sip"
    
    @property
    def _headers(self) -> dict[str, str]:
        """Get authentication headers."""
        return {
            "APCA-API-KEY-ID": self.config.api_key or "",
            "APCA-API-SECRET-KEY": self.config.api_secret or "",
        }
    
    async def initialize(self) -> None:
        """Initialize HTTP session."""
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            self._session = aiohttp.ClientSession(
                headers=self._headers,
                timeout=timeout,
            )
            logger.info(f"Alpaca adapter initialized (feed: {self._data_feed})")
    
    async def close(self) -> None:
        """Close all connections."""
        if self._ws_task:
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass
        
        if self._ws:
            await self._ws.close()
            self._ws = None
        
        if self._session:
            await self._session.close()
            self._session = None
        
        logger.info("Alpaca adapter closed")
    
    async def health_check(self) -> bool:
        """Check API connectivity."""
        try:
            # Simple request to check authentication
            url = f"{self.config.base_url}/v2/stocks/AAPL/quotes/latest"
            async with self._session.get(url) as response:
                if response.status == 200:
                    return True
                elif response.status == 401:
                    logger.error("Alpaca authentication failed")
                    return False
                else:
                    logger.warning(f"Alpaca health check status: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Alpaca health check failed: {e}")
            return False
    
    # ==================== REST API Methods ====================
    
    async def get_quote(self, symbol: str) -> Quote:
        """Get latest quote for a symbol."""
        symbol = symbol.upper()
        url = f"{self.config.base_url}/v2/stocks/{symbol}/quotes/latest"
        
        try:
            start_time = datetime.now()
            async with self._session.get(url) as response:
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    data = await response.json()
                    quote = self._parse_quote(symbol, data.get("quote", {}))
                    self._record_success(latency_ms)
                    return quote
                elif response.status == 401:
                    raise AuthenticationError("alpaca")
                elif response.status == 429:
                    raise RateLimitError("alpaca", retry_after=60)
                elif response.status == 404:
                    raise DataNotAvailableError("alpaca", symbol, "quote")
                else:
                    error_text = await response.text()
                    raise ProviderError("alpaca", f"API error {response.status}: {error_text}")
                    
        except aiohttp.ClientError as e:
            self._record_error(e)
            raise ProviderError("alpaca", f"Connection error: {e}")
    
    async def get_quotes(self, symbols: list[str]) -> list[Quote]:
        """Get latest quotes for multiple symbols."""
        if not symbols:
            return []
        
        symbols = [s.upper() for s in symbols]
        url = f"{self.config.base_url}/v2/stocks/quotes/latest"
        params = {"symbols": ",".join(symbols)}
        
        try:
            start_time = datetime.now()
            async with self._session.get(url, params=params) as response:
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    data = await response.json()
                    quotes = []
                    for sym, quote_data in data.get("quotes", {}).items():
                        try:
                            quote = self._parse_quote(sym, quote_data)
                            quotes.append(quote)
                        except Exception as e:
                            logger.warning(f"Failed to parse quote for {sym}: {e}")
                    
                    self._record_success(latency_ms)
                    return quotes
                elif response.status == 429:
                    raise RateLimitError("alpaca", retry_after=60)
                else:
                    error_text = await response.text()
                    raise ProviderError("alpaca", f"API error {response.status}: {error_text}")
                    
        except aiohttp.ClientError as e:
            self._record_error(e)
            raise ProviderError("alpaca", f"Connection error: {e}")
    
    async def get_historical(
        self,
        symbol: str,
        start_date: date,
        end_date: Optional[date] = None,
        timeframe: TimeFrame = TimeFrame.DAY,
    ) -> list[OHLCV]:
        """Get historical bar data."""
        symbol = symbol.upper()
        
        if end_date is None:
            end_date = date.today()
        
        # Convert timeframe to Alpaca format
        tf_map = {
            TimeFrame.MINUTE_1: "1Min",
            TimeFrame.MINUTE_5: "5Min",
            TimeFrame.MINUTE_15: "15Min",
            TimeFrame.MINUTE_30: "30Min",
            TimeFrame.HOUR_1: "1Hour",
            TimeFrame.HOUR_4: "4Hour",
            TimeFrame.DAY: "1Day",
            TimeFrame.WEEK: "1Week",
            TimeFrame.MONTH: "1Month",
        }
        alpaca_tf = tf_map.get(timeframe, "1Day")
        
        url = f"{self.config.base_url}/v2/stocks/{symbol}/bars"
        params = {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "timeframe": alpaca_tf,
            "limit": 10000,
            "adjustment": "split",  # Adjust for stock splits
        }
        
        all_bars: list[OHLCV] = []
        next_page_token = None
        
        try:
            while True:
                if next_page_token:
                    params["page_token"] = next_page_token
                
                start_time = datetime.now()
                async with self._session.get(url, params=params) as response:
                    latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                    
                    if response.status == 200:
                        data = await response.json()
                        bars = data.get("bars", [])
                        
                        for bar in bars:
                            try:
                                ohlcv = self._parse_bar(symbol, bar, timeframe)
                                all_bars.append(ohlcv)
                            except Exception as e:
                                logger.warning(f"Failed to parse bar for {symbol}: {e}")
                        
                        self._record_success(latency_ms)
                        
                        # Check for pagination
                        next_page_token = data.get("next_page_token")
                        if not next_page_token:
                            break
                    elif response.status == 429:
                        raise RateLimitError("alpaca", retry_after=60)
                    else:
                        error_text = await response.text()
                        raise ProviderError("alpaca", f"API error {response.status}: {error_text}")
            
            # Sort by timestamp
            all_bars.sort(key=lambda x: x.timestamp)
            return all_bars
            
        except aiohttp.ClientError as e:
            self._record_error(e)
            raise ProviderError("alpaca", f"Connection error: {e}")
    
    # ==================== WebSocket Methods ====================
    
    async def connect_websocket(self) -> None:
        """Connect to Alpaca WebSocket stream."""
        if self._ws and not self._ws.closed:
            return
        
        try:
            self._ws = await websockets.connect(self.config.websocket_url)
            logger.info(f"Connected to Alpaca WebSocket: {self.config.websocket_url}")
            
            # Authenticate
            auth_msg = {
                "action": "auth",
                "key": self.config.api_key,
                "secret": self.config.api_secret,
            }
            await self._ws.send(json.dumps(auth_msg))
            
            # Wait for auth response
            response = await self._ws.recv()
            data = json.loads(response)
            
            if isinstance(data, list) and len(data) > 0:
                msg = data[0]
                if msg.get("T") == "success" and msg.get("msg") == "authenticated":
                    self._ws_authenticated = True
                    logger.info("Alpaca WebSocket authenticated")
                else:
                    raise AuthenticationError("alpaca", f"WebSocket auth failed: {msg}")
            else:
                raise AuthenticationError("alpaca", f"Unexpected auth response: {data}")
                
        except Exception as e:
            logger.error(f"Failed to connect to Alpaca WebSocket: {e}")
            raise ProviderError("alpaca", f"WebSocket connection failed: {e}")
    
    async def disconnect_websocket(self) -> None:
        """Disconnect from WebSocket."""
        if self._ws_task:
            self._ws_task.cancel()
        
        if self._ws:
            await self._ws.close()
            self._ws = None
        
        self._ws_authenticated = False
        self._ws_subscriptions.clear()
        logger.info("Disconnected from Alpaca WebSocket")
    
    async def subscribe(self, symbols: list[str]) -> None:
        """Subscribe to quote updates for symbols."""
        if not self._ws or not self._ws_authenticated:
            await self.connect_websocket()
        
        symbols = [s.upper() for s in symbols]
        new_symbols = [s for s in symbols if s not in self._ws_subscriptions]
        
        if not new_symbols:
            return
        
        sub_msg = {
            "action": "subscribe",
            "quotes": new_symbols,
        }
        await self._ws.send(json.dumps(sub_msg))
        
        self._ws_subscriptions.update(new_symbols)
        logger.info(f"Subscribed to Alpaca quotes: {new_symbols}")
    
    async def unsubscribe(self, symbols: list[str]) -> None:
        """Unsubscribe from quote updates."""
        if not self._ws:
            return
        
        symbols = [s.upper() for s in symbols]
        current_symbols = [s for s in symbols if s in self._ws_subscriptions]
        
        if not current_symbols:
            return
        
        unsub_msg = {
            "action": "unsubscribe",
            "quotes": current_symbols,
        }
        await self._ws.send(json.dumps(unsub_msg))
        
        self._ws_subscriptions.difference_update(current_symbols)
        logger.info(f"Unsubscribed from Alpaca quotes: {current_symbols}")
    
    async def stream_quotes(self) -> AsyncIterator[Quote]:
        """Stream real-time quotes from WebSocket."""
        if not self._ws or not self._ws_authenticated:
            await self.connect_websocket()
        
        try:
            async for message in self._ws:
                try:
                    data = json.loads(message)
                    
                    # Alpaca sends messages as arrays
                    if isinstance(data, list):
                        for item in data:
                            msg_type = item.get("T")
                            
                            if msg_type == "q":  # Quote
                                quote = self._parse_ws_quote(item)
                                yield quote
                            elif msg_type == "error":
                                logger.error(f"Alpaca WS error: {item}")
                            elif msg_type in ["success", "subscription"]:
                                # Info messages, ignore
                                pass
                                
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from Alpaca WS: {message}")
                except Exception as e:
                    logger.error(f"Error processing Alpaca WS message: {e}")
                    
        except websockets.ConnectionClosed:
            logger.warning("Alpaca WebSocket connection closed")
            self._ws_authenticated = False
    
    # ==================== Parsing Methods ====================
    
    def _parse_quote(self, symbol: str, data: dict[str, Any]) -> Quote:
        """Parse REST API quote response."""
        # Handle timestamp
        timestamp_str = data.get("t")
        if timestamp_str:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        else:
            timestamp = datetime.now(timezone.utc)
        
        bid = Decimal(str(data.get("bp", 0)))
        ask = Decimal(str(data.get("ap", 0)))
        
        # Calculate mid price if both bid/ask available
        if bid > 0 and ask > 0:
            price = (bid + ask) / 2
        else:
            price = bid or ask or Decimal("0")
        
        return Quote(
            symbol=symbol,
            price=price,
            bid=bid if bid > 0 else None,
            ask=ask if ask > 0 else None,
            bid_size=data.get("bs"),
            ask_size=data.get("as"),
            timestamp=timestamp,
            provider="alpaca",
            market_type=MarketType.US_STOCK,
            exchange=data.get("bx") or data.get("ax"),  # Bid or ask exchange
        )
    
    def _parse_ws_quote(self, data: dict[str, Any]) -> Quote:
        """Parse WebSocket quote message."""
        symbol = data.get("S", "")
        
        timestamp_str = data.get("t")
        if timestamp_str:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        else:
            timestamp = datetime.now(timezone.utc)
        
        bid = Decimal(str(data.get("bp", 0)))
        ask = Decimal(str(data.get("ap", 0)))
        
        if bid > 0 and ask > 0:
            price = (bid + ask) / 2
        else:
            price = bid or ask or Decimal("0")
        
        return Quote(
            symbol=symbol,
            price=price,
            bid=bid if bid > 0 else None,
            ask=ask if ask > 0 else None,
            bid_size=data.get("bs"),
            ask_size=data.get("as"),
            timestamp=timestamp,
            provider="alpaca",
            market_type=MarketType.US_STOCK,
            exchange=data.get("bx"),
        )
    
    def _parse_bar(self, symbol: str, data: dict[str, Any], timeframe: TimeFrame) -> OHLCV:
        """Parse historical bar data."""
        timestamp_str = data.get("t")
        if timestamp_str:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        else:
            timestamp = datetime.now(timezone.utc)
        
        return OHLCV(
            symbol=symbol,
            timestamp=timestamp,
            open=Decimal(str(data.get("o", 0))),
            high=Decimal(str(data.get("h", 0))),
            low=Decimal(str(data.get("l", 0))),
            close=Decimal(str(data.get("c", 0))),
            volume=int(data.get("v", 0)),
            provider="alpaca",
            timeframe=timeframe,
            vwap=Decimal(str(data.get("vw", 0))) if data.get("vw") else None,
            trade_count=data.get("n"),
        )
