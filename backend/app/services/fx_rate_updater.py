"""
PaperTrading Platform - FX Rate Updater Service

Fetches exchange rates from Frankfurter API (ECB data source)
and updates the local exchange_rates table.

Supported currencies: EUR, USD, GBP, CHF (12 pairs)

API Documentation: https://www.frankfurter.app/docs/

Example API call:
GET https://api.frankfurter.app/latest?from=EUR&to=USD,GBP,CHF
Response: {"amount":1.0,"base":"EUR","date":"2025-12-18","rates":{"CHF":0.93,"GBP":0.83,"USD":1.04}}
"""
import httpx
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from loguru import logger

from app.db.database import get_db
from app.db.repositories.exchange_rate import ExchangeRateRepository


# Supported currencies for the platform
SUPPORTED_CURRENCIES = ["EUR", "USD", "GBP", "CHF"]

# Frankfurter API base URL (free, no API key required)
FRANKFURTER_API_BASE = "https://api.frankfurter.app"


class FxRateUpdaterService:
    """
    Service for fetching and updating exchange rates.
    
    Uses Frankfurter API which provides ECB (European Central Bank) rates.
    Rates are typically updated once per business day around 16:00 CET.
    
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
    
    async def fetch_rates_from_api(self, base_currency: str) -> Optional[Dict[str, Decimal]]:
        """
        Fetch exchange rates from Frankfurter API for a base currency.
        
        Args:
            base_currency: The base currency code (e.g., 'EUR')
        
        Returns:
            Dict mapping quote currencies to rates, or None on error
            Example: {'USD': Decimal('1.05'), 'GBP': Decimal('0.86'), 'CHF': Decimal('0.94')}
        """
        # Get other currencies (exclude base)
        quote_currencies = [c for c in self.currencies if c != base_currency]
        
        if not quote_currencies:
            return {}
        
        url = f"{self.api_base}/latest"
        params = {
            "from": base_currency,
            "to": ",".join(quote_currencies)
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                # Convert to Decimal for precision
                rates = {}
                for currency, rate in data.get("rates", {}).items():
                    rates[currency] = Decimal(str(rate))
                
                logger.debug(f"Fetched rates for {base_currency}: {rates}")
                return rates
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching rates for {base_currency}: {e.response.status_code}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error fetching rates for {base_currency}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching rates for {base_currency}: {e}")
            return None
    
    async def fetch_all_rates(self) -> List[Dict]:
        """
        Fetch all exchange rates for supported currency pairs.
        
        Returns:
            List of dicts with keys: base_currency, quote_currency, rate
        """
        all_rates = []
        
        for base_currency in self.currencies:
            rates = await self.fetch_rates_from_api(base_currency)
            
            if rates:
                for quote_currency, rate in rates.items():
                    all_rates.append({
                        "base_currency": base_currency,
                        "quote_currency": quote_currency,
                        "rate": rate,
                    })
        
        logger.info(f"Fetched {len(all_rates)} exchange rates from Frankfurter API")
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
