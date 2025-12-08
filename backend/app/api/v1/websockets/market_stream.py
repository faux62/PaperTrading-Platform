"""
WebSocket endpoint for real-time market data streaming.
"""
import asyncio
import json
from datetime import datetime
from typing import Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from jose import jwt, JWTError

from app.config import settings
from app.utils.logger import logger

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections and message broadcasting."""
    
    def __init__(self):
        # Map of user_id -> set of WebSocket connections
        self.active_connections: dict[int, Set[WebSocket]] = {}
        # Map of symbol -> set of user_ids subscribed
        self.symbol_subscriptions: dict[str, Set[int]] = {}
        # Map of user_id -> set of subscribed symbols
        self.user_subscriptions: dict[int, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        self.user_subscriptions[user_id] = set()
        logger.info(f"WebSocket connected: user_id={user_id}")
    
    def disconnect(self, websocket: WebSocket, user_id: int):
        """Remove a WebSocket connection."""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        # Clean up subscriptions
        if user_id in self.user_subscriptions:
            for symbol in self.user_subscriptions[user_id]:
                if symbol in self.symbol_subscriptions:
                    self.symbol_subscriptions[symbol].discard(user_id)
                    if not self.symbol_subscriptions[symbol]:
                        del self.symbol_subscriptions[symbol]
            del self.user_subscriptions[user_id]
        
        logger.info(f"WebSocket disconnected: user_id={user_id}")
    
    def subscribe(self, user_id: int, symbols: list[str]):
        """Subscribe a user to symbols."""
        if user_id not in self.user_subscriptions:
            self.user_subscriptions[user_id] = set()
        
        for symbol in symbols:
            symbol = symbol.upper()
            self.user_subscriptions[user_id].add(symbol)
            if symbol not in self.symbol_subscriptions:
                self.symbol_subscriptions[symbol] = set()
            self.symbol_subscriptions[symbol].add(user_id)
        
        logger.debug(f"User {user_id} subscribed to: {symbols}")
    
    def unsubscribe(self, user_id: int, symbols: list[str]):
        """Unsubscribe a user from symbols."""
        if user_id not in self.user_subscriptions:
            return
        
        for symbol in symbols:
            symbol = symbol.upper()
            self.user_subscriptions[user_id].discard(symbol)
            if symbol in self.symbol_subscriptions:
                self.symbol_subscriptions[symbol].discard(user_id)
                if not self.symbol_subscriptions[symbol]:
                    del self.symbol_subscriptions[symbol]
        
        logger.debug(f"User {user_id} unsubscribed from: {symbols}")
    
    async def send_personal_message(self, message: dict, user_id: int):
        """Send a message to a specific user."""
        if user_id in self.active_connections:
            disconnected = []
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_json(message)
                except Exception:
                    disconnected.append(websocket)
            
            # Clean up disconnected sockets
            for ws in disconnected:
                self.active_connections[user_id].discard(ws)
    
    async def broadcast_quote(self, symbol: str, quote_data: dict):
        """Broadcast a quote update to all subscribed users."""
        symbol = symbol.upper()
        if symbol not in self.symbol_subscriptions:
            return
        
        message = {
            "type": "quote",
            "symbol": symbol,
            "data": quote_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        for user_id in self.symbol_subscriptions[symbol]:
            await self.send_personal_message(message, user_id)
    
    async def broadcast_to_all(self, message: dict):
        """Broadcast a message to all connected users."""
        for user_id in self.active_connections:
            await self.send_personal_message(message, user_id)
    
    def get_stats(self) -> dict:
        """Get connection statistics."""
        return {
            "total_connections": sum(len(conns) for conns in self.active_connections.values()),
            "unique_users": len(self.active_connections),
            "subscribed_symbols": len(self.symbol_subscriptions),
            "total_subscriptions": sum(len(subs) for subs in self.symbol_subscriptions.values())
        }


# Global connection manager
manager = ConnectionManager()


async def verify_ws_token(token: str) -> int | None:
    """Verify JWT token from WebSocket connection."""
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


@router.websocket("/ws/market")
async def websocket_market_endpoint(
    websocket: WebSocket,
    token: str = Query(...)
):
    """
    WebSocket endpoint for real-time market data.
    
    Connect with: ws://localhost:8000/api/v1/ws/market?token=<jwt_token>
    
    Message types to send:
    - {"action": "subscribe", "symbols": ["AAPL", "GOOGL"]}
    - {"action": "unsubscribe", "symbols": ["AAPL"]}
    - {"action": "ping"}
    
    Message types received:
    - {"type": "quote", "symbol": "AAPL", "data": {...}, "timestamp": "..."}
    - {"type": "connected", "message": "..."}
    - {"type": "subscribed", "symbols": [...]}
    - {"type": "unsubscribed", "symbols": [...]}
    - {"type": "pong"}
    - {"type": "error", "message": "..."}
    """
    # Verify token
    user_id = await verify_ws_token(token)
    if user_id is None:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return
    
    await manager.connect(websocket, user_id)
    
    try:
        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "message": "Successfully connected to market stream",
            "user_id": user_id
        })
        
        while True:
            # Receive message
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                action = message.get("action")
                
                if action == "subscribe":
                    symbols = message.get("symbols", [])
                    if symbols:
                        manager.subscribe(user_id, symbols)
                        await websocket.send_json({
                            "type": "subscribed",
                            "symbols": [s.upper() for s in symbols]
                        })
                
                elif action == "unsubscribe":
                    symbols = message.get("symbols", [])
                    if symbols:
                        manager.unsubscribe(user_id, symbols)
                        await websocket.send_json({
                            "type": "unsubscribed",
                            "symbols": [s.upper() for s in symbols]
                        })
                
                elif action == "ping":
                    await websocket.send_json({"type": "pong"})
                
                elif action == "get_subscriptions":
                    subs = list(manager.user_subscriptions.get(user_id, set()))
                    await websocket.send_json({
                        "type": "subscriptions",
                        "symbols": subs
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
        manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(websocket, user_id)


@router.get("/ws/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics."""
    return manager.get_stats()


# Function to be called by data providers to broadcast quotes
async def broadcast_market_quote(symbol: str, quote_data: dict):
    """
    Broadcast a market quote to all subscribed users.
    Call this from data providers when new quotes arrive.
    """
    await manager.broadcast_quote(symbol, quote_data)


# Export manager for use in other modules
def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager."""
    return manager
