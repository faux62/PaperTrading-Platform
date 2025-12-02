"""
US Markets Router

Intelligent routing layer for US stock market data providers.
Manages failover, load balancing, and provider selection based on
data type, cost, availability, and performance.
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Any, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
import asyncio
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


class SelectionStrategy(Enum):
    """Provider selection strategies."""
    PRIORITY = "priority"           # Use highest priority available
    ROUND_ROBIN = "round_robin"     # Rotate between providers
    LOWEST_LATENCY = "lowest_latency"  # Use fastest provider
    LOWEST_COST = "lowest_cost"     # Use cheapest provider
    RANDOM = "random"               # Random selection


@dataclass
class ProviderStatus:
    """Status of a provider in the router."""
    name: str
    adapter: BaseAdapter
    is_healthy: bool = True
    is_rate_limited: bool = False
    rate_limit_reset: Optional[datetime] = None
    last_error: Optional[str] = None
    last_success: Optional[datetime] = None
    error_count: int = 0
    success_count: int = 0
    total_latency_ms: float = 0.0
    
    @property
    def average_latency_ms(self) -> float:
        """Calculate average response latency."""
        if self.success_count == 0:
            return float('inf')
        return self.total_latency_ms / self.success_count
    
    @property
    def is_available(self) -> bool:
        """Check if provider is available for requests."""
        if not self.is_healthy:
            return False
        if self.is_rate_limited:
            if self.rate_limit_reset and datetime.now() > self.rate_limit_reset:
                self.is_rate_limited = False
                self.rate_limit_reset = None
            else:
                return False
        return True


@dataclass
class RouterConfig:
    """Configuration for US Markets Router."""
    selection_strategy: SelectionStrategy = SelectionStrategy.PRIORITY
    max_retries: int = 3
    retry_delay: float = 1.0
    health_check_interval: int = 60  # seconds
    circuit_breaker_threshold: int = 5  # errors before marking unhealthy
    circuit_breaker_reset: int = 60  # seconds


class USMarketsRouter:
    """
    Router for US stock market data providers.
    
    Manages multiple providers with intelligent selection,
    automatic failover, and health monitoring.
    
    Features:
    - Provider registration and management
    - Automatic failover on errors
    - Rate limit tracking and avoidance
    - Health monitoring with circuit breaker
    - Configurable selection strategies
    
    Usage:
        router = USMarketsRouter()
        router.register_provider("alpaca", alpaca_adapter)
        router.register_provider("polygon", polygon_adapter)
        await router.initialize()
        
        quote = await router.get_quote("AAPL")
        bars = await router.get_historical("MSFT", start_date, end_date)
    """
    
    def __init__(self, config: Optional[RouterConfig] = None):
        self.config = config or RouterConfig()
        self._providers: dict[str, ProviderStatus] = {}
        self._round_robin_index: int = 0
        self._health_check_task: Optional[asyncio.Task] = None
        self._quote_callbacks: list[Callable[[Quote], Awaitable[None]]] = []
    
    # ==================== Provider Management ====================
    
    def register_provider(
        self,
        name: str,
        adapter: BaseAdapter,
        priority: Optional[int] = None,
    ) -> None:
        """Register a data provider."""
        if priority is not None:
            # Override priority from config
            adapter.config.priority = priority
        
        self._providers[name] = ProviderStatus(
            name=name,
            adapter=adapter,
        )
        logger.info(f"Registered US market provider: {name} (priority: {adapter.config.priority})")
    
    def unregister_provider(self, name: str) -> None:
        """Unregister a data provider."""
        if name in self._providers:
            del self._providers[name]
            logger.info(f"Unregistered US market provider: {name}")
    
    async def initialize(self) -> None:
        """Initialize all registered providers."""
        init_tasks = []
        for name, status in self._providers.items():
            init_tasks.append(self._init_provider(name, status))
        
        await asyncio.gather(*init_tasks, return_exceptions=True)
        
        # Start health monitoring
        self._health_check_task = asyncio.create_task(self._health_monitor())
        
        logger.info(f"US Markets Router initialized with {len(self._providers)} providers")
    
    async def _init_provider(self, name: str, status: ProviderStatus) -> None:
        """Initialize a single provider."""
        try:
            await status.adapter.initialize()
            health = await status.adapter.health_check()
            status.is_healthy = health
            if not health:
                logger.warning(f"Provider {name} health check failed")
        except Exception as e:
            status.is_healthy = False
            status.last_error = str(e)
            logger.error(f"Failed to initialize provider {name}: {e}")
    
    async def close(self) -> None:
        """Close all providers and stop monitoring."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        close_tasks = []
        for status in self._providers.values():
            close_tasks.append(status.adapter.close())
        
        await asyncio.gather(*close_tasks, return_exceptions=True)
        logger.info("US Markets Router closed")
    
    # ==================== Provider Selection ====================
    
    def _get_available_providers(self) -> list[ProviderStatus]:
        """Get list of available providers sorted by priority."""
        available = [
            status for status in self._providers.values()
            if status.is_available
        ]
        
        if self.config.selection_strategy == SelectionStrategy.PRIORITY:
            available.sort(key=lambda s: s.adapter.config.priority)
        elif self.config.selection_strategy == SelectionStrategy.LOWEST_LATENCY:
            available.sort(key=lambda s: s.average_latency_ms)
        elif self.config.selection_strategy == SelectionStrategy.LOWEST_COST:
            available.sort(key=lambda s: s.adapter.config.cost_per_request)
        
        return available
    
    def _select_provider(self, exclude: Optional[set[str]] = None) -> Optional[ProviderStatus]:
        """Select the next provider based on strategy."""
        exclude = exclude or set()
        available = [
            s for s in self._get_available_providers()
            if s.name not in exclude
        ]
        
        if not available:
            return None
        
        if self.config.selection_strategy == SelectionStrategy.ROUND_ROBIN:
            self._round_robin_index = (self._round_robin_index + 1) % len(available)
            return available[self._round_robin_index]
        elif self.config.selection_strategy == SelectionStrategy.RANDOM:
            import random
            return random.choice(available)
        else:
            # PRIORITY, LOWEST_LATENCY, LOWEST_COST - already sorted
            return available[0]
    
    # ==================== Data Methods ====================
    
    async def get_quote(self, symbol: str) -> Quote:
        """Get quote with automatic failover."""
        tried_providers: set[str] = set()
        last_error: Optional[Exception] = None
        
        for attempt in range(self.config.max_retries):
            provider = self._select_provider(exclude=tried_providers)
            
            if not provider:
                if last_error:
                    raise last_error
                raise ProviderError("us_router", "No available providers")
            
            tried_providers.add(provider.name)
            
            try:
                start_time = datetime.now()
                quote = await provider.adapter.get_quote(symbol)
                
                # Record success
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                provider.success_count += 1
                provider.total_latency_ms += latency_ms
                provider.last_success = datetime.now()
                provider.error_count = 0
                
                return quote
                
            except RateLimitError as e:
                provider.is_rate_limited = True
                provider.rate_limit_reset = datetime.now()
                if e.retry_after:
                    from datetime import timedelta
                    provider.rate_limit_reset += timedelta(seconds=e.retry_after)
                last_error = e
                logger.warning(f"Provider {provider.name} rate limited")
                
            except DataNotAvailableError as e:
                # Don't retry other providers for missing data
                raise e
                
            except Exception as e:
                provider.error_count += 1
                provider.last_error = str(e)
                last_error = e
                
                # Circuit breaker
                if provider.error_count >= self.config.circuit_breaker_threshold:
                    provider.is_healthy = False
                    logger.warning(f"Provider {provider.name} circuit breaker opened")
                
                logger.warning(f"Provider {provider.name} error: {e}")
                
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay)
        
        raise last_error or ProviderError("us_router", "All providers failed")
    
    async def get_quotes(self, symbols: list[str]) -> list[Quote]:
        """Get quotes for multiple symbols."""
        if not symbols:
            return []
        
        # Try batch-capable providers first
        provider = self._select_provider()
        
        if provider and provider.adapter.config.supports_batch:
            try:
                return await provider.adapter.get_quotes(symbols)
            except Exception as e:
                logger.warning(f"Batch quote failed: {e}, falling back to individual")
        
        # Fallback to individual requests
        tasks = [self.get_quote(s) for s in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        quotes = []
        for result in results:
            if isinstance(result, Quote):
                quotes.append(result)
            elif isinstance(result, Exception):
                logger.warning(f"Quote fetch error: {result}")
        
        return quotes
    
    async def get_historical(
        self,
        symbol: str,
        start_date: date,
        end_date: Optional[date] = None,
        timeframe: TimeFrame = TimeFrame.DAY,
    ) -> list[OHLCV]:
        """Get historical data with automatic failover."""
        tried_providers: set[str] = set()
        last_error: Optional[Exception] = None
        
        for attempt in range(self.config.max_retries):
            provider = self._select_provider(exclude=tried_providers)
            
            if not provider:
                if last_error:
                    raise last_error
                raise ProviderError("us_router", "No available providers")
            
            tried_providers.add(provider.name)
            
            try:
                bars = await provider.adapter.get_historical(
                    symbol, start_date, end_date, timeframe
                )
                
                provider.success_count += 1
                provider.last_success = datetime.now()
                provider.error_count = 0
                
                return bars
                
            except RateLimitError as e:
                provider.is_rate_limited = True
                last_error = e
                
            except DataNotAvailableError as e:
                raise e
                
            except Exception as e:
                provider.error_count += 1
                provider.last_error = str(e)
                last_error = e
                
                if provider.error_count >= self.config.circuit_breaker_threshold:
                    provider.is_healthy = False
        
        raise last_error or ProviderError("us_router", "All providers failed")
    
    async def search_symbols(self, query: str) -> list[dict[str, Any]]:
        """Search for symbols across providers."""
        provider = self._select_provider()
        
        if not provider:
            return []
        
        try:
            return await provider.adapter.search_symbols(query)
        except Exception as e:
            logger.warning(f"Symbol search failed: {e}")
            return []
    
    # ==================== Streaming ====================
    
    def on_quote(self, callback: Callable[[Quote], Awaitable[None]]) -> None:
        """Register callback for real-time quotes."""
        self._quote_callbacks.append(callback)
    
    async def subscribe_quotes(self, symbols: list[str]) -> None:
        """Subscribe to real-time quotes from streaming providers."""
        for status in self._providers.values():
            if status.is_available and status.adapter.config.supports_websocket:
                try:
                    # Forward quotes to registered callbacks
                    async def forward_quote(quote: Quote) -> None:
                        for callback in self._quote_callbacks:
                            try:
                                await callback(quote)
                            except Exception as e:
                                logger.error(f"Quote callback error: {e}")
                    
                    status.adapter.on_quote(forward_quote)
                    await status.adapter.start_streaming(symbols)
                    logger.info(f"Subscribed to quotes via {status.name}")
                    return  # Use first available streaming provider
                    
                except Exception as e:
                    logger.warning(f"Failed to start streaming with {status.name}: {e}")
        
        logger.warning("No streaming providers available")
    
    async def unsubscribe_quotes(self, symbols: list[str]) -> None:
        """Unsubscribe from real-time quotes."""
        for status in self._providers.values():
            if hasattr(status.adapter, 'stop_streaming'):
                try:
                    await status.adapter.stop_streaming()
                except Exception as e:
                    logger.warning(f"Failed to stop streaming: {e}")
    
    # ==================== Health Monitoring ====================
    
    async def _health_monitor(self) -> None:
        """Background task to monitor provider health."""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                
                for name, status in self._providers.items():
                    if not status.is_healthy:
                        # Try to recover unhealthy providers
                        try:
                            health = await status.adapter.health_check()
                            if health:
                                status.is_healthy = True
                                status.error_count = 0
                                logger.info(f"Provider {name} recovered")
                        except Exception:
                            pass
                    
                    # Reset rate limits after reset time
                    if status.is_rate_limited and status.rate_limit_reset:
                        if datetime.now() > status.rate_limit_reset:
                            status.is_rate_limited = False
                            status.rate_limit_reset = None
                            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
    
    def get_provider_status(self) -> dict[str, dict[str, Any]]:
        """Get status of all providers."""
        status_dict = {}
        
        for name, status in self._providers.items():
            status_dict[name] = {
                "name": name,
                "is_healthy": status.is_healthy,
                "is_rate_limited": status.is_rate_limited,
                "is_available": status.is_available,
                "error_count": status.error_count,
                "success_count": status.success_count,
                "average_latency_ms": round(status.average_latency_ms, 2),
                "last_error": status.last_error,
                "last_success": status.last_success.isoformat() if status.last_success else None,
                "priority": status.adapter.config.priority,
            }
        
        return status_dict


# ==================== Factory Function ====================

def create_us_markets_router(
    alpaca_config: Optional[ProviderConfig] = None,
    polygon_config: Optional[ProviderConfig] = None,
    finnhub_config: Optional[ProviderConfig] = None,
    tiingo_config: Optional[ProviderConfig] = None,
    intrinio_config: Optional[ProviderConfig] = None,
    router_config: Optional[RouterConfig] = None,
) -> USMarketsRouter:
    """
    Factory function to create a US Markets Router with configured providers.
    
    Args:
        alpaca_config: Configuration for Alpaca adapter
        polygon_config: Configuration for Polygon adapter
        finnhub_config: Configuration for Finnhub adapter
        tiingo_config: Configuration for Tiingo adapter
        intrinio_config: Configuration for Intrinio adapter
        router_config: Router configuration
        
    Returns:
        Configured USMarketsRouter instance
    """
    from app.data_providers.adapters.alpaca import AlpacaAdapter
    from app.data_providers.adapters.polygon import PolygonAdapter
    from app.data_providers.adapters.finnhub import FinnhubAdapter
    from app.data_providers.adapters.tiingo import TiingoAdapter
    from app.data_providers.adapters.intrinio import IntrinioAdapter
    
    router = USMarketsRouter(config=router_config)
    
    if alpaca_config:
        router.register_provider("alpaca", AlpacaAdapter(alpaca_config))
    
    if polygon_config:
        router.register_provider("polygon", PolygonAdapter(polygon_config))
    
    if finnhub_config:
        router.register_provider("finnhub", FinnhubAdapter(finnhub_config))
    
    if tiingo_config:
        router.register_provider("tiingo", TiingoAdapter(tiingo_config))
    
    if intrinio_config:
        router.register_provider("intrinio", IntrinioAdapter(intrinio_config))
    
    return router
