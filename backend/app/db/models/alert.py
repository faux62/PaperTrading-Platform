"""
PaperTrading Platform - Alert Model
Price alerts for watchlist symbols
"""
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.db.database import Base


class AlertType(str, Enum):
    """Type of price alert."""
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    PERCENT_CHANGE_UP = "percent_change_up"
    PERCENT_CHANGE_DOWN = "percent_change_down"


class AlertStatus(str, Enum):
    """Status of an alert."""
    ACTIVE = "active"
    TRIGGERED = "triggered"
    EXPIRED = "expired"
    DISABLED = "disabled"


class Alert(Base):
    """Price alert model."""
    
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Alert configuration
    symbol = Column(String(20), nullable=False, index=True)
    alert_type = Column(SQLEnum(AlertType), nullable=False)
    target_value = Column(Float, nullable=False)  # Price or percentage
    
    # Status
    status = Column(SQLEnum(AlertStatus), default=AlertStatus.ACTIVE, nullable=False)
    is_recurring = Column(Boolean, default=False)  # Re-activate after trigger
    
    # Trigger info
    triggered_at = Column(DateTime, nullable=True)
    triggered_price = Column(Float, nullable=True)
    
    # Optional settings
    note = Column(String(500), nullable=True)
    expires_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="alerts")
    
    def __repr__(self):
        return f"<Alert {self.symbol} {self.alert_type.value} {self.target_value}>"
    
    def check_trigger(self, current_price: float, previous_price: float = None) -> bool:
        """Check if alert should be triggered based on current price."""
        if self.status != AlertStatus.ACTIVE:
            return False
        
        if self.alert_type == AlertType.PRICE_ABOVE:
            return current_price >= self.target_value
        
        elif self.alert_type == AlertType.PRICE_BELOW:
            return current_price <= self.target_value
        
        elif self.alert_type == AlertType.PERCENT_CHANGE_UP and previous_price:
            percent_change = ((current_price - previous_price) / previous_price) * 100
            return percent_change >= self.target_value
        
        elif self.alert_type == AlertType.PERCENT_CHANGE_DOWN and previous_price:
            percent_change = ((current_price - previous_price) / previous_price) * 100
            return percent_change <= -self.target_value
        
        return False
