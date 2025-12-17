"""
Currency Conversion Service

Provides real-time currency conversion using free exchange rate APIs.
Caches rates to minimize API calls.

SINGLE CURRENCY MODEL:
This module provides the unified convert() function that should be used
everywhere in the platform for currency conversions. All portfolios use
a single base currency, and conversions happen on-demand when trading
assets in different currencies.
"""
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Tuple
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


# =============================================================================
# UNIFIED CONVERT FUNCTION - USE THIS EVERYWHERE
# =============================================================================

async def convert(
    amount: Decimal,
    from_currency: str,
    to_currency: str,
) -> Tuple[Decimal, Decimal]:
    """
    THE UNIFIED CURRENCY CONVERSION FUNCTION.
    
    Use this function everywhere in the platform for currency conversions.
    It returns both the converted amount and the exchange rate used,
    which is essential for audit trail and P&L calculations.
    
    Args:
        amount: Amount to convert (Decimal for precision)
        from_currency: Source currency code (e.g., "USD")
        to_currency: Target currency code (e.g., "EUR")
        
    Returns:
        Tuple of (converted_amount, exchange_rate_used)
        - converted_amount: The amount in target currency
        - exchange_rate_used: The rate applied (from_currency -> to_currency)
        
    Example:
        # Converting $275 USD to EUR
        eur_amount, rate = await convert(Decimal("275.00"), "USD", "EUR")
        # Returns: (Decimal("254.12"), Decimal("0.924073"))
        # Meaning: 275 USD * 0.924073 = 254.12 EUR
    """
    if from_currency == to_currency:
        return amount, Decimal("1.0")
    
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))
    
    # Get exchange rate
    rate = await get_exchange_rate(from_currency, to_currency)
    exchange_rate = Decimal(str(rate))
    
    # Convert with proper rounding
    converted = (amount * exchange_rate).quantize(
        Decimal("0.01"), 
        rounding=ROUND_HALF_UP
    )
    
    return converted, exchange_rate


async def get_exchange_rate(from_currency: str, to_currency: str) -> Decimal:
    """
    Get the exchange rate from one currency to another.
    
    Args:
        from_currency: Source currency code
        to_currency: Target currency code
        
    Returns:
        Decimal exchange rate (multiply by this to convert)
    """
    if from_currency == to_currency:
        return Decimal("1.0")
    
    rates = await fetch_exchange_rates("USD")
    from_rate = rates.get(from_currency, 1.0)
    to_rate = rates.get(to_currency, 1.0)
    
    # Rate from X to Y = Y_rate / X_rate
    if from_rate == 0:
        return Decimal("1.0")
    
    rate = Decimal(str(to_rate / from_rate))
    return rate.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

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
