"""
Provider Initialization Module

Initializes all data providers based on user configuration.
Loads API keys from database settings and registers providers with the orchestrator.
"""
from decimal import Decimal
from typing import Optional
from loguru import logger

from app.data_providers import orchestrator, rate_limiter, budget_tracker, failover_manager
from app.data_providers.rate_limiter import RateLimitConfig
from app.data_providers.budget_tracker import BudgetConfig

# Import all adapters
from app.data_providers.adapters.alpaca import AlpacaAdapter, create_alpaca_config
from app.data_providers.adapters.alpha_vantage import AlphaVantageAdapter, create_alpha_vantage_config
from app.data_providers.adapters.eodhd import EODHDAdapter, create_eodhd_config
from app.data_providers.adapters.finnhub import FinnhubAdapter, create_finnhub_config
from app.data_providers.adapters.fmp import FMPAdapter, create_fmp_config
from app.data_providers.adapters.intrinio import IntrinioAdapter, create_intrinio_config
from app.data_providers.adapters.marketstack import MarketstackAdapter, create_marketstack_config
from app.data_providers.adapters.nasdaq_datalink import NasdaqDataLinkAdapter, create_nasdaq_datalink_config
from app.data_providers.adapters.polygon import PolygonAdapter, create_polygon_config
from app.data_providers.adapters.stockdata import StockDataAdapter, create_stockdata_config
from app.data_providers.adapters.tiingo import TiingoAdapter, create_tiingo_config
from app.data_providers.adapters.twelve_data import TwelveDataAdapter, create_twelve_data_config
from app.data_providers.adapters.yfinance_adapter import YFinanceAdapter, create_yfinance_config
from app.data_providers.adapters.stooq import StooqAdapter, create_stooq_config
from app.data_providers.adapters.investing import InvestingAdapter, create_investing_config
from app.data_providers.adapters.investiny_adapter import InvestinyAdapter, create_investiny_config
from app.data_providers.adapters.nasdaq import NasdaqAdapter, create_nasdaq_config
from app.data_providers.adapters.frankfurter import FrankfurterAdapter, create_frankfurter_config


# Default rate limits and budgets for free tiers
PROVIDER_DEFAULTS = {
    "finnhub": {
        "requests_per_minute": 60,
        "requests_per_day": 0,  # Unlimited
        "daily_budget": Decimal("0"),
    },
    "polygon": {
        "requests_per_minute": 5,  # Free tier
        "requests_per_day": 0,
        "daily_budget": Decimal("0"),
    },
    "alpha_vantage": {
        "requests_per_minute": 5,
        "requests_per_day": 100,
        "daily_budget": Decimal("0"),
    },
    "tiingo": {
        "requests_per_minute": 0,  # No per-minute limit
        "requests_per_day": 1000,
        "daily_budget": Decimal("0"),
    },
    "twelve_data": {
        "requests_per_minute": 8,
        "requests_per_day": 800,
        "daily_budget": Decimal("0"),
    },
    "alpaca": {
        "requests_per_minute": 200,
        "requests_per_day": 0,
        "daily_budget": Decimal("0"),
    },
    "fmp": {
        "requests_per_minute": 5,
        "requests_per_day": 250,
        "daily_budget": Decimal("0"),
    },
    "eodhd": {
        "requests_per_minute": 0,
        "requests_per_day": 20,  # Free tier
        "daily_budget": Decimal("0"),
    },
    "intrinio": {
        "requests_per_minute": 60,
        "requests_per_day": 0,
        "daily_budget": Decimal("0"),
    },
    "marketstack": {
        "requests_per_minute": 0,
        "requests_per_day": 100,  # Free tier
        "daily_budget": Decimal("0"),
    },
    "nasdaq_datalink": {
        "requests_per_minute": 0,
        "requests_per_day": 50,
        "daily_budget": Decimal("0"),
    },
    "stockdata": {
        "requests_per_minute": 5,
        "requests_per_day": 100,
        "daily_budget": Decimal("0"),
    },
    "yfinance": {
        "requests_per_minute": 0,  # Rate limits are unofficial
        "requests_per_day": 0,
        "daily_budget": Decimal("0"),
    },
    "stooq": {
        "requests_per_minute": 0,
        "requests_per_day": 0,
        "daily_budget": Decimal("0"),
    },
    "investing": {
        "requests_per_minute": 0,
        "requests_per_day": 0,
        "daily_budget": Decimal("0"),
    },
    "investiny": {
        "requests_per_minute": 30,
        "requests_per_day": 2000,
        "daily_budget": Decimal("0"),
    },
    "nasdaq": {
        "requests_per_minute": 30,
        "requests_per_day": 5000,
        "daily_budget": Decimal("0"),
    },
    "frankfurter": {
        "requests_per_minute": 60,
        "requests_per_day": 10000,
        "daily_budget": Decimal("0"),
    },
}


