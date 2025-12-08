"""
Trading Assistant Bot - Position Monitor

Real-time monitoring of open positions:
- P/L threshold alerts
- Trailing stop suggestions
- Risk warnings
- Target approach notifications
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from loguru import logger

from app.db.models import (
    Portfolio,
    Position,
    BotSignal,
    SignalType,
    SignalPriority,
    SignalStatus,
    SignalDirection,
)
from app.bot.signal_engine import SignalEngine


class PositionMonitor:
    """
    Real-time position monitoring engine.
    
    Monitors open positions for:
    - P/L thresholds (profit targets, loss limits)
    - Trailing stop opportunities
    - Risk concentration
    - Position sizing issues
    """
    
    # Configuration thresholds
    PROFIT_ALERT_THRESHOLDS = [2.0, 5.0, 10.0]  # Alert at these % gains
    LOSS_ALERT_THRESHOLDS = [-2.0, -5.0]         # Alert at these % losses
    TRAILING_STOP_TRIGGER = 3.0                   # Suggest trailing stop after 3% gain
    MAX_POSITION_PERCENT = 15.0                   # Max single position as % of portfolio
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.signal_engine = SignalEngine(db)
        # Track which alerts have been sent to avoid duplicates
        self._sent_alerts: Dict[str, datetime] = {}
    
    async def monitor_user_positions(self, user_id: int) -> int:
        """
        Monitor all positions for a user.
        
        Returns number of signals created.
        """
        # Get user's portfolios
        result = await self.db.execute(
            select(Portfolio).where(
                and_(
                    Portfolio.user_id == user_id,
                    Portfolio.is_active == "active"
                )
            )
        )
        portfolios = result.scalars().all()
        
        signals_created = 0
        
        for portfolio in portfolios:
            signals = await self._monitor_portfolio_positions(portfolio)
            signals_created += signals
        
        return signals_created
    
    async def _monitor_portfolio_positions(self, portfolio: Portfolio) -> int:
        """Monitor positions in a single portfolio."""
        # Get open positions
        result = await self.db.execute(
            select(Position).where(
                and_(
                    Position.portfolio_id == portfolio.id,
                    Position.quantity != 0
                )
            )
        )
        positions = result.scalars().all()
        
        if not positions:
            return 0
        
        # Calculate portfolio value for concentration check
        portfolio_value = await self._calculate_portfolio_value(portfolio, positions)
        
        signals_created = 0
        
        for position in positions:
            # Get current price (in production, this would fetch real-time data)
            current_price = await self._get_current_price(position.symbol)
            if not current_price:
                continue
            
            # Calculate P/L
            entry_price = float(position.average_price)
            pnl_percent = ((current_price - entry_price) / entry_price) * 100
            
            # Check for P/L threshold alerts
            signal = await self._check_pnl_thresholds(
                portfolio=portfolio,
                position=position,
                current_price=current_price,
                pnl_percent=pnl_percent
            )
            if signal:
                signals_created += 1
            
            # Check for trailing stop opportunity
            signal = await self._check_trailing_stop(
                portfolio=portfolio,
                position=position,
                current_price=current_price,
                pnl_percent=pnl_percent
            )
            if signal:
                signals_created += 1
            
            # Check position concentration
            position_value = abs(float(position.quantity) * current_price)
            concentration_pct = (position_value / portfolio_value) * 100 if portfolio_value > 0 else 0
            
            signal = await self._check_concentration_risk(
                portfolio=portfolio,
                position=position,
                concentration_pct=concentration_pct
            )
            if signal:
                signals_created += 1
        
        return signals_created
    
    async def _check_pnl_thresholds(
        self,
        portfolio: Portfolio,
        position: Position,
        current_price: float,
        pnl_percent: float
    ) -> Optional[BotSignal]:
        """Check if position P/L has crossed any threshold."""
        
        # Create unique key for this position/threshold combo
        def get_alert_key(threshold: float) -> str:
            return f"{position.id}:pnl:{threshold}"
        
        # Check profit thresholds
        for threshold in self.PROFIT_ALERT_THRESHOLDS:
            if pnl_percent >= threshold:
                alert_key = get_alert_key(threshold)
                
                # Don't send duplicate alerts within 4 hours
                if self._should_skip_alert(alert_key):
                    continue
                
                # Create profit alert
                signal = await self.signal_engine.create_position_alert(
                    user_id=portfolio.user_id,
                    portfolio_id=portfolio.id,
                    symbol=position.symbol,
                    position_id=position.id,
                    alert_reason=f"Profit target +{threshold}% reached",
                    current_price=current_price,
                    entry_price=float(position.average_price),
                    pnl_percent=pnl_percent,
                    suggested_action=SignalDirection.REDUCE if threshold >= 5 else SignalDirection.HOLD,
                    priority=SignalPriority.HIGH if threshold >= 5 else SignalPriority.MEDIUM
                )
                
                self._mark_alert_sent(alert_key)
                return signal
        
        # Check loss thresholds
        for threshold in self.LOSS_ALERT_THRESHOLDS:
            if pnl_percent <= threshold:
                alert_key = get_alert_key(threshold)
                
                if self._should_skip_alert(alert_key):
                    continue
                
                # Create loss alert
                priority = SignalPriority.URGENT if threshold <= -5 else SignalPriority.HIGH
                
                signal = await self.signal_engine.create_position_alert(
                    user_id=portfolio.user_id,
                    portfolio_id=portfolio.id,
                    symbol=position.symbol,
                    position_id=position.id,
                    alert_reason=f"Loss threshold {threshold}% hit",
                    current_price=current_price,
                    entry_price=float(position.average_price),
                    pnl_percent=pnl_percent,
                    suggested_action=SignalDirection.CLOSE if threshold <= -5 else SignalDirection.REDUCE,
                    priority=priority
                )
                
                self._mark_alert_sent(alert_key)
                return signal
        
        return None
    
    async def _check_trailing_stop(
        self,
        portfolio: Portfolio,
        position: Position,
        current_price: float,
        pnl_percent: float
    ) -> Optional[BotSignal]:
        """Check if trailing stop should be suggested."""
        
        if pnl_percent < self.TRAILING_STOP_TRIGGER:
            return None
        
        alert_key = f"{position.id}:trailing_stop"
        
        if self._should_skip_alert(alert_key, hours=8):
            return None
        
        entry_price = float(position.average_price)
        
        # Calculate suggested trailing stop
        # Lock in 50% of current profit
        profit_to_lock = (pnl_percent / 100) * entry_price * 0.5
        new_stop = entry_price + profit_to_lock
        
        signal = await self.signal_engine.create_position_alert(
            user_id=portfolio.user_id,
            portfolio_id=portfolio.id,
            symbol=position.symbol,
            position_id=position.id,
            alert_reason="Trailing stop opportunity",
            current_price=current_price,
            entry_price=entry_price,
            pnl_percent=pnl_percent,
            suggested_action=SignalDirection.HOLD,
            new_stop_suggestion=round(new_stop, 2),
            priority=SignalPriority.MEDIUM
        )
        
        self._mark_alert_sent(alert_key)
        return signal
    
    async def _check_concentration_risk(
        self,
        portfolio: Portfolio,
        position: Position,
        concentration_pct: float
    ) -> Optional[BotSignal]:
        """Check if position is too concentrated."""
        
        if concentration_pct < self.MAX_POSITION_PERCENT:
            return None
        
        alert_key = f"{position.id}:concentration"
        
        if self._should_skip_alert(alert_key, hours=24):
            return None
        
        await self.signal_engine.create_risk_warning(
            user_id=portfolio.user_id,
            portfolio_id=portfolio.id,
            warning_type="Position Concentration",
            message_detail=f"""Position **{position.symbol}** represents **{concentration_pct:.1f}%** of your portfolio.

