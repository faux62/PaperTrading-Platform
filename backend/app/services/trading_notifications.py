"""
PaperTrading Platform - Trading Notifications Service

Automated notifications for key trading moments:
- Morning Briefing (07:00 CET)
- Market Open Alerts (EU 09:00, US 15:30 CET)
- Daily Summary (22:30 CET)
- Weekly Report (Friday 18:00 CET)
- ML Signal Alerts
- Stop-Loss/Take-Profit Alerts
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.services.email_service import email_service, EmailConfig
from app.db.models.user import User
from app.db.models.portfolio import Portfolio
from app.db.models.position import Position
from app.db.models.market_universe import MarketUniverse


class TradingNotificationService:
    """
    Service for sending automated trading notifications.
    """
    
    def __init__(self):
        self.enabled = EmailConfig.is_configured()
        if not self.enabled:
            logger.warning("Trading notifications disabled: Email not configured")
    
    async def send_morning_briefing(
        self,
        db: AsyncSession,
        user_id: int
    ) -> bool:
        """
        Send morning briefing email with:
        - Overnight P&L changes
        - Top ML signals for the day
        - Market calendar
        """
        if not self.enabled:
            return False
        
        try:
            # Get user
            user = await db.get(User, user_id)
            if not user or not user.email:
                return False
            
            # Check notification preferences
            if hasattr(user, 'notifications_email') and not user.notifications_email:
                return False
            
            # Get portfolios with positions
            portfolios_query = select(Portfolio).where(Portfolio.user_id == user_id)
            result = await db.execute(portfolios_query)
            portfolios = result.scalars().all()
            
            if not portfolios:
                return False
            
            # Calculate overnight changes
            portfolio_data = []
            total_value = 0
            total_overnight_change = 0
            
            for portfolio in portfolios:
                positions_query = select(Position).where(
                    and_(
                        Position.portfolio_id == portfolio.id,
                        Position.quantity > 0
                    )
                )
                positions_result = await db.execute(positions_query)
                positions = positions_result.scalars().all()
                
                portfolio_value = float(portfolio.cash_balance or 0)
                for pos in positions:
                    if pos.current_price:
                        portfolio_value += float(pos.quantity) * float(pos.current_price)
                
                portfolio_data.append({
                    'name': portfolio.name,
                    'value': portfolio_value,
                    'positions_count': len(positions)
                })
                total_value += portfolio_value
            
            # Get top ML signals (placeholder - would come from ML service)
            top_signals = await self._get_top_signals(db, limit=5)
            
            # Send email
            await email_service.send_morning_briefing(
                to_email=user.email,
                date=datetime.now().strftime("%A, %d %B %Y"),
                total_portfolio_value=total_value,
                portfolios=portfolio_data,
                top_signals=top_signals,
                market_events=self._get_market_events()
            )
            
            logger.info(f"Morning briefing sent to {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send morning briefing: {e}")
            return False
    
    async def send_market_open_alert(
        self,
        db: AsyncSession,
        user_id: int,
        market: str  # 'EU' or 'US'
    ) -> bool:
        """
        Send alert when markets are about to open.
        """
        if not self.enabled:
            return False
        
        try:
            user = await db.get(User, user_id)
            if not user or not user.email:
                return False
            
            market_info = {
                'EU': {
                    'name': 'European Markets',
                    'exchanges': ['Frankfurt (XETRA)', 'Paris (Euronext)', 'Milan (Borsa Italiana)', 'London (LSE)'],
                    'open_time': '09:00 CET',
                    'tip': 'Avoid trading in the first 30 minutes - high volatility!'
                },
                'US': {
                    'name': 'US Markets',
                    'exchanges': ['NYSE', 'NASDAQ'],
                    'open_time': '15:30 CET (09:30 ET)',
                    'tip': 'Wait 15-30 minutes after open for prices to stabilize.'
                }
            }
            
            info = market_info.get(market, market_info['US'])
            
            await email_service.send_market_open_alert(
                to_email=user.email,
                market_name=info['name'],
                exchanges=info['exchanges'],
                open_time=info['open_time'],
                tip=info['tip']
            )
            
            logger.info(f"Market open alert ({market}) sent to {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send market open alert: {e}")
            return False
    
    async def send_stop_loss_alert(
        self,
        to_email: str,
        symbol: str,
        entry_price: float,
        stop_price: float,
        current_price: float,
        quantity: int,
        loss_amount: float,
        portfolio_name: str
    ) -> bool:
        """
        Send alert when stop-loss is triggered.
        """
        if not self.enabled:
            return False
        
        try:
            await email_service.send_stop_loss_alert(
                to_email=to_email,
                symbol=symbol,
                entry_price=entry_price,
                stop_price=stop_price,
                current_price=current_price,
                quantity=quantity,
                loss_amount=loss_amount,
                portfolio_name=portfolio_name
            )
            
            logger.info(f"Stop-loss alert for {symbol} sent to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send stop-loss alert: {e}")
            return False
    
    async def send_take_profit_alert(
        self,
        to_email: str,
        symbol: str,
        entry_price: float,
        target_price: float,
        current_price: float,
        quantity: int,
        profit_amount: float,
        portfolio_name: str
    ) -> bool:
        """
        Send alert when take-profit target is reached.
        """
        if not self.enabled:
            return False
        
        try:
            await email_service.send_take_profit_alert(
                to_email=to_email,
                symbol=symbol,
                entry_price=entry_price,
                target_price=target_price,
                current_price=current_price,
                quantity=quantity,
                profit_amount=profit_amount,
                portfolio_name=portfolio_name
            )
            
            logger.info(f"Take-profit alert for {symbol} sent to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send take-profit alert: {e}")
            return False
    
    async def send_ml_signal_alert(
        self,
        to_email: str,
        signals: List[Dict[str, Any]]
    ) -> bool:
        """
        Send alert for high-confidence ML signals.
        """
        if not self.enabled or not signals:
            return False
        
        try:
            await email_service.send_ml_signal_alert(
                to_email=to_email,
                signals=signals,
                generated_at=datetime.now().strftime("%H:%M %d/%m/%Y")
            )
            
            logger.info(f"ML signal alert sent to {to_email} with {len(signals)} signals")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send ML signal alert: {e}")
            return False
    
    async def _get_top_signals(self, db: AsyncSession, limit: int = 5) -> List[Dict]:
        """Get top ML signals for the day."""
        # This would integrate with the ML service
        # For now, return placeholder
        return [
            {'symbol': 'AAPL', 'signal': 'BUY', 'confidence': 72},
            {'symbol': 'MSFT', 'signal': 'BUY', 'confidence': 68},
            {'symbol': 'SAP.DE', 'signal': 'BUY', 'confidence': 65},
        ]
    
    def _get_market_events(self) -> List[Dict]:
        """Get today's market events."""
        # This would integrate with an economic calendar
        return [
            {'time': '14:30', 'event': 'US Jobless Claims', 'importance': 'Medium'},
            {'time': '16:00', 'event': 'US Consumer Confidence', 'importance': 'High'},
        ]


