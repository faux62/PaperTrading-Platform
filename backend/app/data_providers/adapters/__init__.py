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
# Remaining Global Providers
from app.data_providers.adapters.eodhd import (
    EODHDAdapter,
    create_eodhd_config,
)
from app.data_providers.adapters.fmp import (
    FMPAdapter,
    create_fmp_config,
)
from app.data_providers.adapters.alpha_vantage import (
    AlphaVantageAdapter,
    create_alpha_vantage_config,
)
from app.data_providers.adapters.nasdaq_datalink import (
    NasdaqDataLinkAdapter,
    create_nasdaq_datalink_config,
)
from app.data_providers.adapters.marketstack import (
    MarketstackAdapter,
    create_marketstack_config,
)
from app.data_providers.adapters.stockdata import (
    StockDataAdapter,
    create_stockdata_config,
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
    # Remaining Global Providers
    "EODHDAdapter",
    "create_eodhd_config",
    "FMPAdapter",
    "create_fmp_config",
    "AlphaVantageAdapter",
    "create_alpha_vantage_config",
    "NasdaqDataLinkAdapter",
    "create_nasdaq_datalink_config",
    "MarketstackAdapter",
    "create_marketstack_config",
    "StockDataAdapter",
    "create_stockdata_config",
]