Recommended maximum is {self.MAX_POSITION_PERCENT}%.

Consider reducing position size to manage concentration risk.""",
            affected_symbols=[position.symbol],
            priority=SignalPriority.HIGH
        )
        
        self._mark_alert_sent(alert_key)
        return True
    
    async def _calculate_portfolio_value(
        self,
        portfolio: Portfolio,
        positions: List[Position]
    ) -> float:
        """Calculate total portfolio value."""
        cash = float(portfolio.cash_balance)
        positions_value = 0.0
        
        for position in positions:
            current_price = await self._get_current_price(position.symbol)
            if current_price:
                positions_value += abs(float(position.quantity) * current_price)
        
        return cash + positions_value
    
    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current price for a symbol.
        
        In production, this would integrate with the data provider aggregator.
        For now, returns None to indicate price unavailable.
        """
        # TODO: Integrate with actual data provider
        # from app.data_providers.aggregator import get_aggregator
        # aggregator = get_aggregator()
        # quote = await aggregator.get_quote(symbol)
        # return quote.price if quote else None
        
        return None
    
    def _should_skip_alert(self, alert_key: str, hours: int = 4) -> bool:
        """Check if we recently sent this alert."""
        if alert_key not in self._sent_alerts:
            return False
        
        last_sent = self._sent_alerts[alert_key]
        return datetime.utcnow() - last_sent < timedelta(hours=hours)
    
    def _mark_alert_sent(self, alert_key: str) -> None:
        """Mark an alert as sent."""
        self._sent_alerts[alert_key] = datetime.utcnow()


async def run_position_monitor_for_all_users(db: AsyncSession) -> int:
    """
    Run position monitoring for all active users.
    Called by scheduler job during market hours.
    """
    from app.db.models import User
    
    result = await db.execute(
        select(User).where(User.is_active == True)
    )
    users = result.scalars().all()
    
    total_signals = 0
    for user in users:
        try:
            monitor = PositionMonitor(db)
            signals = await monitor.monitor_user_positions(user.id)
            total_signals += signals
        except Exception as e:
            logger.error(f"Position monitoring failed for user {user.id}: {e}")
    
    if total_signals > 0:
        logger.info(f"Position monitoring complete: {total_signals} signals created")
    
    return total_signals
