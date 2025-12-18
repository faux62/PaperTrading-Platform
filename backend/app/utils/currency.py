"""
Currency Conversion Service

Provides currency conversion using cached exchange rates from database.
Rates are updated hourly by the fx_rate_update scheduled job.

SINGLE CURRENCY MODEL:
This module provides the unified convert() function that should be used
everywhere in the platform for currency conversions. All portfolios use
a single base currency, and conversions happen on-demand when trading
assets in different currencies.

DATA SOURCE: exchange_rates table (populated from Frankfurter/ECB API)
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Tuple
from loguru import logger

# Supported currencies (must match exchange_rates table)
SUPPORTED_CURRENCIES = ["USD", "EUR", "GBP", "CHF"]

# Fallback rates (approximate, used if DB query fails)
# These should NEVER be used in production - they're emergency fallback only
FALLBACK_RATES = {
    ("EUR", "USD"): Decimal("1.05"),
    ("EUR", "GBP"): Decimal("0.86"),
    ("EUR", "CHF"): Decimal("0.94"),
    ("USD", "EUR"): Decimal("0.95"),
    ("USD", "GBP"): Decimal("0.82"),
    ("USD", "CHF"): Decimal("0.89"),
    ("GBP", "EUR"): Decimal("1.16"),
    ("GBP", "USD"): Decimal("1.22"),
    ("GBP", "CHF"): Decimal("1.09"),
    ("CHF", "EUR"): Decimal("1.06"),
    ("CHF", "USD"): Decimal("1.12"),
    ("CHF", "GBP"): Decimal("0.92"),
}


async def get_exchange_rate_from_db(
    from_currency: str,
    to_currency: str,
) -> Optional[Decimal]:
    """
    Get exchange rate from database.
    
    Args:
        from_currency: Source currency code
        to_currency: Target currency code
        
    Returns:
        Decimal rate or None if not found
    """
    from app.db.database import get_db
    from app.db.repositories.exchange_rate import ExchangeRateRepository
    
    if from_currency == to_currency:
        return Decimal("1.0")
    
    try:
        async for db in get_db():
            repo = ExchangeRateRepository(db)
            rate_obj = await repo.get_rate(from_currency, to_currency)
            if rate_obj:
                return rate_obj.rate
            return None
    except Exception as e:
        logger.error(f"Error fetching rate from DB: {e}")
        return None


async def fetch_exchange_rates(base: str = "USD") -> dict[str, float]:
    """
    DEPRECATED: Fetch exchange rates - now uses database.
    
    This function is kept for backward compatibility but now returns
    rates from the database. Use get_exchange_rate() instead.
    """
    from app.db.database import get_db
    from app.db.repositories.exchange_rate import ExchangeRateRepository
    
    rates = {}
    
    try:
        async for db in get_db():
            repo = ExchangeRateRepository(db)
            all_rates = await repo.get_all_rates()
            
            # Build rates dict with base as key
            for rate_obj in all_rates:
                if rate_obj.base_currency == base:
                    rates[rate_obj.quote_currency] = float(rate_obj.rate)
            
            # Add base currency itself
            rates[base] = 1.0
            
            if rates:
                return rates
    except Exception as e:
        logger.error(f"Error fetching rates from DB: {e}")
    
    # Fallback to hardcoded rates
    logger.warning("Using fallback exchange rates - DB fetch failed")
    fallback = {base: 1.0}
    for (from_curr, to_curr), rate in FALLBACK_RATES.items():
        if from_curr == base:
            fallback[to_curr] = float(rate)
    return fallback


async def convert_currency(
    amount: float,
    from_currency: str,
    to_currency: str,
    rates: Optional[dict[str, float]] = None
) -> float:
    """
    Convert amount from one currency to another.
    
    DEPRECATED: Use convert() instead for Decimal precision.
    
    Args:
        amount: Amount to convert
        from_currency: Source currency code (e.g., "EUR")
        to_currency: Target currency code (e.g., "USD")
        rates: Optional pre-fetched rates (ignored, kept for compatibility)
        
    Returns:
        Converted amount
    """
    if from_currency == to_currency:
        return amount
    
    # Use database rate directly
    rate = await get_exchange_rate_from_db(from_currency, to_currency)
    if rate:
        return float(Decimal(str(amount)) * rate)
    
    # Fallback
    fallback_rate = FALLBACK_RATES.get((from_currency, to_currency), Decimal("1.0"))
    logger.warning(f"Using fallback rate for {from_currency}/{to_currency}: {fallback_rate}")
    return float(Decimal(str(amount)) * fallback_rate)


async def get_conversion_rate(from_currency: str, to_currency: str) -> float:
    """
    Get direct conversion rate between two currencies.
    
    DEPRECATED: Use get_exchange_rate() instead for Decimal precision.
    """
    if from_currency == to_currency:
        return 1.0
    
    rate = await get_exchange_rate_from_db(from_currency, to_currency)
    if rate:
        return float(rate)
    
    fallback_rate = FALLBACK_RATES.get((from_currency, to_currency), Decimal("1.0"))
    return float(fallback_rate)


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
    
    Rates are fetched from the exchange_rates database table, which is
    updated hourly by the fx_rate_update scheduled job.
    
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
        # Returns: (Decimal("261.25"), Decimal("0.95"))
        # Meaning: 275 USD * 0.95 = 261.25 EUR
    """
    if from_currency == to_currency:
        return amount, Decimal("1.0")
    
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))
    
    # Get exchange rate from database
    rate = await get_exchange_rate(from_currency, to_currency)
    
    # Convert with proper rounding
    converted = (amount * rate).quantize(
        Decimal("0.01"), 
        rounding=ROUND_HALF_UP
    )
    
    return converted, rate


async def get_exchange_rate(from_currency: str, to_currency: str) -> Decimal:
    """
    Get the exchange rate from one currency to another.
    
    Fetches from database (exchange_rates table).
    Falls back to hardcoded rates if DB unavailable.
    
    Args:
        from_currency: Source currency code
        to_currency: Target currency code
        
    Returns:
        Decimal exchange rate (multiply by this to convert)
    """
    if from_currency == to_currency:
        return Decimal("1.0")
    
    # Try database first
    rate = await get_exchange_rate_from_db(from_currency, to_currency)
    if rate:
        return rate.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    
    # Fallback to hardcoded rates
    fallback_rate = FALLBACK_RATES.get(
        (from_currency.upper(), to_currency.upper()), 
        Decimal("1.0")
    )
    logger.warning(
        f"Using fallback rate for {from_currency}/{to_currency}: {fallback_rate}"
    )
    return fallback_rate


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_currency_symbol(currency: str) -> str:
    """Get currency symbol for display."""
    symbols = {
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "CHF": "CHF",
    }
    return symbols.get(currency, currency)


def get_supported_currencies() -> list[dict]:
    """Get list of supported currencies with metadata."""
    return [
        {"code": "USD", "name": "US Dollar", "symbol": "$"},
        {"code": "EUR", "name": "Euro", "symbol": "€"},
        {"code": "GBP", "name": "British Pound", "symbol": "£"},
        {"code": "CHF", "name": "Swiss Franc", "symbol": "CHF"},
    ]
