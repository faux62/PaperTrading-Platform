"""
PaperTrading Platform - Trade Model
"""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from app.db.database import Base


class TradeType(str, enum.Enum):
    """Trade type."""
    BUY = "buy"
    SELL = "sell"


class OrderType(str, enum.Enum):
    """Order type."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class TradeStatus(str, enum.Enum):
    """Trade status."""
    PENDING = "pending"
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class Trade(Base):
    """Trade transaction model."""
    
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    
    # Symbol info
    symbol = Column(String(20), nullable=False, index=True)
    exchange = Column(String(20), nullable=True)
    
    # Trade details
    trade_type = Column(SQLEnum(TradeType), nullable=False)
    order_type = Column(SQLEnum(OrderType), default=OrderType.MARKET)
    status = Column(SQLEnum(TradeStatus), default=TradeStatus.PENDING)
    
    # Quantities and prices
    quantity = Column(Numeric(15, 4), nullable=False)
    price = Column(Numeric(15, 4), nullable=True)  # Limit/stop price
    executed_price = Column(Numeric(15, 4), nullable=True)
    executed_quantity = Column(Numeric(15, 4), nullable=True)
    
    # Financials
    total_value = Column(Numeric(15, 2), nullable=True)
    commission = Column(Numeric(10, 2), default=Decimal("0"))
    
    # P&L (for sells)
    realized_pnl = Column(Numeric(15, 2), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    executed_at = Column(DateTime, nullable=True)
    
    # Notes
    notes = Column(String(500), nullable=True)
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="trades")
    
    def __repr__(self):
        return f"<Trade {self.trade_type.value} {self.symbol} qty={self.quantity}>"
