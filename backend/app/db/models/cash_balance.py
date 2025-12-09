"""
PaperTrading Platform - Cash Balance Model
IBKR-style multi-currency cash management
"""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.database import Base


class CashBalance(Base):
    """
    Multi-currency cash balance for a portfolio.
    Each portfolio can hold cash in multiple currencies (IBKR-style).
    """
    
    __tablename__ = "cash_balances"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Currency and amount
    currency = Column(String(3), nullable=False)  # USD, EUR, GBP, etc.
    balance = Column(Numeric(15, 2), default=Decimal("0.00"))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="cash_balances")
    
    # Ensure one balance per currency per portfolio
    __table_args__ = (
        UniqueConstraint('portfolio_id', 'currency', name='uq_portfolio_currency'),
    )
    
    def __repr__(self):
        return f"<CashBalance {self.currency}: {self.balance}>"


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
