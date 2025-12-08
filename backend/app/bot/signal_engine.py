"""
Trading Assistant Bot - Signal Engine

Core engine for generating trading signals and recommendations.
All signals are ADVISORY only - no automatic execution.
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from loguru import logger

from app.db.models import (
    BotSignal,
    BotReport,
    SignalType,
    SignalPriority,
    SignalStatus,
    SignalDirection,
    Portfolio,
    Position,
    Alert,
    AlertStatus,
    User,
)


def _signal_to_dict(signal: BotSignal) -> dict:
    """Convert BotSignal to dictionary for WebSocket notification."""
    return {
        "id": signal.id,
        "signal_type": signal.signal_type.value,
        "priority": signal.priority.value,
        "status": signal.status.value,
        "symbol": signal.symbol,
        "direction": signal.direction.value if signal.direction else None,
        "title": signal.title,
        "message": signal.message,
        "rationale": signal.rationale,
        "current_price": float(signal.current_price) if signal.current_price else None,
        "suggested_entry": float(signal.suggested_entry) if signal.suggested_entry else None,
        "suggested_stop_loss": float(signal.suggested_stop_loss) if signal.suggested_stop_loss else None,
        "suggested_take_profit": float(signal.suggested_take_profit) if signal.suggested_take_profit else None,
        "suggested_quantity": signal.suggested_quantity,
        "risk_reward_ratio": float(signal.risk_reward_ratio) if signal.risk_reward_ratio else None,
        "confidence_score": float(signal.confidence_score) if signal.confidence_score else None,
        "ml_model_used": signal.ml_model_used,
        "source": signal.source,
        "portfolio_id": signal.portfolio_id,
        "valid_until": signal.valid_until.isoformat() if signal.valid_until else None,
        "created_at": signal.created_at.isoformat() if signal.created_at else None,
    }


async def _notify_websocket(user_id: int, signal: BotSignal):
    """
    Send WebSocket notification for a new signal.
    
    Lazy import to avoid circular dependencies.
    """
    try:
        from app.api.v1.websockets import (
            broadcast_new_signal,
            broadcast_position_alert,
            broadcast_risk_warning,
        )
        
        signal_data = _signal_to_dict(signal)
        
        if signal.signal_type == SignalType.TRADE_SUGGESTION:
            await broadcast_new_signal(user_id, signal_data)
        elif signal.signal_type == SignalType.POSITION_ALERT:
            await broadcast_position_alert(user_id, signal_data)
        elif signal.signal_type == SignalType.RISK_WARNING:
            await broadcast_risk_warning(user_id, signal_data)
        elif signal.signal_type == SignalType.ML_PREDICTION:
            await broadcast_new_signal(user_id, signal_data)
        else:
            # Generic signal notification
            await broadcast_new_signal(user_id, signal_data)
            
        logger.debug(f"WebSocket notification sent for signal {signal.id} to user {user_id}")
        
    except Exception as e:
        # Don't fail the signal creation if WebSocket fails
        logger.warning(f"Failed to send WebSocket notification: {e}")


class SignalEngine:
    """
    Signal generation engine for the Trading Assistant Bot.
    
    Generates ADVISORY signals only:
    - Trade suggestions (entry/stop/target)
    - Position alerts (P/L thresholds)
    - Risk warnings
    - Market alerts
    
    ALL actions require user confirmation and manual execution.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ==================== Signal Creation ====================
    
    async def create_trade_suggestion(
        self,
        user_id: int,
        portfolio_id: int,
        symbol: str,
        direction: SignalDirection,
        current_price: float,
        suggested_entry: float,
        suggested_stop_loss: float,
        suggested_take_profit: float,
        suggested_quantity: int,
        rationale: str,
        confidence_score: float = None,
        ml_model_used: str = None,
        technical_indicators: dict = None,
        priority: SignalPriority = SignalPriority.MEDIUM,
        valid_hours: int = 8,
        source: str = "bot"
    ) -> BotSignal:
        """
        Create a trade suggestion signal.
        
        This is an ADVISORY signal - the user must manually execute any trade.
        
        Args:
            user_id: Target user
            portfolio_id: Target portfolio
            symbol: Stock symbol
            direction: LONG, SHORT, CLOSE, REDUCE
            current_price: Current market price
            suggested_entry: Recommended entry price
            suggested_stop_loss: Recommended stop-loss
            suggested_take_profit: Recommended take-profit
            suggested_quantity: Recommended quantity
            rationale: Explanation for the suggestion
            confidence_score: ML confidence (0-100)
            ml_model_used: Which ML model generated this
            technical_indicators: Dict of indicator values
            priority: Signal priority level
            valid_hours: Hours until signal expires
            source: Signal source identifier
            
        Returns:
            Created BotSignal
        """
        # Calculate risk/reward
        if direction == SignalDirection.LONG:
            risk = suggested_entry - suggested_stop_loss
            reward = suggested_take_profit - suggested_entry
        else:
            risk = suggested_stop_loss - suggested_entry
            reward = suggested_entry - suggested_take_profit
        
        risk_reward = round(reward / risk, 2) if risk > 0 else 0
        
        # Calculate risk percent (simplified - actual implementation would fetch portfolio value)
        risk_percent = None  # Would calculate: (risk * quantity) / portfolio_value * 100
        
        # Build title
        direction_text = "BUY" if direction == SignalDirection.LONG else "SELL"
        title = f"💡 {direction_text} {symbol} @ ${suggested_entry:.2f}"
        
        # Build message
        message = self._build_trade_message(
            symbol=symbol,
            direction=direction,
            current_price=current_price,
            entry=suggested_entry,
            stop=suggested_stop_loss,
            target=suggested_take_profit,
            quantity=suggested_quantity,
            rr_ratio=risk_reward
        )
        
        signal = BotSignal(
            user_id=user_id,
            portfolio_id=portfolio_id,
            signal_type=SignalType.TRADE_SUGGESTION,
            priority=priority,
            status=SignalStatus.PENDING,
            symbol=symbol,
            direction=direction,
            suggested_entry=suggested_entry,
            suggested_stop_loss=suggested_stop_loss,
            suggested_take_profit=suggested_take_profit,
            suggested_quantity=suggested_quantity,
            risk_reward_ratio=risk_reward,
            risk_percent=risk_percent,
            current_price=current_price,
            title=title,
            message=message,
            rationale=rationale,
            confidence_score=confidence_score,
            ml_model_used=ml_model_used,
            technical_indicators=technical_indicators,
            source=source,
            valid_until=datetime.utcnow() + timedelta(hours=valid_hours)
        )
        
        self.db.add(signal)
        await self.db.commit()
        await self.db.refresh(signal)
        
        # Send real-time WebSocket notification
        await _notify_websocket(user_id, signal)
        
        logger.info(f"Created trade suggestion: {symbol} {direction.value} for user {user_id}")
        return signal
    
    async def create_position_alert(
        self,
        user_id: int,
        portfolio_id: int,
        symbol: str,
        position_id: int,
        alert_reason: str,
        current_price: float,
        entry_price: float,
        pnl_percent: float,
        suggested_action: SignalDirection,
        new_stop_suggestion: float = None,
        priority: SignalPriority = SignalPriority.MEDIUM,
    ) -> BotSignal:
        """
        Create a position-related alert signal.
        
        Examples:
        - Position approaching target
        - Position hitting stop loss
        - Trailing stop suggestion
        - Unusual movement in position
        """
        # Build title based on P/L
        if pnl_percent >= 0:
            title = f"📈 {symbol}: +{pnl_percent:.1f}% - {alert_reason}"
        else:
            title = f"📉 {symbol}: {pnl_percent:.1f}% - {alert_reason}"
        
        message = f"""**Position Alert: {symbol}**

Entry: ${entry_price:.2f}
Current: ${current_price:.2f}
P/L: {pnl_percent:+.2f}%

**Reason:** {alert_reason}

**Suggested Action:** {suggested_action.value.upper()}
"""
        
        if new_stop_suggestion:
            message += f"\n**New Stop Suggestion:** ${new_stop_suggestion:.2f}"
        
        rationale = f"Alert triggered: {alert_reason}. Current P/L is {pnl_percent:+.2f}%."
        
        signal = BotSignal(
            user_id=user_id,
            portfolio_id=portfolio_id,
            signal_type=SignalType.POSITION_ALERT,
            priority=priority,
            status=SignalStatus.PENDING,
            symbol=symbol,
            direction=suggested_action,
            current_price=current_price,
            suggested_stop_loss=new_stop_suggestion,
            title=title,
            message=message,
            rationale=rationale,
            source="position_monitor",
            valid_until=datetime.utcnow() + timedelta(hours=4)
        )
        
        self.db.add(signal)
        await self.db.commit()
        await self.db.refresh(signal)
        
        # Send real-time WebSocket notification
        await _notify_websocket(user_id, signal)
        
        logger.info(f"Created position alert: {symbol} for user {user_id}")
        return signal
    
    async def create_risk_warning(
        self,
        user_id: int,
        portfolio_id: int,
        warning_type: str,
        message_detail: str,
        affected_symbols: List[str] = None,
        priority: SignalPriority = SignalPriority.HIGH,
    ) -> BotSignal:
        """
        Create a portfolio risk warning signal.
        
        Examples:
        - Concentration risk (single position > X%)
        - Sector overexposure
        - Correlation warning
        - Drawdown alert
        """
        title = f"⚠️ Risk Warning: {warning_type}"
        
        message = f"""**Portfolio Risk Alert**

**Type:** {warning_type}

{message_detail}
"""
        
        if affected_symbols:
            message += f"\n**Affected Symbols:** {', '.join(affected_symbols)}"
        
        signal = BotSignal(
            user_id=user_id,
            portfolio_id=portfolio_id,
            signal_type=SignalType.RISK_WARNING,
            priority=priority,
            status=SignalStatus.PENDING,
            symbol=affected_symbols[0] if affected_symbols else None,
            title=title,
            message=message,
            rationale=f"Risk detected: {warning_type}",
            source="risk_monitor",
            valid_until=datetime.utcnow() + timedelta(hours=24)
        )
        
        self.db.add(signal)
        await self.db.commit()
        await self.db.refresh(signal)
        
        # Send real-time WebSocket notification
        await _notify_websocket(user_id, signal)
        
        logger.info(f"Created risk warning: {warning_type} for user {user_id}")
        return signal
    
    async def create_market_alert(
        self,
        user_id: int,
        alert_type: str,
        symbol: str,
        current_value: float,
        threshold: float,
        message_detail: str,
        source_alert_id: int = None,
        priority: SignalPriority = SignalPriority.MEDIUM,
    ) -> BotSignal:
        """
        Create a market-based alert signal (from user alerts).
        
        Converts triggered user alerts into bot signals for dashboard display.
        """
        title = f"🔔 Alert: {symbol} {alert_type}"
        
        message = f"""**Market Alert Triggered**

**Symbol:** {symbol}
**Condition:** {alert_type}
**Threshold:** {threshold}
**Current:** {current_value}

{message_detail}
"""
        
        signal = BotSignal(
            user_id=user_id,
            signal_type=SignalType.MARKET_ALERT,
            priority=priority,
            status=SignalStatus.PENDING,
            symbol=symbol,
            current_price=current_value,
            title=title,
            message=message,
            rationale=f"User alert triggered: {alert_type} at {threshold}",
            source="alert_monitor",
            source_alert_id=source_alert_id,
            valid_until=datetime.utcnow() + timedelta(hours=12)
        )
        
        self.db.add(signal)
        await self.db.commit()
        await self.db.refresh(signal)
        
        # Send real-time WebSocket notification
        await _notify_websocket(user_id, signal)
        
        logger.info(f"Created market alert: {symbol} {alert_type} for user {user_id}")
        return signal
    
    async def create_ml_prediction_signal(
        self,
        user_id: int,
        portfolio_id: int,
        symbol: str,
        prediction_direction: SignalDirection,
        confidence: float,
        predicted_change_percent: float,
        model_name: str,
        features_used: dict,
        current_price: float,
        priority: SignalPriority = SignalPriority.MEDIUM,
    ) -> BotSignal:
        """
        Create an ML prediction signal.
        """
        direction_emoji = "🟢" if prediction_direction == SignalDirection.LONG else "🔴"
        title = f"{direction_emoji} ML Signal: {symbol} ({confidence:.0f}% confidence)"
        
        message = f"""**ML Prediction: {symbol}**

**Direction:** {prediction_direction.value.upper()}
**Confidence:** {confidence:.1f}%
**Predicted Move:** {predicted_change_percent:+.2f}%

**Model:** {model_name}
**Current Price:** ${current_price:.2f}

*This is a model prediction. Always verify with your own analysis.*
"""
        
        signal = BotSignal(
            user_id=user_id,
            portfolio_id=portfolio_id,
            signal_type=SignalType.ML_PREDICTION,
            priority=priority,
            status=SignalStatus.PENDING,
            symbol=symbol,
            direction=prediction_direction,
            current_price=current_price,
            title=title,
            message=message,
            rationale=f"ML model {model_name} predicts {predicted_change_percent:+.2f}% move",
            confidence_score=confidence,
            ml_model_used=model_name,
            technical_indicators=features_used,
            source="ml_engine",
            valid_until=datetime.utcnow() + timedelta(hours=24)
        )
        
        self.db.add(signal)
        await self.db.commit()
        await self.db.refresh(signal)
        
        # Send real-time WebSocket notification
        await _notify_websocket(user_id, signal)
        
        logger.info(f"Created ML signal: {symbol} {prediction_direction.value} for user {user_id}")
        return signal
    
    # ==================== Signal Management ====================
    
    async def get_pending_signals(
        self,
        user_id: int,
        signal_types: List[SignalType] = None,
        limit: int = 50
    ) -> List[BotSignal]:
        """Get all pending signals for a user."""
        query = select(BotSignal).where(
            and_(
                BotSignal.user_id == user_id,
                BotSignal.status == SignalStatus.PENDING
            )
        )
        
        if signal_types:
            query = query.where(BotSignal.signal_type.in_(signal_types))
        
        query = query.order_by(
            BotSignal.priority.desc(),
            BotSignal.created_at.desc()
        ).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def accept_signal(
        self,
        signal_id: int,
        user_id: int,
        notes: str = None,
        resulting_trade_id: int = None
    ) -> BotSignal:
        """Mark a signal as accepted by user."""
        signal = await self.db.get(BotSignal, signal_id)
        
        if not signal or signal.user_id != user_id:
            raise ValueError("Signal not found")
        
        signal.status = SignalStatus.ACCEPTED
        signal.user_action_at = datetime.utcnow()
        signal.user_notes = notes
        signal.resulting_trade_id = resulting_trade_id
        
        await self.db.commit()
        await self.db.refresh(signal)
        
        logger.info(f"Signal {signal_id} accepted by user {user_id}")
        return signal
    
    async def ignore_signal(
        self,
        signal_id: int,
        user_id: int,
        notes: str = None
    ) -> BotSignal:
        """Mark a signal as ignored by user."""
        signal = await self.db.get(BotSignal, signal_id)
        
        if not signal or signal.user_id != user_id:
            raise ValueError("Signal not found")
        
        signal.status = SignalStatus.IGNORED
        signal.user_action_at = datetime.utcnow()
        signal.user_notes = notes
        
        await self.db.commit()
        await self.db.refresh(signal)
        
        logger.info(f"Signal {signal_id} ignored by user {user_id}")
        return signal
    
    async def expire_old_signals(self) -> int:
        """Expire signals past their valid_until time."""
        now = datetime.utcnow()
        
        result = await self.db.execute(
            select(BotSignal).where(
                and_(
                    BotSignal.status == SignalStatus.PENDING,
                    BotSignal.valid_until < now
                )
            )
        )
        signals = result.scalars().all()
        
        count = 0
        for signal in signals:
            signal.status = SignalStatus.EXPIRED
            count += 1
        
        await self.db.commit()
        
        if count > 0:
            logger.info(f"Expired {count} old signals")
        
        return count
    
    # ==================== Helper Methods ====================
    
    def _build_trade_message(
        self,
        symbol: str,
        direction: SignalDirection,
        current_price: float,
        entry: float,
        stop: float,
        target: float,
        quantity: int,
        rr_ratio: float
    ) -> str:
        """Build formatted trade suggestion message."""
        
        direction_text = "BUY (Long)" if direction == SignalDirection.LONG else "SELL (Short)"
        
        if direction == SignalDirection.LONG:
            stop_pct = ((entry - stop) / entry) * 100
            target_pct = ((target - entry) / entry) * 100
        else:
            stop_pct = ((stop - entry) / entry) * 100
            target_pct = ((entry - target) / entry) * 100
        
        return f"""**Trade Suggestion: {symbol}**

**Action:** {direction_text}
**Current Price:** ${current_price:.2f}

━━━━━━━━━━━━━━━━━━━━
**Entry:** ${entry:.2f}
**Stop-Loss:** ${stop:.2f} ({stop_pct:.1f}%)
**Take-Profit:** ${target:.2f} (+{target_pct:.1f}%)
**Quantity:** {quantity} shares
━━━━━━━━━━━━━━━━━━━━

**Risk/Reward:** {rr_ratio}:1 {'✅' if rr_ratio >= 2 else '⚠️' if rr_ratio >= 1.5 else '❌'}

*Review and execute manually if you agree with this analysis.*
"""


# Convenience function for dependency injection
async def get_signal_engine(db: AsyncSession) -> SignalEngine:
    """Get a signal engine instance with database session."""
    return SignalEngine(db)
