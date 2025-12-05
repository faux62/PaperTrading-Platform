"""
Currency Conversion Service

Provides real-time currency conversion using free exchange rate APIs.
Caches rates to minimize API calls.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional
import httpx
from loguru import logger

# Cache for exchange rates
_rates_cache: dict[str, float] = {}
_cache_timestamp: Optional[datetime] = None
_cache_duration = timedelta(hours=1)  # Refresh rates every hour

# Supported currencies
SUPPORTED_CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD"]

# Fallback rates (approximate, used if API fails)
FALLBACK_RATES = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "JPY": 149.50,
    "CHF": 0.88,
    "CAD": 1.36,
    "AUD": 1.53,
}


async def fetch_exchange_rates(base: str = "USD") -> dict[str, float]:
    """
    Fetch current exchange rates from free API.
    
    Uses exchangerate-api.com free tier (1500 requests/month).
    Falls back to cached or static rates on failure.
    """
    global _rates_cache, _cache_timestamp
    
    # Check cache validity
    if _cache_timestamp and datetime.utcnow() - _cache_timestamp < _cache_duration:
        if _rates_cache:
            return _rates_cache
    
    try:
        # Free API: https://open.er-api.com/v6/latest/USD
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"https://open.er-api.com/v6/latest/{base}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("result") == "success":
                    rates = data.get("rates", {})
                    # Filter to supported currencies
                    _rates_cache = {
                        currency: rates.get(currency, FALLBACK_RATES.get(currency, 1.0))
                        for currency in SUPPORTED_CURRENCIES
                    }
                    _cache_timestamp = datetime.utcnow()
                    logger.info(f"Exchange rates updated: {_rates_cache}")
                    return _rates_cache
            
            logger.warning(f"Exchange rate API returned status {response.status_code}")
    except Exception as e:
        logger.error(f"Failed to fetch exchange rates: {e}")
    
    # Return cached or fallback rates
    if _rates_cache:
        logger.info("Using cached exchange rates")
        return _rates_cache
    
    logger.warning("Using fallback exchange rates")
    return FALLBACK_RATES.copy()


async def convert_currency(
    amount: float,
    from_currency: str,
    to_currency: str,
    rates: Optional[dict[str, float]] = None
) -> float:
    """
    Convert amount from one currency to another.
    
    Args:
        amount: Amount to convert
        from_currency: Source currency code (e.g., "EUR")
        to_currency: Target currency code (e.g., "USD")
        rates: Optional pre-fetched rates (base USD)
        
    Returns:
        Converted amount
    """
    if from_currency == to_currency:
        return amount
    
    if rates is None:
        rates = await fetch_exchange_rates("USD")
    
    # Convert via USD as base
    # If from_currency is EUR and rate is 0.92, then 1 EUR = 1/0.92 USD
    from_rate = rates.get(from_currency, 1.0)
    to_rate = rates.get(to_currency, 1.0)
    
    # Convert to USD first, then to target
    amount_in_usd = amount / from_rate if from_rate != 0 else amount
    result = amount_in_usd * to_rate
    
    return round(result, 2)


async def get_conversion_rate(from_currency: str, to_currency: str) -> float:
    """Get direct conversion rate between two currencies."""
    if from_currency == to_currency:
        return 1.0
    
    rates = await fetch_exchange_rates("USD")
    from_rate = rates.get(from_currency, 1.0)
    to_rate = rates.get(to_currency, 1.0)
    
    # Rate from X to Y = (1/X_rate) * Y_rate
    if from_rate == 0:
        return 1.0
    return to_rate / from_rate


def get_currency_symbol(currency: str) -> str:
    """Get currency symbol for display."""
    symbols = {
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "JPY": "¥",
        "CHF": "CHF",
        "CAD": "C$",
        "AUD": "A$",
    }
    return symbols.get(currency, currency)


def get_supported_currencies() -> list[dict]:
    """Get list of supported currencies with metadata."""
    return [
        {"code": "USD", "name": "US Dollar", "symbol": "$"},
        {"code": "EUR", "name": "Euro", "symbol": "€"},
        {"code": "GBP", "name": "British Pound", "symbol": "£"},
        {"code": "JPY", "name": "Japanese Yen", "symbol": "¥"},
        {"code": "CHF", "name": "Swiss Franc", "symbol": "CHF"},
        {"code": "CAD", "name": "Canadian Dollar", "symbol": "C$"},
        {"code": "AUD", "name": "Australian Dollar", "symbol": "A$"},
    ]
