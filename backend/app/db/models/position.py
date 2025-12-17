"""
PaperTrading Platform - Position Model

SINGLE CURRENCY MODEL:
- avg_cost: Average cost in the symbol's NATIVE currency (e.g., USD for AAPL)
- avg_cost_portfolio: Average cost converted to PORTFOLIO currency at entry
- entry_exchange_rate: The FX rate used at the time of purchase
"""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.db.database import Base


class Position(Base):
    """Stock position model."""
    
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    
    # Symbol info
    symbol = Column(String(20), nullable=False, index=True)
    exchange = Column(String(20), nullable=True)
    native_currency = Column(String(3), default="USD", nullable=False)  # Currency the symbol is quoted in
    
    # Position details - NATIVE CURRENCY values
    quantity = Column(Numeric(15, 4), default=Decimal("0"))
    avg_cost = Column(Numeric(15, 4), default=Decimal("0"))  # Average cost in NATIVE currency
    current_price = Column(Numeric(15, 4), default=Decimal("0"))  # Current price in NATIVE currency
    
    # Position details - PORTFOLIO CURRENCY values (for P&L calculations)
    avg_cost_portfolio = Column(Numeric(15, 4), default=Decimal("0"))  # Average cost in PORTFOLIO currency
    entry_exchange_rate = Column(Numeric(15, 6), default=Decimal("1.0"))  # FX rate at entry (native -> portfolio)
    
    # Calculated fields (updated on price change) - in PORTFOLIO currency
    market_value = Column(Numeric(15, 2), default=Decimal("0"))  # Current value in PORTFOLIO currency
    unrealized_pnl = Column(Numeric(15, 2), default=Decimal("0"))  # P&L in PORTFOLIO currency
    unrealized_pnl_percent = Column(Numeric(8, 4), default=Decimal("0"))
    
    # Timestamps
    opened_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="positions")
    
    def __repr__(self):
        return f"<Position {self.symbol} qty={self.quantity}>"
