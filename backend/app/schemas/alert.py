"""
PaperTrading Platform - Alert Schemas
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.db.models.alert import AlertType, AlertStatus


class AlertBase(BaseModel):
    """Base alert schema."""
    symbol: str = Field(..., min_length=1, max_length=20, description="Stock ticker symbol")
    alert_type: AlertType = Field(..., description="Type of price alert")
    target_value: float = Field(..., gt=0, description="Target price or percentage")
    note: Optional[str] = Field(None, max_length=500, description="Optional note")
    is_recurring: bool = Field(default=False, description="Re-activate after trigger")
    expires_at: Optional[datetime] = Field(None, description="Alert expiration date")


class AlertCreate(AlertBase):
    """Schema for creating an alert."""
    pass


class AlertUpdate(BaseModel):
    """Schema for updating an alert."""
    target_value: Optional[float] = Field(None, gt=0)
    note: Optional[str] = Field(None, max_length=500)
    is_recurring: Optional[bool] = None
    expires_at: Optional[datetime] = None


class AlertResponse(AlertBase):
    """Response schema for alert."""
    id: int
    user_id: int
    status: AlertStatus
    triggered_at: Optional[datetime] = None
    triggered_price: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class AlertSummary(BaseModel):
    """Summary of user's alerts."""
    total: int
    active: int
    triggered: int
    disabled: int
    expired: int


class AlertTriggeredNotification(BaseModel):
    """Notification when alert is triggered."""
    alert_id: int
    symbol: str
    alert_type: AlertType
    target_value: float
    triggered_price: float
    triggered_at: datetime
    note: Optional[str] = None
