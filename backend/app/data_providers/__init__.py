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
]
