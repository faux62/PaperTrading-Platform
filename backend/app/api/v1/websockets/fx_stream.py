"""
WebSocket endpoint for real-time FX rate streaming.

Broadcasts exchange rate updates to connected clients.
Clients can use these to recalculate position values in real-time.
"""
import asyncio
import json
from datetime import datetime
from typing import Set, Dict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import jwt, JWTError

from app.config import settings
from app.utils.logger import logger
from app.services.fx_rate_service import fx_rate_service
from app.db.redis_client import redis_client

router = APIRouter()


class FXConnectionManager:
    """Manages WebSocket connections for FX rate streaming."""
    
    def __init__(self):
        # Set of all connected WebSockets
        self.active_connections: Set[WebSocket] = set()
        # Map of user_id -> WebSocket for targeted messages
        self.user_connections: Dict[int, Set[WebSocket]] = {}
        # Last broadcast rates (for new connections)
        self.last_rates: Dict[str, float] = {}
        self.last_timestamp: str = None
    
    async def connect(self, websocket: WebSocket, user_id: int):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(websocket)
        
        logger.info(f"FX WebSocket connected: user_id={user_id}")
        
        # Send current rates immediately on connect
        if self.last_rates:
            await self._send_rates_to_socket(websocket, self.last_rates)
        else:
            # Fetch fresh rates if none cached
            rates = await fx_rate_service.get_all_rates("USD")
            if rates:
                self.last_rates = rates
                self.last_timestamp = datetime.utcnow().isoformat()
                await self._send_rates_to_socket(websocket, rates)
    
    def disconnect(self, websocket: WebSocket, user_id: int):
        """Remove a WebSocket connection."""
        self.active_connections.discard(websocket)
        
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        logger.info(f"FX WebSocket disconnected: user_id={user_id}")
    
    async def broadcast_rates(self, rates: Dict[str, float]):
        """Broadcast rates to all connected clients."""
        self.last_rates = rates
        self.last_timestamp = datetime.utcnow().isoformat()
        
        if not self.active_connections:
            return
        
        message = json.dumps({
            "type": "fx_rates",
            "rates": rates,
            "base": "USD",
            "timestamp": self.last_timestamp
        })
        
        # Broadcast to all connections
        disconnected = set()
        for websocket in self.active_connections:
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.debug(f"Failed to send FX rates: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected sockets
        self.active_connections -= disconnected
        
        logger.debug(f"Broadcast FX rates to {len(self.active_connections)} clients")
    
    async def _send_rates_to_socket(self, websocket: WebSocket, rates: Dict[str, float]):
        """Send rates to a specific socket."""
        try:
            await websocket.send_text(json.dumps({
                "type": "fx_rates",
                "rates": rates,
                "base": "USD",
                "timestamp": self.last_timestamp or datetime.utcnow().isoformat()
            }))
        except Exception as e:
            logger.debug(f"Failed to send initial FX rates: {e}")


# Global connection manager
fx_manager = FXConnectionManager()


def verify_ws_token(token: str) -> int:
    """Verify JWT token and return user_id."""
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id = int(payload.get("sub"))
        return user_id
    except JWTError as e:
        logger.error(f"FX WS token verification failed: {e}")
        raise ValueError("Invalid token")


@router.websocket("/fx")
async def fx_rates_websocket(
    websocket: WebSocket,
    token: str = Query(..., description="JWT token for authentication")
):
    """
    WebSocket endpoint for real-time FX rate updates.
    
    Connection URL: ws://host/api/v1/ws/fx?token=<jwt_token>
    
    Messages sent to client:
    - fx_rates: { type: "fx_rates", rates: {...}, base: "USD", timestamp: "..." }
    
    Messages from client:
    - ping: { type: "ping" } -> responds with { type: "pong" }
    - get_rates: { type: "get_rates" } -> sends current rates
    """
    # Verify token
    try:
        user_id = verify_ws_token(token)
    except ValueError:
        await websocket.close(code=4001, reason="Invalid token")
        return
    
    # Connect
    await fx_manager.connect(websocket, user_id)
    
    try:
        while True:
            # Wait for messages from client
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=60.0  # Ping interval
                )
                
                message = json.loads(data)
                msg_type = message.get("type")
                
                if msg_type == "ping":
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    }))
                
                elif msg_type == "get_rates":
                    # Force fetch and send rates
                    rates = await fx_rate_service.get_all_rates("USD")
                    await websocket.send_text(json.dumps({
                        "type": "fx_rates",
                        "rates": rates,
                        "base": "USD",
                        "timestamp": datetime.utcnow().isoformat()
                    }))
                    
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                try:
                    await websocket.send_text(json.dumps({
                        "type": "ping",
                        "timestamp": datetime.utcnow().isoformat()
                    }))
                except Exception:
                    break
                    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"FX WebSocket error: {e}")
    finally:
        fx_manager.disconnect(websocket, user_id)


# =============================================================================
# Broadcast Function (called by FX Rate Service)
# =============================================================================

async def broadcast_fx_update(rates: Dict[str, float]):
    """
    Broadcast FX rate update to all connected clients.
    
    Called by the FX rate service after fetching new rates.
    """
    await fx_manager.broadcast_rates(rates)


# =============================================================================
# Redis PubSub Listener (for distributed broadcast)
# =============================================================================

async def start_fx_pubsub_listener():
    """
    Start listening for FX rate updates via Redis PubSub.
    
    This allows the FX rate job to broadcast updates even if
    running in a different process/container.
    """
    try:
        pubsub = redis_client.pubsub()
        await pubsub.subscribe("fx_rates_updated")
        
        logger.info("FX PubSub listener started")
        
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    rates = data.get("rates", {})
                    if rates:
                        await fx_manager.broadcast_rates(rates)
                except Exception as e:
                    logger.error(f"Failed to process FX PubSub message: {e}")
                    
    except Exception as e:
        logger.error(f"FX PubSub listener error: {e}")
