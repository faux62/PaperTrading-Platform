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
# US Market Providers
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
# EU & Global Providers
from app.data_providers.adapters.twelve_data import (
    TwelveDataAdapter,
    create_twelve_data_config,
)
from app.data_providers.adapters.yfinance_adapter import (
    YFinanceAdapter,
    create_yfinance_config,
)
from app.data_providers.adapters.investing import (
    InvestingAdapter,
    create_investing_config,
)
from app.data_providers.adapters.stooq import (
    StooqAdapter,
    create_stooq_config,
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
    # US Providers
    "AlpacaAdapter",
    "create_alpaca_config",
    "PolygonAdapter",
    "create_polygon_config",
    "FinnhubAdapter",
    "create_finnhub_config",
    "TiingoAdapter",
    "create_tiingo_config",
    "IntrinioAdapter",
    "create_intrinio_config",
    # EU & Global Providers
    "TwelveDataAdapter",
    "create_twelve_data_config",
    "YFinanceAdapter",
    "create_yfinance_config",
    "InvestingAdapter",
    "create_investing_config",
    "StooqAdapter",
    "create_stooq_config",
]
