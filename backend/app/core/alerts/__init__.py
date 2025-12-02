"""
PaperTrading Platform - Alert Service
Business logic for price alerts
"""
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_

from app.db.models.alert import Alert, AlertType, AlertStatus


class AlertService:
    """Service for alert management and triggering."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_alert(
        self,
        user_id: int,
        symbol: str,
        alert_type: AlertType,
        target_value: float,
        note: Optional[str] = None,
        is_recurring: bool = False,
        expires_at: Optional[datetime] = None
    ) -> Alert:
        """Create a new price alert."""
        alert = Alert(
            user_id=user_id,
            symbol=symbol.upper(),
            alert_type=alert_type,
            target_value=target_value,
            note=note,
            is_recurring=is_recurring,
            expires_at=expires_at,
            status=AlertStatus.ACTIVE
        )
        self.db.add(alert)
        await self.db.commit()
        await self.db.refresh(alert)
        return alert
    
    async def get_alert(self, alert_id: int, user_id: int) -> Optional[Alert]:
        """Get alert by ID for specific user."""
        stmt = select(Alert).where(
            Alert.id == alert_id,
            Alert.user_id == user_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_alerts(
        self,
        user_id: int,
        status: Optional[AlertStatus] = None,
        symbol: Optional[str] = None
    ) -> list[Alert]:
        """Get all alerts for user with optional filters."""
        conditions = [Alert.user_id == user_id]
        
        if status:
            conditions.append(Alert.status == status)
        if symbol:
            conditions.append(Alert.symbol == symbol.upper())
        
        stmt = select(Alert).where(and_(*conditions)).order_by(Alert.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def get_active_alerts_for_symbol(self, symbol: str) -> list[Alert]:
        """Get all active alerts for a symbol (for checking triggers)."""
        stmt = select(Alert).where(
            Alert.symbol == symbol.upper(),
            Alert.status == AlertStatus.ACTIVE
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def update_alert(
        self,
        alert_id: int,
        user_id: int,
        target_value: Optional[float] = None,
        note: Optional[str] = None,
        is_recurring: Optional[bool] = None,
        expires_at: Optional[datetime] = None
    ) -> Optional[Alert]:
        """Update alert settings."""
        alert = await self.get_alert(alert_id, user_id)
        if not alert:
            return None
        
        if target_value is not None:
            alert.target_value = target_value
        if note is not None:
            alert.note = note
        if is_recurring is not None:
            alert.is_recurring = is_recurring
        if expires_at is not None:
            alert.expires_at = expires_at
        
        alert.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(alert)
        return alert
    
    async def delete_alert(self, alert_id: int, user_id: int) -> bool:
        """Delete an alert."""
        alert = await self.get_alert(alert_id, user_id)
        if not alert:
            return False
        
        await self.db.delete(alert)
        await self.db.commit()
        return True
    
    async def toggle_alert(self, alert_id: int, user_id: int) -> Optional[Alert]:
        """Enable/disable an alert."""
        alert = await self.get_alert(alert_id, user_id)
        if not alert:
            return None
        
        if alert.status == AlertStatus.ACTIVE:
            alert.status = AlertStatus.DISABLED
        elif alert.status == AlertStatus.DISABLED:
            alert.status = AlertStatus.ACTIVE
        
        alert.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(alert)
        return alert
    
    async def trigger_alert(
        self,
        alert: Alert,
        triggered_price: float
    ) -> Alert:
        """Mark an alert as triggered."""
        alert.status = AlertStatus.TRIGGERED
        alert.triggered_at = datetime.utcnow()
        alert.triggered_price = triggered_price
        
        # If recurring, create a new alert
        if alert.is_recurring:
            await self.create_alert(
                user_id=alert.user_id,
                symbol=alert.symbol,
                alert_type=alert.alert_type,
                target_value=alert.target_value,
                note=alert.note,
                is_recurring=True,
                expires_at=alert.expires_at
            )
        
        await self.db.commit()
        await self.db.refresh(alert)
        return alert
    
    async def check_and_trigger_alerts(
        self,
        symbol: str,
        current_price: float,
        previous_price: Optional[float] = None
    ) -> list[Alert]:
        """Check all active alerts for a symbol and trigger matching ones."""
        triggered = []
        alerts = await self.get_active_alerts_for_symbol(symbol)
        
        for alert in alerts:
            # Check expiration
            if alert.expires_at and alert.expires_at < datetime.utcnow():
                alert.status = AlertStatus.EXPIRED
                await self.db.commit()
                continue
            
            # Check trigger condition
            if alert.check_trigger(current_price, previous_price):
                await self.trigger_alert(alert, current_price)
                triggered.append(alert)
        
        return triggered
    
    async def get_alerts_summary(self, user_id: int) -> dict:
        """Get summary of user's alerts."""
        all_alerts = await self.get_user_alerts(user_id)
        
        return {
            "total": len(all_alerts),
            "active": len([a for a in all_alerts if a.status == AlertStatus.ACTIVE]),
            "triggered": len([a for a in all_alerts if a.status == AlertStatus.TRIGGERED]),
            "disabled": len([a for a in all_alerts if a.status == AlertStatus.DISABLED]),
            "expired": len([a for a in all_alerts if a.status == AlertStatus.EXPIRED]),
        }
