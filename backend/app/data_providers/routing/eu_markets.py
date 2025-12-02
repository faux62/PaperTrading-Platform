"""
EU Markets Router

Intelligent routing layer for European stock market data providers.
Manages failover, load balancing, and provider selection for
EU markets (FTSE MIB, DAX, CAC40, IBEX, etc.).
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Any, Callable, Awaitable
from dataclasses import dataclass
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
from app.data_providers.routing.us_markets import (
    SelectionStrategy,
    ProviderStatus,
    RouterConfig,
)


# EU Exchange mapping
EU_EXCHANGES = {
    "MIB": "italy",       # FTSE MIB
    "MI": "italy",        # Borsa Italiana
    "XMIL": "italy",
    "DAX": "germany",     # German DAX
    "XETRA": "germany",
    "XFRA": "germany",
    "CAC": "france",      # CAC 40
    "EPA": "france",      # Euronext Paris
    "IBEX": "spain",      # IBEX 35
    "BME": "spain",       # Bolsa de Madrid
    "LSE": "united kingdom",  # London Stock Exchange
    "LON": "united kingdom",
    "AMS": "netherlands", # Amsterdam
    "BRU": "belgium",     # Brussels
    "LIS": "portugal",    # Lisbon
    "SIX": "switzerland", # Swiss Exchange
    "VIE": "austria",     # Vienna
}

# Symbol suffix for yfinance
YFINANCE_SUFFIXES = {
    "italy": ".MI",
    "germany": ".DE",
    "france": ".PA",
    "spain": ".MC",
    "united kingdom": ".L",
    "netherlands": ".AS",
    "belgium": ".BR",
    "portugal": ".LS",
    "switzerland": ".SW",
    "austria": ".VI",
}


class EUMarketsRouter:
    """
    Router for European stock market data providers.
    
    Manages multiple providers specialized in EU markets with
    intelligent selection, automatic failover, and country-aware routing.
    
    Features:
    - Country-specific routing (Italy, Germany, France, Spain, UK)
    - Provider registration and management
    - Automatic failover on errors
    - Rate limit tracking
    - Health monitoring
    
    Usage:
        router = EUMarketsRouter()
        router.register_provider("twelve_data", twelve_data_adapter)
        router.register_provider("investing", investing_adapter)
        await router.initialize()
        
        quote = await router.get_quote("ENI", country="italy")
        bars = await router.get_historical("SAP", country="germany")
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
        logger.info(f"Registered EU market provider: {name} (priority: {adapter.config.priority})")
    
    def unregister_provider(self, name: str) -> None:
        """Unregister a data provider."""
        if name in self._providers:
            del self._providers[name]
            logger.info(f"Unregistered EU market provider: {name}")
    
    async def initialize(self) -> None:
        """Initialize all registered providers."""
        init_tasks = []
        for name, status in self._providers.items():
            init_tasks.append(self._init_provider(name, status))
        
        await asyncio.gather(*init_tasks, return_exceptions=True)
        
        # Start health monitoring
        self._health_check_task = asyncio.create_task(self._health_monitor())
        
        logger.info(f"EU Markets Router initialized with {len(self._providers)} providers")
    
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
        logger.info("EU Markets Router closed")
    
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
            suffix = YFINANCE_SUFFIXES.get(country, ".MI")
            if not symbol.endswith(suffix):
                return f"{symbol}{suffix}"
        elif provider_name == "stooq":
            # Stooq uses different suffixes
            suffix_map = {
                "italy": "",  # Italian stocks may not need suffix
                "germany": ".DE",
                "france": ".FR",
                "united kingdom": ".UK",
            }
            suffix = suffix_map.get(country, "")
            if suffix and not symbol.endswith(suffix):
                return f"{symbol}{suffix}"
        
        return symbol
    
    def _get_country_from_exchange(self, exchange: str) -> str:
        """Get country from exchange code."""
        return EU_EXCHANGES.get(exchange.upper(), "italy")
    
    # ==================== Data Methods ====================
    
    async def get_quote(
        self,
        symbol: str,
        country: str = "italy",
    ) -> Quote:
        """Get quote with automatic failover."""
        tried_providers: set[str] = set()
        last_error: Optional[Exception] = None
        
        for attempt in range(self.config.max_retries):
            provider = self._select_provider(exclude=tried_providers)
            
            if not provider:
                if last_error:
                    raise last_error
                raise ProviderError("eu_router", "No available providers")
            
            tried_providers.add(provider.name)
            
            try:
                formatted_symbol = self._format_symbol_for_provider(
                    symbol, provider.name, country
                )
                
                start_time = datetime.now()
                
                # Special handling for investing.com (requires country param)
                if provider.name == "investing":
                    quote = await provider.adapter.get_quote(formatted_symbol, country=country)
                else:
                    quote = await provider.adapter.get_quote(formatted_symbol)
                
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                provider.success_count += 1
                provider.total_latency_ms += latency_ms
                provider.last_success = datetime.now()
                provider.error_count = 0
                
                # Normalize symbol in quote
                quote.symbol = symbol.upper()
                quote.market_type = MarketType.EU_STOCK
                
                return quote
                
            except RateLimitError as e:
                provider.is_rate_limited = True
                if e.retry_after:
                    from datetime import timedelta
                    provider.rate_limit_reset = datetime.now() + timedelta(seconds=e.retry_after)
                last_error = e
                logger.warning(f"Provider {provider.name} rate limited")
                
            except DataNotAvailableError as e:
                # Try next provider for missing data
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
        
        raise last_error or ProviderError("eu_router", "All providers failed")
    
    async def get_quotes(
        self,
        symbols: list[str],
        country: str = "italy",
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
                
                # Normalize symbols
                for i, quote in enumerate(quotes):
                    quote.symbol = symbols[i].upper() if i < len(symbols) else quote.symbol
                    quote.market_type = MarketType.EU_STOCK
                
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
        country: str = "italy",
    ) -> list[OHLCV]:
        """Get historical data with automatic failover."""
        tried_providers: set[str] = set()
        last_error: Optional[Exception] = None
        
        for attempt in range(self.config.max_retries):
            provider = self._select_provider(exclude=tried_providers)
            
            if not provider:
                if last_error:
                    raise last_error
                raise ProviderError("eu_router", "No available providers")
            
            tried_providers.add(provider.name)
            
            try:
                formatted_symbol = self._format_symbol_for_provider(
                    symbol, provider.name, country
                )
                
                # Special handling for investing.com
                if provider.name == "investing":
                    bars = await provider.adapter.get_historical(
                        formatted_symbol, start_date, end_date, timeframe, country=country
                    )
                else:
                    bars = await provider.adapter.get_historical(
                        formatted_symbol, start_date, end_date, timeframe
                    )
                
                # Normalize symbols
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
        
        raise last_error or ProviderError("eu_router", "All providers failed")
    
    # ==================== EU-Specific Methods ====================
    
    async def get_index_quote(
        self,
        index_name: str,
        country: str = "italy",
    ) -> Quote:
        """Get quote for a European index."""
        # Map common index names to symbols
        index_map = {
            "FTSE MIB": ("FTSEMIB", "italy"),
            "MIB": ("FTSEMIB", "italy"),
            "DAX": ("^GDAXI", "germany"),
            "CAC 40": ("^FCHI", "france"),
            "IBEX 35": ("^IBEX", "spain"),
            "FTSE 100": ("^FTSE", "united kingdom"),
            "EURO STOXX 50": ("^STOXX50E", "germany"),
            "AEX": ("^AEX", "netherlands"),
            "SMI": ("^SSMI", "switzerland"),
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

def create_eu_markets_router(
    twelve_data_config: Optional[ProviderConfig] = None,
    yfinance_config: Optional[ProviderConfig] = None,
    investing_config: Optional[ProviderConfig] = None,
    stooq_config: Optional[ProviderConfig] = None,
    router_config: Optional[RouterConfig] = None,
) -> EUMarketsRouter:
    """
    Factory function to create an EU Markets Router with configured providers.
    
    Args:
        twelve_data_config: Configuration for Twelve Data adapter
        yfinance_config: Configuration for yfinance adapter
        investing_config: Configuration for Investing.com adapter
        stooq_config: Configuration for Stooq adapter
        router_config: Router configuration
        
    Returns:
        Configured EUMarketsRouter instance
    """
    from app.data_providers.adapters.twelve_data import TwelveDataAdapter
    from app.data_providers.adapters.yfinance_adapter import YFinanceAdapter
    from app.data_providers.adapters.investing import InvestingAdapter
    from app.data_providers.adapters.stooq import StooqAdapter
    
    router = EUMarketsRouter(config=router_config)
    
    if twelve_data_config:
        router.register_provider("twelve_data", TwelveDataAdapter(twelve_data_config))
    
    if yfinance_config:
        router.register_provider("yfinance", YFinanceAdapter(yfinance_config))
    
    if investing_config:
        router.register_provider("investing", InvestingAdapter(investing_config))
    
    if stooq_config:
        router.register_provider("stooq", StooqAdapter(stooq_config))
    
    return router