# Singleton instance
trading_notifications = TradingNotificationService()


# ==================== Scheduled Job Functions ====================

async def morning_briefing_job(db: AsyncSession):
    """
    Job to send morning briefing to all users with notifications enabled.
    Runs at 07:00 CET.
    """
    logger.info("Running morning briefing job...")
    
    # Get all users with email notifications enabled
    query = select(User).where(
        and_(
            User.is_active == True,
            User.notifications_email == True
        )
    )
    result = await db.execute(query)
    users = result.scalars().all()
    
    sent_count = 0
    for user in users:
        success = await trading_notifications.send_morning_briefing(db, user.id)
        if success:
            sent_count += 1
    
    logger.info(f"Morning briefing sent to {sent_count}/{len(users)} users")


async def eu_market_open_job(db: AsyncSession):
    """
    Job to send EU market open alert.
    Runs at 08:45 CET (15 minutes before EU open).
    """
    logger.info("Running EU market open alert job...")
    
    query = select(User).where(
        and_(
            User.is_active == True,
            User.notifications_email == True
        )
    )
    result = await db.execute(query)
    users = result.scalars().all()
    
    for user in users:
        await trading_notifications.send_market_open_alert(db, user.id, 'EU')


async def us_market_open_job(db: AsyncSession):
    """
    Job to send US market open alert.
    Runs at 15:15 CET (15 minutes before US open).
    """
    logger.info("Running US market open alert job...")
    
    query = select(User).where(
        and_(
            User.is_active == True,
            User.notifications_email == True
        )
    )
    result = await db.execute(query)
    users = result.scalars().all()
    
    for user in users:
        await trading_notifications.send_market_open_alert(db, user.id, 'US')
