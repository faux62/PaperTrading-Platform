"""
Asia Markets Router

Intelligent routing layer for Asian stock market data providers.
Manages failover, load balancing, and provider selection for
Asia markets (TSE, HKEX, SSE, NSE, etc.).
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Any
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
from app.data_providers.routing.us_markets import (
    SelectionStrategy,
    ProviderStatus,
    RouterConfig,
)


# Asia Exchange mapping
ASIA_EXCHANGES = {
    "TSE": "japan",       # Tokyo Stock Exchange
    "TYO": "japan",
    "HKEX": "hong kong",  # Hong Kong
    "HKG": "hong kong",
    "SSE": "china",       # Shanghai
    "SZSE": "china",      # Shenzhen
    "SHE": "china",
    "NSE": "india",       # National Stock Exchange
    "BSE": "india",       # Bombay Stock Exchange
    "KRX": "south korea", # Korea Exchange
    "KSC": "south korea",
    "TWSE": "taiwan",     # Taiwan Stock Exchange
    "TPE": "taiwan",
    "SGX": "singapore",   # Singapore Exchange
    "ASX": "australia",   # Australian Securities Exchange
}

# Symbol suffix for yfinance
YFINANCE_ASIA_SUFFIXES = {
    "japan": ".T",
    "hong kong": ".HK",
    "china": ".SS",  # Shanghai, or .SZ for Shenzhen
    "india": ".NS",  # NSE, or .BO for BSE
    "south korea": ".KS",
    "taiwan": ".TW",
    "singapore": ".SI",
    "australia": ".AX",
}


class AsiaMarketsRouter:
    """
    Router for Asian stock market data providers.
    
    Manages multiple providers with intelligent selection,
    automatic failover, and country-aware routing.
    
    Features:
    - Country-specific routing (Japan, HK, China, India, Korea)
    - Provider registration and management
    - Automatic failover on errors
    - Rate limit tracking
    - Health monitoring
    
    Usage:
        router = AsiaMarketsRouter()
        router.register_provider("twelve_data", twelve_data_adapter)
        router.register_provider("yfinance", yfinance_adapter)
        await router.initialize()
        
        quote = await router.get_quote("7203", country="japan")  # Toyota
        bars = await router.get_historical("0700", country="hong kong")  # Tencent
    """
    
    def __init__(self, config: Optional[RouterConfig] = None):
        self.config = config or RouterConfig()
        self._providers: dict[str, ProviderStatus] = {}
        self._round_robin_index: int = 0
        self._health_check_task: Optional[asyncio.Task] = None
    
    # ==================== Provider Management ====================
    
    def register_provider(
        self,
        name: str,
        adapter: BaseAdapter,
        priority: Optional[int] = None,
    ) -> None:
        """Register a data provider."""
        if priority is not None:
            adapter.config.priority = priority
        
        self._providers[name] = ProviderStatus(
            name=name,
            adapter=adapter,
        )
        logger.info(f"Registered Asia market provider: {name} (priority: {adapter.config.priority})")
    
    def unregister_provider(self, name: str) -> None:
        """Unregister a data provider."""
        if name in self._providers:
            del self._providers[name]
            logger.info(f"Unregistered Asia market provider: {name}")
    
    async def initialize(self) -> None:
        """Initialize all registered providers."""
        init_tasks = []
        for name, status in self._providers.items():
            init_tasks.append(self._init_provider(name, status))
        
        await asyncio.gather(*init_tasks, return_exceptions=True)
        
        # Start health monitoring
        self._health_check_task = asyncio.create_task(self._health_monitor())
        
        logger.info(f"Asia Markets Router initialized with {len(self._providers)} providers")
    
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
        logger.info("Asia Markets Router closed")
    
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
            return available[0]
    
    # ==================== Symbol Formatting ====================
    
    def _format_symbol_for_provider(
        self,
        symbol: str,
        provider_name: str,
        country: str,
    ) -> str:
        """Format symbol appropriately for each provider."""
        symbol = symbol.upper()
        country = country.lower()
        
        if provider_name == "yfinance":
            suffix = YFINANCE_ASIA_SUFFIXES.get(country, ".T")
            if not any(symbol.endswith(s) for s in YFINANCE_ASIA_SUFFIXES.values()):
                return f"{symbol}{suffix}"
        elif provider_name == "eodhd":
            # EODHD uses format SYMBOL.EXCHANGE
            exchange_map = {
                "japan": "TSE",
                "hong kong": "HK",
                "china": "SS",
                "india": "NSE",
                "south korea": "KO",
            }
            exchange = exchange_map.get(country, "TSE")
            if "." not in symbol:
                return f"{symbol}.{exchange}"
        
        return symbol
    
    def _get_country_from_exchange(self, exchange: str) -> str:
        """Get country from exchange code."""
        return ASIA_EXCHANGES.get(exchange.upper(), "japan")
    
    # ==================== Data Methods ====================
    
    async def get_quote(
        self,
        symbol: str,
        country: str = "japan",
    ) -> Quote:
        """Get quote with automatic failover."""
        tried_providers: set[str] = set()
        last_error: Optional[Exception] = None
        
        for attempt in range(self.config.max_retries):
            provider = self._select_provider(exclude=tried_providers)
            
            if not provider:
                if last_error:
                    raise last_error
                raise ProviderError("asia_router", "No available providers")
            
            tried_providers.add(provider.name)
            
            try:
                formatted_symbol = self._format_symbol_for_provider(
                    symbol, provider.name, country
                )
                
                start_time = datetime.now()
                quote = await provider.adapter.get_quote(formatted_symbol)
                
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                provider.success_count += 1
                provider.total_latency_ms += latency_ms
                provider.last_success = datetime.now()
                provider.error_count = 0
                
                # Normalize symbol in quote
                quote.symbol = symbol.upper()
                quote.market_type = MarketType.ASIA_STOCK
                
                return quote
                
            except RateLimitError as e:
                provider.is_rate_limited = True
                if e.retry_after:
                    from datetime import timedelta
                    provider.rate_limit_reset = datetime.now() + timedelta(seconds=e.retry_after)
                last_error = e
                logger.warning(f"Provider {provider.name} rate limited")
                
            except DataNotAvailableError as e:
                last_error = e
                logger.debug(f"Data not available from {provider.name}: {e}")
                
            except Exception as e:
                provider.error_count += 1
                provider.last_error = str(e)
                last_error = e
                
                if provider.error_count >= self.config.circuit_breaker_threshold:
                    provider.is_healthy = False
                    logger.warning(f"Provider {provider.name} circuit breaker opened")
                
                logger.warning(f"Provider {provider.name} error: {e}")
                
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay)
        
        raise last_error or ProviderError("asia_router", "All providers failed")
    
    async def get_quotes(
        self,
        symbols: list[str],
        country: str = "japan",
    ) -> list[Quote]:
        """Get quotes for multiple symbols."""
        if not symbols:
            return []
        
        # Try batch-capable provider first
        provider = self._select_provider()
        
        if provider and provider.adapter.config.supports_batch:
            try:
                formatted = [
                    self._format_symbol_for_provider(s, provider.name, country)
                    for s in symbols
                ]
                quotes = await provider.adapter.get_quotes(formatted)
                
                for i, quote in enumerate(quotes):
                    quote.symbol = symbols[i].upper() if i < len(symbols) else quote.symbol
                    quote.market_type = MarketType.ASIA_STOCK
                
                return quotes
            except Exception as e:
                logger.warning(f"Batch quote failed: {e}")
        
        # Fallback to individual requests
        tasks = [self.get_quote(s, country) for s in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        quotes = []
        for result in results:
            if isinstance(result, Quote):
                quotes.append(result)
        
        return quotes
    
    async def get_historical(
        self,
        symbol: str,
        start_date: date,
        end_date: Optional[date] = None,
        timeframe: TimeFrame = TimeFrame.DAY,
        country: str = "japan",
    ) -> list[OHLCV]:
        """Get historical data with automatic failover."""
        tried_providers: set[str] = set()
        last_error: Optional[Exception] = None
        
        for attempt in range(self.config.max_retries):
            provider = self._select_provider(exclude=tried_providers)
            
            if not provider:
                if last_error:
                    raise last_error
                raise ProviderError("asia_router", "No available providers")
            
            tried_providers.add(provider.name)
            
            try:
                formatted_symbol = self._format_symbol_for_provider(
                    symbol, provider.name, country
                )
                
                bars = await provider.adapter.get_historical(
                    formatted_symbol, start_date, end_date, timeframe
                )
                
                for bar in bars:
                    bar.symbol = symbol.upper()
                
                provider.success_count += 1
                provider.last_success = datetime.now()
                provider.error_count = 0
                
                return bars
                
            except RateLimitError as e:
                provider.is_rate_limited = True
                last_error = e
                
            except DataNotAvailableError as e:
                last_error = e
                
            except Exception as e:
                provider.error_count += 1
                provider.last_error = str(e)
                last_error = e
                
                if provider.error_count >= self.config.circuit_breaker_threshold:
                    provider.is_healthy = False
        
        raise last_error or ProviderError("asia_router", "All providers failed")
    
    # ==================== Asia-Specific Methods ====================
    
    async def get_index_quote(
        self,
        index_name: str,
        country: str = "japan",
    ) -> Quote:
        """Get quote for an Asian index."""
        # Map common index names to symbols
        index_map = {
            "NIKKEI 225": ("^N225", "japan"),
            "NIKKEI": ("^N225", "japan"),
            "HANG SENG": ("^HSI", "hong kong"),
            "HSI": ("^HSI", "hong kong"),
            "SSE COMPOSITE": ("000001.SS", "china"),
            "SHANGHAI": ("000001.SS", "china"),
            "SENSEX": ("^BSESN", "india"),
            "NIFTY 50": ("^NSEI", "india"),
            "KOSPI": ("^KS11", "south korea"),
            "ASX 200": ("^AXJO", "australia"),
            "TAIEX": ("^TWII", "taiwan"),
            "STI": ("^STI", "singapore"),
        }
        
        if index_name.upper() in index_map:
            symbol, country = index_map[index_name.upper()]
        else:
            symbol = index_name
        
        return await self.get_quote(symbol, country)
    
    async def get_stocks_by_country(self, country: str) -> list[dict[str, Any]]:
        """Get list of stocks available for a country."""
        for status in self._providers.values():
            if status.is_available and hasattr(status.adapter, 'get_stocks_list'):
                try:
                    return await status.adapter.get_stocks_list(country)
                except Exception as e:
                    logger.warning(f"Failed to get stocks list: {e}")
        
        return []
    
    # ==================== Health Monitoring ====================
    
    async def _health_monitor(self) -> None:
        """Background task to monitor provider health."""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                
                for name, status in self._providers.items():
                    if not status.is_healthy:
                        try:
                            health = await status.adapter.health_check()
                            if health:
                                status.is_healthy = True
                                status.error_count = 0
                                logger.info(f"Provider {name} recovered")
                        except Exception:
                            pass
                    
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

def create_asia_markets_router(
    twelve_data_config: Optional[ProviderConfig] = None,
    yfinance_config: Optional[ProviderConfig] = None,
    eodhd_config: Optional[ProviderConfig] = None,
    router_config: Optional[RouterConfig] = None,
) -> AsiaMarketsRouter:
    """
    Factory function to create an Asia Markets Router with configured providers.
    
    Args:
        twelve_data_config: Configuration for Twelve Data adapter
        yfinance_config: Configuration for yfinance adapter
        eodhd_config: Configuration for EODHD adapter
        router_config: Router configuration
        
    Returns:
        Configured AsiaMarketsRouter instance
    """
    from app.data_providers.adapters.twelve_data import TwelveDataAdapter
    from app.data_providers.adapters.yfinance_adapter import YFinanceAdapter
    from app.data_providers.adapters.eodhd import EODHDAdapter
    
    router = AsiaMarketsRouter(config=router_config)
    
    if twelve_data_config:
        router.register_provider("twelve_data", TwelveDataAdapter(twelve_data_config))
    
    if yfinance_config:
        router.register_provider("yfinance", YFinanceAdapter(yfinance_config))
    
    if eodhd_config:
        router.register_provider("eodhd", EODHDAdapter(eodhd_config))
    
    return router
