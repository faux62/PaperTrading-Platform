"""
Provider Orchestrator

Central coordinator for all data provider operations.
Handles request routing, data aggregation, and caching.
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import Optional, Any
from decimal import Decimal
from loguru import logger

from app.data_providers.adapters.base import (
    BaseAdapter,
    Quote,
    OHLCV,
    MarketType,
    DataType,
    TimeFrame,
    ProviderError,
)
from app.data_providers.rate_limiter import rate_limiter, RateLimitConfig
from app.data_providers.budget_tracker import budget_tracker, BudgetConfig
from app.data_providers.health_monitor import health_monitor, HealthConfig
from app.data_providers.failover import failover_manager, FailoverConfig
from app.data_providers.cache_manager import cache_manager
from app.data_providers.data_normalizer import data_normalizer
from app.data_providers.gap_detector import gap_detector, DataGap


@dataclass
class OrchestratorConfig:
    """Configuration for the orchestrator."""
    # Cache settings
    enable_cache: bool = True
    cache_quotes: bool = True
    cache_historical: bool = True
    
    # Parallel request settings
    max_parallel_requests: int = 10
    batch_size: int = 100
    
    # Data quality
    validate_data: bool = True
    fill_gaps: bool = True
    
    # Timeouts
    request_timeout: float = 30.0


class ProviderOrchestrator:
    """
    Central orchestrator for market data operations.
    
    This is the main interface for fetching market data. It coordinates:
    - Provider selection and failover
    - Caching and cache invalidation
    - Rate limiting and budget tracking
    - Data normalization and validation
    - Gap detection and backfilling
    
    Usage:
        orchestrator = ProviderOrchestrator()
        orchestrator.register_provider(alpaca_adapter)
        orchestrator.register_provider(polygon_adapter)
        
        quote = await orchestrator.get_quote("AAPL")
        history = await orchestrator.get_historical("AAPL", TimeFrame.DAY, start, end)
    """
    
    def __init__(self, config: Optional[OrchestratorConfig] = None):
        self.config = config or OrchestratorConfig()
        self._initialized = False
        self._semaphore = asyncio.Semaphore(self.config.max_parallel_requests)
    
    async def initialize(self) -> None:
        """Initialize all registered providers."""
        if self._initialized:
            return
        
        # Initialize all providers
        for name, provider in failover_manager._providers.items():
            try:
                await provider.initialize()
                logger.info(f"Initialized provider: {name}")
            except Exception as e:
                logger.error(f"Failed to initialize provider {name}: {e}")
                await health_monitor.record_failure(name, str(e))
        
        self._initialized = True
        logger.info("Provider orchestrator initialized")
    
    async def shutdown(self) -> None:
        """Shutdown all providers."""
        for name, provider in failover_manager._providers.items():
            try:
                await provider.close()
                logger.info(f"Closed provider: {name}")
            except Exception as e:
                logger.error(f"Error closing provider {name}: {e}")
        
        self._initialized = False
    
    def register_provider(
        self,
        adapter: BaseAdapter,
        rate_config: Optional[RateLimitConfig] = None,
        budget_config: Optional[BudgetConfig] = None,
        health_config: Optional[HealthConfig] = None,
    ) -> None:
        """
        Register a data provider with the orchestrator.
        
        Args:
            adapter: The provider adapter instance
            rate_config: Rate limiting configuration
            budget_config: Budget tracking configuration
            health_config: Health monitoring configuration
        """
        # Register with failover manager
        failover_manager.register_provider(adapter)
        
        # Configure rate limiter
        if rate_config:
            rate_limiter.configure(adapter.name, rate_config)
        elif adapter.config.requests_per_minute:
            rate_limiter.configure(adapter.name, RateLimitConfig(
                requests_per_minute=adapter.config.requests_per_minute,
                requests_per_day=adapter.config.requests_per_day,
            ))
        
        # Configure budget tracker
        if budget_config:
            budget_tracker.configure(adapter.name, budget_config)
        elif adapter.config.daily_budget > 0:
            budget_tracker.configure(adapter.name, BudgetConfig(
                daily_limit=adapter.config.daily_budget,
                cost_per_request=adapter.config.cost_per_request,
            ))
        
        # Configure health monitor
        health_monitor.configure(adapter.name, health_config)
        
        logger.info(f"Registered provider: {adapter.name}")
    
    # ==================== Quote Operations ====================
    
    async def get_quote(
        self,
        symbol: str,
        market_type: MarketType = MarketType.US_STOCK,
        force_refresh: bool = False,
    ) -> Quote:
        """
        Get a real-time quote for a symbol.
        
        Args:
            symbol: Ticker symbol
            market_type: Market type for provider selection
            force_refresh: Skip cache and fetch fresh data
            
        Returns:
            Quote object with current price data
        """
        symbol = symbol.upper()
        
        # Check cache first
        if self.config.enable_cache and self.config.cache_quotes and not force_refresh:
            cached = await cache_manager.get_quote(symbol)
            if cached:
                logger.debug(f"Cache hit for quote: {symbol}")
                return cached
        
        # Fetch from provider with failover
        async def fetch_quote(provider: BaseAdapter) -> Quote:
            provider_symbol = data_normalizer.get_provider_symbol(symbol, provider.name)
            quote = await provider.get_quote(provider_symbol)
            
            # Ensure canonical symbol
            quote.symbol = symbol
            
            # Validate data
            if self.config.validate_data:
                warnings = data_normalizer.validate_quote(quote)
                if warnings:
                    logger.warning(f"Quote validation warnings for {symbol}: {warnings}")
            
            return quote
        
        quote = await failover_manager.execute_with_failover(
            fetch_quote,
            market_type,
            DataType.QUOTE,
            f"get_quote({symbol})",
        )
        
        # Cache the result
        if self.config.enable_cache and self.config.cache_quotes:
            await cache_manager.set_quote(quote)
        
        return quote
    
    async def get_quotes(
        self,
        symbols: list[str],
        market_type: MarketType = MarketType.US_STOCK,
        force_refresh: bool = False,
    ) -> dict[str, Quote]:
        """
        Get quotes for multiple symbols.
        
        Args:
            symbols: List of ticker symbols
            market_type: Market type for provider selection
            force_refresh: Skip cache and fetch fresh data
            
        Returns:
            Dictionary mapping symbols to Quote objects
        """
        symbols = [s.upper() for s in symbols]
        result: dict[str, Quote] = {}
        symbols_to_fetch: list[str] = []
        
        # Check cache first
        if self.config.enable_cache and self.config.cache_quotes and not force_refresh:
            cached = await cache_manager.get_quotes(symbols)
            for symbol, quote in cached.items():
                if quote:
                    result[symbol] = quote
                else:
                    symbols_to_fetch.append(symbol)
        else:
            symbols_to_fetch = symbols
        
        if not symbols_to_fetch:
            return result
        
        # Fetch in batches
        for i in range(0, len(symbols_to_fetch), self.config.batch_size):
            batch = symbols_to_fetch[i:i + self.config.batch_size]
            
            async def fetch_quotes(provider: BaseAdapter) -> list[Quote]:
                provider_symbols = [
                    data_normalizer.get_provider_symbol(s, provider.name)
                    for s in batch
                ]
                quotes = await provider.get_quotes(provider_symbols)
                
                # Map back to canonical symbols
                for quote in quotes:
                    canonical = data_normalizer.get_canonical_symbol(
                        quote.symbol, provider.name
                    )
                    quote.symbol = canonical
                
                return quotes
            
            try:
                quotes = await failover_manager.execute_with_failover(
                    fetch_quotes,
                    market_type,
                    DataType.QUOTE,
                    f"get_quotes({len(batch)} symbols)",
                )
                
                for quote in quotes:
                    result[quote.symbol] = quote
                
                # Cache results
                if self.config.enable_cache and self.config.cache_quotes:
                    await cache_manager.set_quotes(quotes)
                    
            except ProviderError as e:
                logger.error(f"Failed to fetch batch quotes: {e}")
        
        return result
    
    # ==================== Historical Data Operations ====================
    
    async def get_historical(
        self,
        symbol: str,
        timeframe: TimeFrame = TimeFrame.DAY,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        market_type: MarketType = MarketType.US_STOCK,
        force_refresh: bool = False,
    ) -> list[OHLCV]:
        """
        Get historical OHLCV data for a symbol.
        
        Args:
            symbol: Ticker symbol
            timeframe: Data timeframe (1min, 5min, 1day, etc.)
            start_date: Start date (defaults to 1 year ago)
            end_date: End date (defaults to today)
            market_type: Market type for provider selection
            force_refresh: Skip cache and fetch fresh data
            
        Returns:
            List of OHLCV bars sorted by timestamp
        """
        symbol = symbol.upper()
        
        # Default date range
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=365)
        
        start_str = start_date.isoformat()
        end_str = end_date.isoformat()
        
        # Check cache first
        if self.config.enable_cache and self.config.cache_historical and not force_refresh:
            cached = await cache_manager.get_historical(symbol, timeframe, start_str, end_str)
            if cached:
                logger.debug(f"Cache hit for historical: {symbol}")
                return cached
        
        # Fetch from provider with failover
        async def fetch_historical(provider: BaseAdapter) -> list[OHLCV]:
            provider_symbol = data_normalizer.get_provider_symbol(symbol, provider.name)
            bars = await provider.get_historical(
                provider_symbol, start_date, end_date, timeframe
            )
            
            # Ensure canonical symbol
            for bar in bars:
                bar.symbol = symbol
            
            # Validate data
            if self.config.validate_data:
                for bar in bars:
                    warnings = data_normalizer.validate_ohlcv(bar)
                    if warnings:
                        logger.warning(f"OHLCV validation warnings for {symbol}: {warnings}")
            
            return bars
        
        bars = await failover_manager.execute_with_failover(
            fetch_historical,
            market_type,
            DataType.OHLCV,
            f"get_historical({symbol})",
        )
        
        # Detect and fill gaps if enabled
        if self.config.fill_gaps and bars:
            gaps = gap_detector.detect_gaps(bars, start_date, end_date, market_type)
            if gaps:
                logger.warning(f"Detected {len(gaps)} gaps in {symbol} data")
                # Could trigger backfill here
        
        # Cache the result
        if self.config.enable_cache and self.config.cache_historical:
            await cache_manager.set_historical(symbol, timeframe, start_str, end_str, bars)
        
        return bars
    
    async def get_latest_bar(
        self,
        symbol: str,
        timeframe: TimeFrame = TimeFrame.DAY,
        market_type: MarketType = MarketType.US_STOCK,
    ) -> Optional[OHLCV]:
        """Get the latest OHLCV bar for a symbol."""
        symbol = symbol.upper()
        
        # Check cache
        cached = await cache_manager.get_latest_bar(symbol, timeframe)
        if cached:
            return cached
        
        # Fetch recent history and get last bar
        end_date = date.today()
        start_date = end_date - timedelta(days=7)  # Last week
        
        bars = await self.get_historical(
            symbol, timeframe, start_date, end_date, market_type
        )
        
        if bars:
            latest = bars[-1]
            await cache_manager.set_latest_bar(latest)
            return latest
        
        return None
    
    # ==================== Batch Operations ====================
    
    async def get_historical_batch(
        self,
        symbols: list[str],
        timeframe: TimeFrame = TimeFrame.DAY,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        market_type: MarketType = MarketType.US_STOCK,
    ) -> dict[str, list[OHLCV]]:
        """
        Get historical data for multiple symbols in parallel.
        
        Args:
            symbols: List of ticker symbols
            timeframe: Data timeframe
            start_date: Start date
            end_date: End date
            market_type: Market type
            
        Returns:
            Dictionary mapping symbols to OHLCV lists
        """
        result: dict[str, list[OHLCV]] = {}
        
        async def fetch_one(symbol: str) -> tuple[str, list[OHLCV]]:
            async with self._semaphore:
                try:
                    bars = await self.get_historical(
                        symbol, timeframe, start_date, end_date, market_type
                    )
                    return (symbol, bars)
                except Exception as e:
                    logger.error(f"Failed to fetch historical for {symbol}: {e}")
                    return (symbol, [])
        
        tasks = [fetch_one(s) for s in symbols]
        results = await asyncio.gather(*tasks)
        
        for symbol, bars in results:
            result[symbol.upper()] = bars
        
        return result
    
    # ==================== Company Info & Search Operations ====================
    
    async def get_company_info(self, symbol: str) -> Optional[dict[str, Any]]:
        """
        Get company information for a symbol.
        
        Uses providers that support company info (primarily yfinance).
        
        Args:
            symbol: Ticker symbol
            
        Returns:
            Dictionary with company info or None if not found
        """
        symbol = symbol.upper()
        
        # Try providers that support company info
        # Currently only yfinance has this capability
        yfinance_provider = failover_manager.get_provider("yfinance")
        if yfinance_provider and hasattr(yfinance_provider, 'get_company_info'):
            try:
                info = await yfinance_provider.get_company_info(symbol)
                if info:
                    return info
            except Exception as e:
                logger.warning(f"Failed to get company info for {symbol}: {e}")
        
        return None
    
    async def search_symbols(
        self,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Search for symbols by name or ticker.
        
        Uses providers that support search functionality.
        
        Args:
            query: Search query (symbol or company name)
            limit: Maximum results to return
            
        Returns:
            List of matching symbols with metadata
        """
        query = query.strip().upper()
        results: list[dict[str, Any]] = []
        
        # Try yfinance provider for search
        yfinance_provider = failover_manager.get_provider("yfinance")
        if yfinance_provider and hasattr(yfinance_provider, 'search_symbols'):
            try:
                yf_results = await yfinance_provider.search_symbols(query)
                results.extend(yf_results)
            except Exception as e:
                logger.warning(f"yfinance search failed: {e}")
        
        # If no results from search, try direct symbol lookup
        if not results:
            try:
                info = await self.get_company_info(query)
                if info and info.get("name"):
                    results.append({
                        "symbol": query,
                        "name": info.get("name"),
                        "exchange": info.get("exchange"),
                        "sector": info.get("sector"),
                        "type": "stock",
                        "currency": info.get("currency"),
                    })
            except Exception:
                pass
        
        return results[:limit]
    
    async def get_index_quote(self, symbol: str) -> Optional[Quote]:
        """
        Get quote for a market index.
        
        Args:
            symbol: Index symbol (e.g., ^GSPC, ^DJI, ^IXIC)
            
        Returns:
            Quote object or None
        """
        # Use INDEX market type
        try:
            quote = await self.get_quote(
                symbol,
                market_type=MarketType.INDEX,
                force_refresh=True,
            )
            return quote
        except Exception as e:
            logger.warning(f"Failed to get index quote for {symbol}: {e}")
            return None
    
    async def get_indices_quotes(
        self,
        symbols: list[str],
    ) -> dict[str, Quote]:
        """
        Get quotes for multiple market indices.
        
        Args:
            symbols: List of index symbols
            
        Returns:
            Dictionary mapping symbols to Quote objects
        """
        results: dict[str, Quote] = {}
        
        for symbol in symbols:
            try:
                quote = await self.get_index_quote(symbol)
                if quote:
                    results[symbol] = quote
            except Exception as e:
                logger.warning(f"Failed to get quote for index {symbol}: {e}")
        
        return results
    
    # ==================== Status & Monitoring ====================
    
    def get_status(self) -> dict[str, Any]:
        """Get comprehensive status of the orchestrator."""
        return {
            "initialized": self._initialized,
            "config": {
                "enable_cache": self.config.enable_cache,
                "max_parallel_requests": self.config.max_parallel_requests,
                "validate_data": self.config.validate_data,
            },
            "providers": failover_manager.get_status(),
            "cache": cache_manager.get_stats(),
            "health": health_monitor.get_all_health(),
            "budgets": budget_tracker.get_all_stats(),
        }
    
    def get_healthy_providers(self) -> list[str]:
        """Get list of healthy providers."""
        return health_monitor.get_healthy_providers()
    
    async def check_providers(self) -> dict[str, bool]:
        """Run health check on all providers."""
        results: dict[str, bool] = {}
        
        for name, provider in failover_manager._providers.items():
            try:
                healthy = await provider.health_check()
                results[name] = healthy
                if healthy:
                    await health_monitor.record_success(name, 0)
                else:
                    await health_monitor.record_failure(name, "Health check failed")
            except Exception as e:
                results[name] = False
                await health_monitor.record_failure(name, str(e))
        
        return results


# Global orchestrator instance
orchestrator = ProviderOrchestrator()
