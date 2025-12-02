"""
Provider Adapters Package

Contains adapters for all supported data providers.
Each adapter implements the BaseAdapter interface for consistent data access.
"""
from app.data_providers.adapters.base import (
    BaseAdapter,
    ProviderConfig,
    ProviderType,
    MarketType,
    DataType,
    TimeFrame,
    Quote,
    OHLCV,
    ProviderStatus,
    ProviderError,
    RateLimitError,
    AuthenticationError,
    DataNotAvailableError,
)

__all__ = [
    "BaseAdapter",
    "ProviderConfig",
    "ProviderType",
    "MarketType",
    "DataType",
    "TimeFrame",
    "Quote",
    "OHLCV",
    "ProviderStatus",
    "ProviderError",
    "RateLimitError",
    "AuthenticationError",
    "DataNotAvailableError",
]
