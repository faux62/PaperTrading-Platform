"""
WebSocket endpoints for real-time data streaming.
"""
from .market_stream import router as market_stream_router, get_connection_manager, broadcast_market_quote
from .portfolio_stream import (
    router as portfolio_stream_router, 
    get_portfolio_manager,
    broadcast_portfolio_value,
    broadcast_position_update,
    notify_order_update,
    notify_trade_execution
)

__all__ = [
    # Market stream
    "market_stream_router", 
    "get_connection_manager", 
    "broadcast_market_quote",
    # Portfolio stream
    "portfolio_stream_router",
    "get_portfolio_manager",
    "broadcast_portfolio_value",
    "broadcast_position_update",
    "notify_order_update",
    "notify_trade_execution"
]
