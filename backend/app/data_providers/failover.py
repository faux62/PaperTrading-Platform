"""
Failover Manager

Manages automatic failover between data providers.
Selects the best available provider based on health, priority, and capabilities.
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, TypeVar, Generic, Callable, Awaitable, Any
from loguru import logger

from app.data_providers.adapters.base import (
    BaseAdapter,
    MarketType,
    DataType,
    ProviderError,
    RateLimitError,
)
from app.data_providers.health_monitor import health_monitor, CircuitState
from app.data_providers.rate_limiter import rate_limiter
from app.data_providers.budget_tracker import budget_tracker, BudgetExceededError


T = TypeVar('T')


@dataclass
class FailoverConfig:
    """Configuration for failover behavior."""
    max_retries: int = 3
    retry_delay_base: float = 1.0  # Base delay for exponential backoff
    retry_delay_max: float = 30.0   # Maximum retry delay
    
    # Provider selection strategy
    prefer_healthy: bool = True     # Prefer healthy providers
    prefer_budget: bool = True      # Prefer providers with remaining budget
    prefer_low_latency: bool = True # Prefer providers with lower latency


@dataclass
class ProviderGroup:
    """A group of providers for a specific market/data type combination."""
    market_type: MarketType
    data_type: DataType
    providers: list[BaseAdapter] = field(default_factory=list)
    
    def get_ordered_providers(self) -> list[BaseAdapter]:
        """Get providers ordered by priority (lower = better)."""
        return sorted(self.providers, key=lambda p: p.config.priority)


class FailoverManager:
    """
    Manages failover between data providers.
    
    Features:
    - Automatic provider selection based on health and priority
    - Retry with exponential backoff
    - Transparent failover to backup providers
    - Request routing based on market/data type
    """
    
    def __init__(self, config: Optional[FailoverConfig] = None):
        self.config = config or FailoverConfig()
        self._providers: dict[str, BaseAdapter] = {}
        self._groups: dict[tuple[MarketType, DataType], ProviderGroup] = {}
        self._lock = asyncio.Lock()
        
    def register_provider(self, adapter: BaseAdapter) -> None:
        """Register a data provider adapter."""
        self._providers[adapter.name] = adapter
        
        # Add to appropriate groups based on capabilities
        for market in adapter.config.supported_markets:
            for data_type in adapter.config.supported_data_types:
                key = (market, data_type)
                if key not in self._groups:
                    self._groups[key] = ProviderGroup(
                        market_type=market,
                        data_type=data_type,
                    )
                self._groups[key].providers.append(adapter)
        
        # Configure health monitor
        health_monitor.configure(adapter.name)
        
        logger.info(
            f"Registered provider: {adapter.name} "
            f"(markets: {adapter.config.supported_markets}, "
            f"data_types: {adapter.config.supported_data_types})"
        )
    
    def get_provider(self, name: str) -> Optional[BaseAdapter]:
        """Get a specific provider by name."""
        return self._providers.get(name)
    
    def get_providers_for(
        self, 
        market_type: MarketType, 
        data_type: DataType
    ) -> list[BaseAdapter]:
        """Get all providers that support a market/data type combination."""
        key = (market_type, data_type)
        group = self._groups.get(key)
        if not group:
            return []
        return group.get_ordered_providers()
    
    def select_provider(
        self,
        market_type: MarketType,
        data_type: DataType,
        exclude: Optional[list[str]] = None,
    ) -> Optional[BaseAdapter]:
        """
        Select the best available provider for a request.
        
        Selection criteria (in order):
        1. Supports required market and data type
        2. Is healthy (circuit not open)
        3. Has remaining budget
        4. Has available rate limit capacity
        5. Lower priority number = higher preference
        6. Lower latency (if enabled)
        
        Args:
            market_type: Target market type
            data_type: Required data type
            exclude: Provider names to exclude
            
        Returns:
            Best available provider or None
        """
        exclude = exclude or []
        candidates = self.get_providers_for(market_type, data_type)
        
        if not candidates:
            logger.warning(
                f"No providers registered for {market_type.value}/{data_type.value}"
            )
            return None
        
        # Score and filter candidates
        scored_candidates: list[tuple[float, BaseAdapter]] = []
        
        for provider in candidates:
            if provider.name in exclude:
                continue
            
            # Check health
            if self.config.prefer_healthy:
                if not health_monitor.can_request(provider.name):
                    continue
            
            # Check budget
            if self.config.prefer_budget:
                if not budget_tracker.can_afford(provider.name):
                    continue
            
            # Check rate limit
            if not rate_limiter.can_proceed(provider.name):
                continue
            
            # Calculate score (lower is better)
            score = self._calculate_provider_score(provider)
            scored_candidates.append((score, provider))
        
        if not scored_candidates:
            logger.warning(
                f"No available providers for {market_type.value}/{data_type.value}"
            )
            return None
        
        # Select best candidate
        scored_candidates.sort(key=lambda x: x[0])
        selected = scored_candidates[0][1]
        
        logger.debug(
            f"Selected provider {selected.name} for "
            f"{market_type.value}/{data_type.value}"
        )
        
        return selected
    
    def _calculate_provider_score(self, provider: BaseAdapter) -> float:
        """
        Calculate a score for provider selection.
        Lower score = better provider.
        """
        score = float(provider.config.priority)
        
        # Adjust for latency if enabled
        if self.config.prefer_low_latency:
            health = health_monitor.get_health(provider.name)
            if health.get("metrics"):
                avg_latency = health["metrics"].get("avg_latency_ms", 0)
                # Add latency penalty (normalized to 0-10 range)
                score += min(10, avg_latency / 1000)
        
        # Adjust for error rate
        health = health_monitor.get_health(provider.name)
        if health.get("metrics"):
            error_rate = health["metrics"].get("error_rate", 0)
            # Add error rate penalty
            score += error_rate * 50  # 1% error = +0.5 to score
        
        return score
    
    async def execute_with_failover(
        self,
        operation: Callable[[BaseAdapter], Awaitable[T]],
        market_type: MarketType,
        data_type: DataType,
        operation_name: str = "request",
    ) -> T:
        """
        Execute an operation with automatic failover.
        
        If the primary provider fails, automatically tries backup providers.
        
        Args:
            operation: Async function that takes a provider and returns result
            market_type: Target market type
            data_type: Required data type
            operation_name: Name for logging
            
        Returns:
            Result from the operation
            
        Raises:
            ProviderError: If all providers fail
        """
        excluded: list[str] = []
        last_error: Optional[Exception] = None
        
        for attempt in range(self.config.max_retries):
            # Select a provider
            provider = self.select_provider(market_type, data_type, exclude=excluded)
            
            if not provider:
                break
            
            try:
                # Acquire rate limit
                await rate_limiter.acquire(provider.name)
                
                # Check budget
                await budget_tracker.check_and_record(provider.name)
                
                # Execute the operation
                start_time = datetime.utcnow()
                result = await operation(provider)
                
                # Record success
                latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                await health_monitor.record_success(provider.name, latency_ms)
                
                return result
                
            except RateLimitError as e:
                logger.warning(f"Rate limit hit for {provider.name}: {e}")
                excluded.append(provider.name)
                last_error = e
                
            except BudgetExceededError as e:
                logger.warning(f"Budget exceeded for {provider.name}: {e}")
                excluded.append(provider.name)
                last_error = e
                
            except ProviderError as e:
                logger.error(f"Provider error from {provider.name}: {e}")
                await health_monitor.record_failure(provider.name, str(e))
                
                if not e.recoverable:
                    raise
                
                excluded.append(provider.name)
                last_error = e
                
                # Apply backoff before retry
                delay = min(
                    self.config.retry_delay_base * (2 ** attempt),
                    self.config.retry_delay_max
                )
                logger.info(f"Retrying in {delay:.1f}s...")
                await asyncio.sleep(delay)
                
            except Exception as e:
                logger.error(f"Unexpected error from {provider.name}: {e}")
                await health_monitor.record_failure(provider.name, str(e))
                excluded.append(provider.name)
                last_error = e
        
        # All providers failed
        error_msg = f"All providers failed for {operation_name}"
        if last_error:
            error_msg += f": {last_error}"
        raise ProviderError("failover", error_msg, recoverable=False)
    
    async def broadcast(
        self,
        operation: Callable[[BaseAdapter], Awaitable[T]],
        market_type: MarketType,
        data_type: DataType,
    ) -> list[tuple[str, T | Exception]]:
        """
        Execute an operation on all available providers.
        
        Useful for comparing data across providers or redundant requests.
        
        Returns:
            List of (provider_name, result_or_exception) tuples
        """
        providers = self.get_providers_for(market_type, data_type)
        results: list[tuple[str, T | Exception]] = []
        
        async def execute_one(provider: BaseAdapter) -> tuple[str, T | Exception]:
            try:
                result = await operation(provider)
                return (provider.name, result)
            except Exception as e:
                return (provider.name, e)
        
        tasks = [execute_one(p) for p in providers if health_monitor.can_request(p.name)]
        results = await asyncio.gather(*tasks)
        
        return results
    
    def get_status(self) -> dict:
        """Get status of all registered providers."""
        return {
            "providers": {
                name: {
                    "health": health_monitor.get_health(name),
                    "rate_limit": rate_limiter.get_stats(name),
                    "budget": budget_tracker.get_stats(name),
                    "config": {
                        "priority": adapter.config.priority,
                        "markets": [m.value for m in adapter.config.supported_markets],
                        "data_types": [d.value for d in adapter.config.supported_data_types],
                    }
                }
                for name, adapter in self._providers.items()
            },
            "groups": {
                f"{market.value}/{data.value}": [
                    p.name for p in group.get_ordered_providers()
                ]
                for (market, data), group in self._groups.items()
            }
        }


# Global failover manager instance
failover_manager = FailoverManager()
