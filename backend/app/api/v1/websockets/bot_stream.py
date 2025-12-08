"""
WebSocket endpoint for real-time Bot Advisory notifications.

Broadcasts:
- New trading signals (ADVISORY ONLY)
- Signal status updates
- Alert notifications
- Report availability
- Bot status changes

ALL notifications are ADVISORY - user must manually execute any suggested action.
"""
import asyncio
import json
from datetime import datetime
from typing import Set, Dict, Optional
from decimal import Decimal
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.config import settings
from app.utils.logger import logger

router = APIRouter()


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal types."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class BotConnectionManager:
    """
    Manages WebSocket connections for Bot Advisory notifications.
    
    Handles:
    - User connections/disconnections
    - Real-time signal broadcasting
    - Signal subscription management
    """
    
    def __init__(self):
        # Map of user_id -> set of WebSocket connections
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        # Map of user_id -> notification preferences
        self.user_preferences: Dict[int, Dict[str, bool]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        
        # Default preferences: all notifications enabled
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = {
                "trade_signals": True,
                "position_alerts": True,
                "risk_warnings": True,
                "market_alerts": True,
                "reports": True,
                "bot_status": True,
            }
        
        logger.info(f"Bot WebSocket connected: user_id={user_id}")
        
        # Send welcome message
        await self.send_to_user({
            "type": "connected",
            "message": "Trading Assistant Bot connected",
            "advisory_notice": "All signals are ADVISORY ONLY - manual execution required",
            "timestamp": datetime.utcnow().isoformat()
        }, user_id)
    
    def disconnect(self, websocket: WebSocket, user_id: int):
        """Remove a WebSocket connection."""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"Bot WebSocket disconnected: user_id={user_id}")
    
    def update_preferences(self, user_id: int, preferences: Dict[str, bool]):
        """Update notification preferences for a user."""
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = {}
        self.user_preferences[user_id].update(preferences)
        logger.debug(f"User {user_id} preferences updated: {preferences}")
    
    def should_notify(self, user_id: int, notification_type: str) -> bool:
        """Check if user should receive this notification type."""
        if user_id not in self.user_preferences:
            return True  # Default: notify
        return self.user_preferences[user_id].get(notification_type, True)
    
    async def send_to_user(self, message: dict, user_id: int):
        """Send a message to a specific user."""
        if user_id not in self.active_connections:
            return
        
        disconnected = []
        json_message = json.dumps(message, cls=DecimalEncoder)
        
        for websocket in self.active_connections[user_id]:
            try:
                await websocket.send_text(json_message)
            except Exception as e:
                logger.warning(f"Failed to send to user {user_id}: {e}")
                disconnected.append(websocket)
        
        for ws in disconnected:
            self.active_connections[user_id].discard(ws)
    
    async def broadcast_to_all(self, message: dict, notification_type: str = None):
        """Broadcast a message to all connected users."""
        for user_id in list(self.active_connections.keys()):
            if notification_type and not self.should_notify(user_id, notification_type):
                continue
            await self.send_to_user(message, user_id)
    
    # ==================== Signal Notifications ====================
    
    async def notify_new_signal(
        self,
        user_id: int,
        signal_data: dict
    ):
        """
        Notify user of a new trading signal.
        
        ADVISORY ONLY - user must manually execute.
        """
        if not self.should_notify(user_id, "trade_signals"):
            return
        
        message = {
            "type": "new_signal",
            "category": "trade_signal",
            "advisory_notice": "⚠️ ADVISORY ONLY - Requires manual execution",
            "signal": signal_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_to_user(message, user_id)
        logger.info(f"Signal notification sent to user {user_id}: {signal_data.get('symbol', 'N/A')}")
    
    async def notify_signal_update(
        self,
        user_id: int,
        signal_id: int,
        status: str,
        update_data: dict = None
    ):
        """Notify user of signal status change."""
        message = {
            "type": "signal_update",
            "category": "trade_signal",
            "signal_id": signal_id,
            "status": status,
            "data": update_data or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_to_user(message, user_id)
    
    async def notify_position_alert(
        self,
        user_id: int,
        alert_data: dict
    ):
        """
        Notify user of position alert (P/L, stop-loss, etc.)
        
        ADVISORY ONLY - user must decide action.
        """
        if not self.should_notify(user_id, "position_alerts"):
            return
        
        message = {
            "type": "position_alert",
            "category": "position_alert",
            "advisory_notice": "⚠️ Review required - Take action manually if needed",
            "alert": alert_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_to_user(message, user_id)
        logger.info(f"Position alert sent to user {user_id}: {alert_data.get('symbol', 'N/A')}")
    
    async def notify_risk_warning(
        self,
        user_id: int,
        warning_data: dict
    ):
        """
        Notify user of risk warning.
        
        Important risk alerts that require attention.
        """
        if not self.should_notify(user_id, "risk_warnings"):
            return
        
        message = {
            "type": "risk_warning",
            "category": "risk_warning",
            "priority": "HIGH",
            "advisory_notice": "⚠️ RISK ALERT - Review and take manual action",
            "warning": warning_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_to_user(message, user_id)
        logger.warning(f"Risk warning sent to user {user_id}: {warning_data.get('message', 'N/A')}")
    
    async def notify_market_alert(
        self,
        user_id: int,
        alert_data: dict
    ):
        """Notify user of market-wide alert."""
        if not self.should_notify(user_id, "market_alerts"):
            return
        
        message = {
            "type": "market_alert",
            "category": "market_alert",
            "alert": alert_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_to_user(message, user_id)
    
    async def notify_report_ready(
        self,
        user_id: int,
        report_data: dict
    ):
        """Notify user that a report is ready."""
        if not self.should_notify(user_id, "reports"):
            return
        
        message = {
            "type": "report_ready",
            "category": "report",
            "report": report_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_to_user(message, user_id)
        logger.info(f"Report notification sent to user {user_id}: {report_data.get('report_type', 'N/A')}")
    
    async def notify_bot_status(
        self,
        status: str,
        details: dict = None
    ):
        """Broadcast bot status change to all users."""
        message = {
            "type": "bot_status",
            "category": "bot_status",
            "status": status,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast_to_all(message, "bot_status")
        logger.info(f"Bot status broadcast: {status}")
    
    async def notify_pre_market_briefing(
        self,
        user_id: int,
        briefing_data: dict
    ):
        """
        Send pre-market briefing to user.
        
        Morning analysis with watchlist and overnight alerts.
        """
        message = {
            "type": "pre_market_briefing",
            "category": "report",
            "advisory_notice": "Pre-market analysis - Review before market open",
            "briefing": briefing_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_to_user(message, user_id)
        logger.info(f"Pre-market briefing sent to user {user_id}")
    
    async def notify_market_close_summary(
        self,
        user_id: int,
        summary_data: dict
    ):
        """Send end-of-day market close summary."""
        message = {
            "type": "market_close_summary",
            "category": "report",
            "summary": summary_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_to_user(message, user_id)
        logger.info(f"Market close summary sent to user {user_id}")
    
    def get_stats(self) -> dict:
        """Get connection statistics."""
        return {
            "total_connections": sum(len(conns) for conns in self.active_connections.values()),
            "unique_users": len(self.active_connections),
            "users_connected": list(self.active_connections.keys())
        }


# Global connection manager
bot_manager = BotConnectionManager()


def get_bot_manager() -> BotConnectionManager:
    """Get the global bot connection manager."""
    return bot_manager


async def verify_ws_token(token: str) -> Optional[int]:
    """Verify JWT token from WebSocket connection."""
    from jose import jwt, JWTError
    
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        user_id = int(payload.get("sub"))
        token_type = payload.get("type")
        
        if token_type != "access":
            return None
        
        return user_id
    except (JWTError, ValueError):
        return None


# ==================== Helper Functions for External Use ====================

async def broadcast_new_signal(user_id: int, signal_data: dict):
    """Helper to broadcast new signal from external modules."""
    await bot_manager.notify_new_signal(user_id, signal_data)


async def broadcast_position_alert(user_id: int, alert_data: dict):
    """Helper to broadcast position alert from external modules."""
    await bot_manager.notify_position_alert(user_id, alert_data)


async def broadcast_risk_warning(user_id: int, warning_data: dict):
    """Helper to broadcast risk warning from external modules."""
    await bot_manager.notify_risk_warning(user_id, warning_data)


async def broadcast_report_ready(user_id: int, report_data: dict):
    """Helper to broadcast report availability from external modules."""
    await bot_manager.notify_report_ready(user_id, report_data)


async def broadcast_bot_status(status: str, details: dict = None):
    """Helper to broadcast bot status from external modules."""
    await bot_manager.notify_bot_status(status, details)


async def broadcast_pre_market_briefing(user_id: int, briefing_data: dict):
    """Helper to send pre-market briefing from external modules."""
    await bot_manager.notify_pre_market_briefing(user_id, briefing_data)


# ==================== WebSocket Endpoint ====================

@router.websocket("/ws/bot")
async def websocket_bot_endpoint(
    websocket: WebSocket,
    token: str = Query(...)
):
    """
    WebSocket endpoint for real-time Trading Assistant Bot notifications.
    
    Connect with token query parameter:
    ws://host/api/v1/ws/bot?token=<jwt_token>
    
    Message Types Received:
    - set_preferences: Update notification preferences
    - ping: Heartbeat (responds with pong)
    
    Message Types Sent:
    - connected: Initial connection confirmation
    - new_signal: New trade signal (ADVISORY ONLY)
    - signal_update: Signal status change
    - position_alert: Position P/L alert
    - risk_warning: Risk alert
    - market_alert: Market-wide alert
    - report_ready: Report availability
    - bot_status: Bot status change
    - pre_market_briefing: Morning analysis
    - market_close_summary: EOD summary
    - pong: Heartbeat response
    - error: Error message
    
    ALL trade signals are ADVISORY ONLY - user must manually execute.
    """
    # Verify token
    user_id = await verify_ws_token(token)
    if not user_id:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return
    
    await bot_manager.connect(websocket, user_id)
    
    try:
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                message_type = message.get("type", "")
                
                if message_type == "ping":
                    # Heartbeat response
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                elif message_type == "set_preferences":
                    # Update notification preferences
                    preferences = message.get("preferences", {})
                    bot_manager.update_preferences(user_id, preferences)
                    await websocket.send_json({
                        "type": "preferences_updated",
                        "preferences": bot_manager.user_preferences.get(user_id, {}),
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                elif message_type == "get_stats":
                    # Get connection stats (admin only - future enhancement)
                    stats = bot_manager.get_stats()
                    await websocket.send_json({
                        "type": "stats",
                        "data": stats,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                else:
                    # Unknown message type
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown message type: {message_type}",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON message",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
    except WebSocketDisconnect:
        bot_manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        bot_manager.disconnect(websocket, user_id)


@router.get("/ws/bot/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics."""
    return bot_manager.get_stats()
