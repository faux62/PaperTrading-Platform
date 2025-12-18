"""
PaperTrading Platform - FX Transaction Model

NOTE: CashBalance class has been REMOVED (Dec 2025).
The cash_balances table is deprecated - use portfolio.cash_balance instead.
"""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.db.database import Base


# CashBalance class REMOVED - table deprecated
# Use portfolio.cash_balance (Single Currency Model) instead


class FxTransaction(Base):
    """
    Foreign exchange transaction record.
    Tracks currency conversions within a portfolio.
    """
    
    __tablename__ = "fx_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Transaction details
    from_currency = Column(String(3), nullable=False)
    to_currency = Column(String(3), nullable=False)
    from_amount = Column(Numeric(15, 2), nullable=False)
    to_amount = Column(Numeric(15, 2), nullable=False)
    exchange_rate = Column(Numeric(15, 6), nullable=False)
    
    # Timestamps
    executed_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="fx_transactions")
    
    def __repr__(self):
        return f"<FxTransaction {self.from_currency}->{self.to_currency} @ {self.exchange_rate}>"
