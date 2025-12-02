"""
Data Providers Package

This package contains all data provider adapters and infrastructure
for fetching market data from multiple sources.
"""
from app.data_providers.rate_limiter import rate_limiter, RateLimiter, RateLimitConfig
from app.data_providers.budget_tracker import (
    budget_tracker, 
    BudgetTracker, 
    BudgetConfig,
    BudgetExceededError,
)
from app.data_providers.health_monitor import (
    health_monitor,
    ProviderHealthMonitor,
    HealthConfig,
    CircuitState,
)
from app.data_providers.failover import failover_manager, FailoverManager, FailoverConfig
from app.data_providers.data_normalizer import data_normalizer, DataNormalizer, SymbolMapping
from app.data_providers.cache_manager import (
    cache_manager,
    CacheManager,
    CacheConfig,
    cached_quote,
    cached_historical,
)
from app.data_providers.gap_detector import (
    gap_detector,
    GapDetector,
    DataGap,
    MarketHours,
)
from app.data_providers.orchestrator import orchestrator, ProviderOrchestrator, OrchestratorConfig

__all__ = [
    # Rate Limiter
    "rate_limiter",
    "RateLimiter",
    "RateLimitConfig",
    # Budget Tracker
    "budget_tracker",
    "BudgetTracker",
    "BudgetConfig",
    "BudgetExceededError",
    # Health Monitor
    "health_monitor",
    "ProviderHealthMonitor",
    "HealthConfig",
    "CircuitState",
    # Failover
    "failover_manager",
    "FailoverManager",
    "FailoverConfig",
    # Data Normalizer
    "data_normalizer",
    "DataNormalizer",
    "SymbolMapping",
    # Cache Manager
    "cache_manager",
    "CacheManager",
    "CacheConfig",
    "cached_quote",
    "cached_historical",
    # Gap Detector
    "gap_detector",
    "GapDetector",
    "DataGap",
    "MarketHours",
    # Orchestrator
    "orchestrator",
    "ProviderOrchestrator",
    "OrchestratorConfig",
]
