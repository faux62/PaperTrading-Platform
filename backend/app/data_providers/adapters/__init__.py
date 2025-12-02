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
from app.data_providers.adapters.alpaca import (
    AlpacaAdapter,
    create_alpaca_config,
)
from app.data_providers.adapters.polygon import (
    PolygonAdapter,
    create_polygon_config,
)
from app.data_providers.adapters.finnhub import (
    FinnhubAdapter,
    create_finnhub_config,
)
from app.data_providers.adapters.tiingo import (
    TiingoAdapter,
    create_tiingo_config,
)
from app.data_providers.adapters.intrinio import (
    IntrinioAdapter,
    create_intrinio_config,
)

__all__ = [
    # Base
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
    # Alpaca
    "AlpacaAdapter",
    "create_alpaca_config",
    # Polygon
    "PolygonAdapter",
    "create_polygon_config",
    # Finnhub
    "FinnhubAdapter",
    "create_finnhub_config",
    # Tiingo
    "TiingoAdapter",
    "create_tiingo_config",
    # Intrinio
    "IntrinioAdapter",
    "create_intrinio_config",
]