async def initialize_providers(api_keys: dict[str, str]) -> dict[str, bool]:
    """
    Initialize all providers with the given API keys.
    
    Args:
        api_keys: Dictionary mapping provider names to API keys
        
    Returns:
        Dictionary mapping provider names to initialization status
    """
    results = {}
    
    # Map of provider names to (adapter_class, config_factory)
    provider_factories = {
        "finnhub": (FinnhubAdapter, create_finnhub_config),
        "polygon": (PolygonAdapter, create_polygon_config),
        "alpha_vantage": (AlphaVantageAdapter, create_alpha_vantage_config),
        "tiingo": (TiingoAdapter, create_tiingo_config),
        "twelve_data": (TwelveDataAdapter, create_twelve_data_config),
        "alpaca": (AlpacaAdapter, create_alpaca_config),
        "fmp": (FMPAdapter, create_fmp_config),
        "eodhd": (EODHDAdapter, create_eodhd_config),
        # "intrinio": (IntrinioAdapter, create_intrinio_config),  # Disabled - no active subscription
        "marketstack": (MarketstackAdapter, create_marketstack_config),
        # "nasdaq_datalink": (NasdaqDataLinkAdapter, create_nasdaq_datalink_config),  # Disabled - WIKI dataset discontinued
        "stockdata": (StockDataAdapter, create_stockdata_config),
        "yfinance": (YFinanceAdapter, create_yfinance_config),
        "stooq": (StooqAdapter, create_stooq_config),
        # "investing": (InvestingAdapter, create_investing_config),  # Disabled - scraping blocked (403)
        # "investiny": (InvestinyAdapter, create_investiny_config),  # Disabled - TVC API Cloudflare protected
        "nasdaq": (NasdaqAdapter, create_nasdaq_config),  # Free - US stocks/ETF
        "frankfurter": (FrankfurterAdapter, create_frankfurter_config),  # Free - Forex (ECB)
    }
    
    # Initialize each provider that has an API key configured
    for provider_name, api_key in api_keys.items():
        if not api_key or provider_name not in provider_factories:
            continue
        
        try:
            adapter_class, config_factory = provider_factories[provider_name]
            
            # Create config - some providers need additional params
            if provider_name == "alpaca":
                # Alpaca needs both key and secret
                secret = api_keys.get("alpaca_secret", "")
                if secret:
                    config = config_factory(api_key, secret)
                else:
                    logger.warning(f"Skipping {provider_name}: missing secret")
                    results[provider_name] = False
                    continue
            elif provider_name in ("yfinance", "stooq", "investing", "investiny"):
                # These don't need API keys
                config = config_factory()
            else:
                config = config_factory(api_key)
            
            # Create adapter
            adapter = adapter_class(config)
            
            # Get default limits
            defaults = PROVIDER_DEFAULTS.get(provider_name, {})
            
            # Create rate limit config
            rate_config = RateLimitConfig(
                requests_per_minute=defaults.get("requests_per_minute", 60),
                requests_per_day=defaults.get("requests_per_day", 0),
            )
            
            # Create budget config
            budget_config = BudgetConfig(
                daily_limit=defaults.get("daily_budget", Decimal("0")),
                cost_per_request=Decimal("0"),
            )
            
            # Register with orchestrator
            orchestrator.register_provider(
                adapter,
                rate_config=rate_config,
                budget_config=budget_config,
            )
            
            # Initialize the adapter
            await adapter.initialize()
            
            results[provider_name] = True
            logger.info(f"✅ Provider {provider_name} initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize provider {provider_name}: {e}")
            results[provider_name] = False
    
    # Always initialize free providers that don't need API keys
    for free_provider in ("yfinance", "stooq", "nasdaq", "frankfurter"):
        if free_provider not in results or not results.get(free_provider):
            if free_provider not in provider_factories:
                continue  # Skip disabled providers
            try:
                adapter_class, config_factory = provider_factories[free_provider]
                config = config_factory()
                adapter = adapter_class(config)
                
                defaults = PROVIDER_DEFAULTS.get(free_provider, {})
                rate_config = RateLimitConfig(
                    requests_per_minute=defaults.get("requests_per_minute", 60),
                    requests_per_day=defaults.get("requests_per_day", 0),
                )
                
                orchestrator.register_provider(adapter, rate_config=rate_config)
                await adapter.initialize()
                
                results[free_provider] = True
                logger.info(f"✅ Free provider {free_provider} initialized")
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize free provider {free_provider}: {e}")
                results[free_provider] = False
    
    # Initialize orchestrator
    await orchestrator.initialize()
    
    return results


async def shutdown_providers():
    """Shutdown all providers gracefully."""
    try:
        await orchestrator.close()
        logger.info("All providers shut down")
    except Exception as e:
        logger.error(f"Error shutting down providers: {e}")


def get_provider_status() -> dict:
    """Get status of all registered providers."""
    status = {}
    
    for name in failover_manager._providers.keys():
        rate_stats = rate_limiter.get_stats(name)
        status[name] = {
            "registered": True,
            "rate_limit": rate_stats,
        }
    
    return status
