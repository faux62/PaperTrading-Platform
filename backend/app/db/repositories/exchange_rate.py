"""
Exchange Rate Repository

Database operations for exchange rate management.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from loguru import logger

from app.db.models.exchange_rate import ExchangeRate


class ExchangeRateRepository:
    """
    Repository for ExchangeRate database operations.
    
    Provides low-level CRUD operations for exchange rates.
    For business logic, use FxService instead.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_rate(
        self,
        base_currency: str,
        quote_currency: str,
    ) -> Optional[ExchangeRate]:
        """
        Get the exchange rate for a currency pair.
        
        Args:
            base_currency: Base currency code (e.g., 'EUR')
            quote_currency: Quote currency code (e.g., 'USD')
        
        Returns:
            ExchangeRate or None if not found
        """
        result = await self.db.execute(
            select(ExchangeRate).where(
                ExchangeRate.base_currency == base_currency.upper(),
                ExchangeRate.quote_currency == quote_currency.upper(),
            )
        )
        return result.scalar_one_or_none()
    
    async def get_rate_value(
        self,
        base_currency: str,
        quote_currency: str,
    ) -> Decimal:
        """
        Get the exchange rate value for a currency pair.
        Returns 1.0 if same currency or rate not found.
        
        Args:
            base_currency: Base currency code (e.g., 'EUR')
            quote_currency: Quote currency code (e.g., 'USD')
        
        Returns:
            Decimal rate value (1 base = rate quote)
        """
        if base_currency.upper() == quote_currency.upper():
            return Decimal("1.0")
        
        rate = await self.get_rate(base_currency, quote_currency)
        if rate:
            return rate.rate
        
        logger.warning(f"Exchange rate not found for {base_currency}/{quote_currency}, using 1.0")
        return Decimal("1.0")
    
    async def get_all_rates(self) -> list[ExchangeRate]:
        """Get all exchange rates."""
        result = await self.db.execute(
            select(ExchangeRate).order_by(
                ExchangeRate.base_currency,
                ExchangeRate.quote_currency,
            )
        )
        return list(result.scalars().all())
    
    async def upsert_rate(
        self,
        base_currency: str,
        quote_currency: str,
        rate: Decimal,
        source: str = "frankfurter",
        fetched_at: Optional[datetime] = None,
    ) -> ExchangeRate:
        """
        Insert or update an exchange rate.
        
        Args:
            base_currency: Base currency code
            quote_currency: Quote currency code
            rate: The exchange rate value
            source: Source identifier
            fetched_at: When the rate was fetched (defaults to now)
        
        Returns:
            The created or updated ExchangeRate
        """
        if fetched_at is None:
            fetched_at = datetime.utcnow()
        
        base = base_currency.upper()
        quote = quote_currency.upper()
        
        existing = await self.get_rate(base, quote)
        
        if existing:
            # Update existing rate
            existing.rate = rate
            existing.source = source
            existing.fetched_at = fetched_at
            existing.updated_at = datetime.utcnow()
            
            await self.db.commit()
            await self.db.refresh(existing)
            
            logger.debug(f"Updated rate: {base}/{quote} = {rate}")
            return existing
        else:
            # Create new rate
            new_rate = ExchangeRate(
                base_currency=base,
                quote_currency=quote,
                rate=rate,
                source=source,
                fetched_at=fetched_at,
            )
            
            self.db.add(new_rate)
            await self.db.commit()
            await self.db.refresh(new_rate)
            
            logger.info(f"Created rate: {base}/{quote} = {rate}")
            return new_rate
    
    async def bulk_upsert_rates(
        self,
        rates: list[dict],
        source: str = "frankfurter",
    ) -> int:
        """
        Bulk insert or update exchange rates.
        
        Args:
            rates: List of dicts with keys: base_currency, quote_currency, rate
            source: Source identifier
        
        Returns:
            Number of rates processed
        
        Example:
            rates = [
                {"base_currency": "EUR", "quote_currency": "USD", "rate": 1.05},
                {"base_currency": "EUR", "quote_currency": "GBP", "rate": 0.86},
            ]
        """
        fetched_at = datetime.utcnow()
        count = 0
        
        for rate_data in rates:
            await self.upsert_rate(
                base_currency=rate_data["base_currency"],
                quote_currency=rate_data["quote_currency"],
                rate=Decimal(str(rate_data["rate"])),
                source=source,
                fetched_at=fetched_at,
            )
            count += 1
        
        logger.info(f"Bulk upserted {count} exchange rates from {source}")
        return count
    
    async def convert_amount(
        self,
        amount: Decimal,
        from_currency: str,
        to_currency: str,
    ) -> Decimal:
        """
        Convert an amount from one currency to another.
        
        Args:
            amount: The amount to convert
            from_currency: Source currency code
            to_currency: Target currency code
        
        Returns:
            Converted amount
        """
        rate = await self.get_rate_value(from_currency, to_currency)
        return amount * rate
