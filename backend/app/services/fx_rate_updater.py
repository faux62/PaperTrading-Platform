"""
PaperTrading Platform - FX Rate Updater Service

Fetches exchange rates from Frankfurter API (ECB data source)
and updates the local exchange_rates table.

Supported currencies: EUR, USD, GBP, CHF, HKD, JPY (30 pairs)

API Documentation: https://www.frankfurter.app/docs/

OPTIMIZATION (Dec 2024):
- Single HTTP request with EUR base, calculate all cross rates mathematically
- Reduced from 6 HTTP requests to 1 HTTP request per update
- ECB publishes rates once daily at 16:00 CET, so 4h refresh is sufficient

Example API call:
GET https://api.frankfurter.app/latest?from=EUR&to=USD,GBP,CHF,HKD,JPY
Response: {"amount":1.0,"base":"EUR","date":"2025-12-18","rates":{"CHF":0.93,"GBP":0.83,"USD":1.04,"HKD":8.12,"JPY":163.5}}
"""
import httpx
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional
from loguru import logger

from app.db.database import get_db
from app.db.repositories.exchange_rate import ExchangeRateRepository


# Supported currencies for the platform
SUPPORTED_CURRENCIES = ["EUR", "USD", "GBP", "CHF", "HKD", "JPY"]

# Frankfurter API base URL (free, no API key required)
FRANKFURTER_API_BASE = "https://api.frankfurter.app"


class FxRateUpdaterService:
    """
    Service for fetching and updating exchange rates.
    
    Uses Frankfurter API which provides ECB (European Central Bank) rates.
    Rates are typically updated once per business day around 16:00 CET.
    
    OPTIMIZED: Single HTTP request, calculates all cross rates mathematically.
    
    Usage:
        service = FxRateUpdaterService()
        await service.update_all_rates()
    """
    
    def __init__(self, timeout: float = 30.0):
        """
        Initialize the FX rate updater.
        
        Args:
            timeout: HTTP request timeout in seconds
        """
        self.timeout = timeout
        self.api_base = FRANKFURTER_API_BASE
        self.currencies = SUPPORTED_CURRENCIES
    
    async def fetch_eur_rates_from_api(self) -> Optional[Dict[str, Decimal]]:
        """
        Fetch exchange rates from Frankfurter API using EUR as base.
        
        OPTIMIZED: Single HTTP request for all currencies.
        
        Returns:
            Dict mapping currencies to EUR rates, or None on error
            Example: {'USD': Decimal('1.05'), 'GBP': Decimal('0.86'), ...}
            Always includes EUR: Decimal('1.0')
        """
        # Get all non-EUR currencies
        quote_currencies = [c for c in self.currencies if c != "EUR"]
        
        if not quote_currencies:
            return {"EUR": Decimal("1.0")}
        
        url = f"{self.api_base}/latest"
        params = {
            "from": "EUR",
            "to": ",".join(quote_currencies)
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                # Convert to Decimal for precision
                rates = {"EUR": Decimal("1.0")}  # EUR/EUR = 1
                for currency, rate in data.get("rates", {}).items():
                    rates[currency] = Decimal(str(rate))
                
                logger.debug(f"Fetched EUR-based rates: {rates}")
                return rates
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching EUR rates: {e.response.status_code}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error fetching EUR rates: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching EUR rates: {e}")
            return None
    
    def calculate_cross_rate(
        self,
        eur_rates: Dict[str, Decimal],
        base: str,
        quote: str
    ) -> Optional[Decimal]:
        """
        Calculate cross rate from EUR-based rates.
        
        Formula: BASE/QUOTE = EUR/QUOTE ÷ EUR/BASE
        
        Example: To get USD/GBP when we have EUR/USD=1.05 and EUR/GBP=0.83:
        USD/GBP = EUR/GBP ÷ EUR/USD = 0.83 ÷ 1.05 = 0.79
        
        Args:
            eur_rates: Dict of EUR/X rates
            base: Base currency
            quote: Quote currency
            
        Returns:
            Cross rate or None if currencies not found
        """
        if base == quote:
            return Decimal("1.0")
        
        eur_base = eur_rates.get(base)
        eur_quote = eur_rates.get(quote)
        
        if eur_base is None or eur_quote is None:
            return None
        
        if eur_base == 0:
            return None
        
        # Cross rate = EUR/quote ÷ EUR/base
        cross_rate = eur_quote / eur_base
        
        # Round to 8 decimal places for precision
        return cross_rate.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)
    
    async def fetch_all_rates(self) -> List[Dict]:
        """
        Fetch all exchange rates for supported currency pairs.
        
        OPTIMIZED: Single HTTP request + mathematical cross rate calculation.
        
        Returns:
            List of dicts with keys: base_currency, quote_currency, rate
            Generates all 36 pairs (6×6 including identity pairs)
        """
        all_rates = []
        
        # Fetch EUR-based rates (SINGLE HTTP REQUEST)
        eur_rates = await self.fetch_eur_rates_from_api()
        
        if not eur_rates:
            logger.error("Failed to fetch EUR rates, cannot calculate cross rates")
            return all_rates
        
        # Calculate all cross rates mathematically
        for base in self.currencies:
            for quote in self.currencies:
                rate = self.calculate_cross_rate(eur_rates, base, quote)
                
                if rate is not None:
                    all_rates.append({
                        "base_currency": base,
                        "quote_currency": quote,
                        "rate": rate,
                    })
        
        logger.info(
            f"Calculated {len(all_rates)} exchange rates from 1 HTTP request "
            f"(EUR base + {len(self.currencies)-1} cross rates)"
        )
        return all_rates
    
    async def update_all_rates(self) -> int:
        """
        Fetch rates from API and update the database.
        
        Returns:
            Number of rates updated
        """
        logger.info("Starting FX rate update from Frankfurter API")
        
        # Fetch rates from API
        rates = await self.fetch_all_rates()
        
        if not rates:
            logger.warning("No rates fetched from API, skipping update")
            return 0
        
        # Update database
        async for db in get_db():
            repo = ExchangeRateRepository(db)
            count = await repo.bulk_upsert_rates(rates, source="frankfurter")
            
            logger.info(f"Updated {count} exchange rates in database")
            return count
        
        return 0
    
    async def get_rate(self, base_currency: str, quote_currency: str) -> Optional[Decimal]:
        """
        Get a single exchange rate from the database.
        Falls back to API if not found (and updates DB).
        
        Args:
            base_currency: Base currency code
            quote_currency: Quote currency code
        
        Returns:
            Exchange rate or None
        """
        if base_currency == quote_currency:
            return Decimal("1.0")
        
        async for db in get_db():
            repo = ExchangeRateRepository(db)
            rate = await repo.get_rate_value(base_currency, quote_currency)
            
            if rate != Decimal("1.0"):  # Found in DB
                return rate
        
        # Not in DB, fetch from API
        logger.warning(f"Rate {base_currency}/{quote_currency} not in DB, fetching from API")
        rates = await self.fetch_rates_from_api(base_currency)
        
        if rates and quote_currency in rates:
            # Save to DB for next time
            async for db in get_db():
                repo = ExchangeRateRepository(db)
                await repo.upsert_rate(
                    base_currency=base_currency,
                    quote_currency=quote_currency,
                    rate=rates[quote_currency],
                    source="frankfurter",
                )
            return rates[quote_currency]
        
        return None


# Singleton instance
fx_rate_updater = FxRateUpdaterService()


async def update_exchange_rates() -> int:
    """
    Convenience function for scheduled job.
    
    Returns:
        Number of rates updated
    """
    return await fx_rate_updater.update_all_rates()
