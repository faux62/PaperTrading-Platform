"""
PaperTrading Platform - Exchange Rate Model

This model stores cached foreign exchange rates, updated hourly
by a scheduled job fetching from Frankfurter API (ECB data source).

SUPPORTED CURRENCIES: EUR, USD, GBP, CHF (12 pairs total)

Example data:
- EUR/USD: 1.05 (1 EUR = 1.05 USD)
- USD/EUR: 0.95 (1 USD = 0.95 EUR)
"""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Numeric, DateTime, UniqueConstraint, Index

from app.db.database import Base


class ExchangeRate(Base):
    """Foreign exchange rate model.
    
    Stores currency pair rates for portfolio value calculations.
    Rates are updated hourly by the fx_rate_updater job.
    
    Attributes:
        base_currency: The base currency code (e.g., 'EUR')
        quote_currency: The quote currency code (e.g., 'USD')
        rate: The exchange rate (1 base = rate quote)
        source: Data source identifier ('frankfurter', 'seed', etc.)
        fetched_at: Timestamp when rate was fetched from source
    """
    
    __tablename__ = "exchange_rates"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Currency pair
    base_currency = Column(String(3), nullable=False)
    quote_currency = Column(String(3), nullable=False)
    
    # Rate value (1 base = rate quote)
    # Using high precision for accurate financial calculations
    rate = Column(Numeric(20, 10), nullable=False, default=Decimal("1.0"))
    
    # Source metadata
    source = Column(String(50), nullable=False, default="frankfurter")
    fetched_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('base_currency', 'quote_currency', name='uq_exchange_rates_pair'),
        Index('ix_exchange_rates_pair', 'base_currency', 'quote_currency'),
    )
    
    def __repr__(self):
        return f"<ExchangeRate {self.base_currency}/{self.quote_currency}={self.rate}>"
    
    @property
    def pair(self) -> str:
        """Return the currency pair as a string (e.g., 'EUR/USD')."""
        return f"{self.base_currency}/{self.quote_currency}"
    
    @property
    def inverse_rate(self) -> Decimal:
        """Return the inverse rate (e.g., if EUR/USD=1.05, USD/EUR=0.952...)."""
        if self.rate and self.rate != 0:
            return Decimal("1") / self.rate
        return Decimal("1")
