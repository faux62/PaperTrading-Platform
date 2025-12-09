"""
PaperTrading Platform - Portfolio Model
"""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Enum as SQLEnum, Boolean, CheckConstraint
from sqlalchemy.orm import relationship
import enum

from app.db.database import Base


class RiskProfile(str, enum.Enum):
    """Portfolio risk profile types."""
    AGGRESSIVE = "aggressive"
    BALANCED = "balanced"
    PRUDENT = "prudent"


class Portfolio(Base):
    """Portfolio model."""
    
    __tablename__ = "portfolios"
    __table_args__ = (
        CheckConstraint('initial_capital >= 100', name='ck_portfolios_initial_capital_min'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Portfolio info
    name = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)
    risk_profile = Column(SQLEnum(RiskProfile), default=RiskProfile.BALANCED)
    
    # Strategy configuration
    strategy_period_weeks = Column(Integer, default=12, nullable=False)  # Weeks to calibrate strategies
    
    # Financials (min 100, step 100)
    initial_capital = Column(Numeric(15, 2), default=Decimal("10000.00"))
    cash_balance = Column(Numeric(15, 2), default=Decimal("10000.00"))
    currency = Column(String(3), default="USD")
    
    # Status (true = active and processed, false = inactive/paused)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="portfolios")
    positions = relationship("Position", back_populates="portfolio", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="portfolio", cascade="all, delete-orphan")
    cash_balances = relationship("CashBalance", back_populates="portfolio", cascade="all, delete-orphan")
    fx_transactions = relationship("FxTransaction", back_populates="portfolio", cascade="all, delete-orphan")
    bot_signals = relationship("BotSignal", back_populates="portfolio")
    
    def __repr__(self):
        return f"<Portfolio {self.name} ({self.risk_profile.value})>"
