"""
WebSocket endpoint for real-time portfolio updates.

Broadcasts:
- Portfolio value changes
- Position P&L updates
- Order status changes
- Trade executions
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
        return super().default(obj)


class PortfolioConnectionManager:
    """Manages WebSocket connections for portfolio updates."""
    
    def __init__(self):
        # Map of user_id -> set of WebSocket connections
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        # Map of portfolio_id -> set of user_ids watching
        self.portfolio_watchers: Dict[int, Set[int]] = {}
        # Map of user_id -> set of portfolio_ids watching
        self.user_portfolios: Dict[int, Set[int]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        self.user_portfolios[user_id] = set()
        logger.info(f"Portfolio WebSocket connected: user_id={user_id}")
    
    def disconnect(self, websocket: WebSocket, user_id: int):
        """Remove a WebSocket connection."""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        # Clean up portfolio watchers
        if user_id in self.user_portfolios:
            for portfolio_id in self.user_portfolios[user_id]:
                if portfolio_id in self.portfolio_watchers:
                    self.portfolio_watchers[portfolio_id].discard(user_id)
                    if not self.portfolio_watchers[portfolio_id]:
                        del self.portfolio_watchers[portfolio_id]
            del self.user_portfolios[user_id]
        
        logger.info(f"Portfolio WebSocket disconnected: user_id={user_id}")
    
    def watch_portfolio(self, user_id: int, portfolio_ids: list[int]):
        """Subscribe user to portfolio updates."""
        if user_id not in self.user_portfolios:
            self.user_portfolios[user_id] = set()
        
        for portfolio_id in portfolio_ids:
            self.user_portfolios[user_id].add(portfolio_id)
            if portfolio_id not in self.portfolio_watchers:
                self.portfolio_watchers[portfolio_id] = set()
            self.portfolio_watchers[portfolio_id].add(user_id)
        
        logger.debug(f"User {user_id} watching portfolios: {portfolio_ids}")
    
    def unwatch_portfolio(self, user_id: int, portfolio_ids: list[int]):
        """Unsubscribe user from portfolio updates."""
        if user_id not in self.user_portfolios:
            return
        
        for portfolio_id in portfolio_ids:
            self.user_portfolios[user_id].discard(portfolio_id)
            if portfolio_id in self.portfolio_watchers:
                self.portfolio_watchers[portfolio_id].discard(user_id)
                if not self.portfolio_watchers[portfolio_id]:
                    del self.portfolio_watchers[portfolio_id]
    
    async def send_to_user(self, message: dict, user_id: int):
        """Send a message to a specific user."""
        if user_id in self.active_connections:
            disconnected = []
            json_message = json.dumps(message, cls=DecimalEncoder)
            
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_text(json_message)
                except Exception:
                    disconnected.append(websocket)
            
            for ws in disconnected:
                self.active_connections[user_id].discard(ws)
    
    async def broadcast_portfolio_update(
        self, 
        portfolio_id: int, 
        update_type: str,
        data: dict
    ):
        """Broadcast portfolio update to all watchers."""
        if portfolio_id not in self.portfolio_watchers:
            return
        
        message = {
            "type": update_type,
            "portfolio_id": portfolio_id,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        for user_id in self.portfolio_watchers[portfolio_id]:
            await self.send_to_user(message, user_id)
    
    async def send_order_update(
        self,
        user_id: int,
        order_id: int,
        status: str,
        data: dict
    ):
        """Send order status update to user."""
        message = {
            "type": "order_update",
            "order_id": order_id,
            "status": status,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_to_user(message, user_id)
    
    async def send_trade_execution(
        self,
        user_id: int,
        trade_data: dict
    ):
        """Send trade execution notification."""
        message = {
            "type": "trade_executed",
            "data": trade_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_to_user(message, user_id)
    
    def get_stats(self) -> dict:
        """Get connection statistics."""
        return {
            "total_connections": sum(len(conns) for conns in self.active_connections.values()),
            "unique_users": len(self.active_connections),
            "watched_portfolios": len(self.portfolio_watchers),
            "total_watchers": sum(len(w) for w in self.portfolio_watchers.values())
        }


# Global connection manager
portfolio_manager = PortfolioConnectionManager()


async def verify_ws_token(token: str) -> Optional[int]:
    """Verify JWT token from WebSocket connection."""
    from jose import jwt, JWTError
    
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"]
        )
        user_id = int(payload.get("sub"))
        token_type = payload.get("type")
        
        if token_type != "access":
            return None
        
        return user_id
    except (JWTError, ValueError):
        return None


@router.websocket("/ws/portfolio")
async def websocket_portfolio_endpoint(
    websocket: WebSocket,
    token: str = Query(...)
):
    """
    WebSocket endpoint for real-time portfolio updates.
    
    Connect with: ws://localhost:8000/api/v1/ws/portfolio?token=<jwt_token>
    
    Message types to send:
    - {"action": "watch", "portfolio_ids": [1, 2, 3]}
    - {"action": "unwatch", "portfolio_ids": [1]}
    - {"action": "ping"}
    
    Message types received:
    - {"type": "portfolio_value", "portfolio_id": 1, "data": {...}}
    - {"type": "position_update", "portfolio_id": 1, "data": {...}}
    - {"type": "order_update", "order_id": 1, "status": "...", "data": {...}}
    - {"type": "trade_executed", "data": {...}}
    - {"type": "connected", "message": "..."}
    - {"type": "pong"}
    - {"type": "error", "message": "..."}
    """
    # Verify token
    user_id = await verify_ws_token(token)
    if user_id is None:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return
    
    await portfolio_manager.connect(websocket, user_id)
    
    try:
        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "message": "Successfully connected to portfolio updates",
            "user_id": user_id
        })
        
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                action = message.get("action")
                
                if action == "watch":
                    portfolio_ids = message.get("portfolio_ids", [])
                    if portfolio_ids:
                        # TODO: Verify user owns these portfolios
                        portfolio_manager.watch_portfolio(user_id, portfolio_ids)
                        await websocket.send_json({
                            "type": "watching",
                            "portfolio_ids": portfolio_ids
                        })
                
                elif action == "unwatch":
                    portfolio_ids = message.get("portfolio_ids", [])
                    if portfolio_ids:
                        portfolio_manager.unwatch_portfolio(user_id, portfolio_ids)
                        await websocket.send_json({
                            "type": "unwatched",
                            "portfolio_ids": portfolio_ids
                        })
                
                elif action == "ping":
                    await websocket.send_json({"type": "pong"})
                
                elif action == "get_watched":
                    watched = list(portfolio_manager.user_portfolios.get(user_id, set()))
                    await websocket.send_json({
                        "type": "watched_portfolios",
                        "portfolio_ids": watched
                    })
                
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown action: {action}"
                    })
            
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })
    
    except WebSocketDisconnect:
        portfolio_manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"Portfolio WebSocket error for user {user_id}: {e}")
        portfolio_manager.disconnect(websocket, user_id)


@router.get("/ws/portfolio/stats")
async def get_portfolio_ws_stats():
    """Get portfolio WebSocket connection statistics."""
    return portfolio_manager.get_stats()


# Functions to broadcast updates from other modules
async def broadcast_portfolio_value(portfolio_id: int, value_data: dict):
    """Broadcast portfolio value update."""
    await portfolio_manager.broadcast_portfolio_update(
        portfolio_id, "portfolio_value", value_data
    )


async def broadcast_position_update(portfolio_id: int, position_data: dict):
    """Broadcast position update."""
    await portfolio_manager.broadcast_portfolio_update(
        portfolio_id, "position_update", position_data
    )


async def notify_order_update(user_id: int, order_id: int, status: str, data: dict):
    """Notify user of order status change."""
    await portfolio_manager.send_order_update(user_id, order_id, status, data)


async def notify_trade_execution(user_id: int, trade_data: dict):
    """Notify user of trade execution."""
    await portfolio_manager.send_trade_execution(user_id, trade_data)


def get_portfolio_manager() -> PortfolioConnectionManager:
    """Get the global portfolio connection manager."""
    return portfolio_manager
