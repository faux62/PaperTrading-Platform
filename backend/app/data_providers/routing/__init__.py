"""
Market Routing

Intelligent routing across multiple data providers
with failover, rate limiting, and health monitoring.
"""
from app.data_providers.routing.us_markets import (
    USMarketsRouter,
    RouterConfig,
    SelectionStrategy,
    ProviderStatus,
    create_us_markets_router,
)
from app.data_providers.routing.eu_markets import (
    EUMarketsRouter,
    create_eu_markets_router,
)

__all__ = [
    # US Markets
    "USMarketsRouter",
    "RouterConfig",
    "SelectionStrategy",
    "ProviderStatus",
    "create_us_markets_router",
    # EU Markets
    "EUMarketsRouter",
    "create_eu_markets_router",
]
