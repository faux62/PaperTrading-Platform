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
from .bot_stream import (
    router as bot_stream_router,
    get_bot_manager,
    broadcast_new_signal,
    broadcast_position_alert,
    broadcast_risk_warning,
    broadcast_report_ready,
    broadcast_bot_status,
    broadcast_pre_market_briefing,
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
    "notify_trade_execution",
    # Bot stream
    "bot_stream_router",
    "get_bot_manager",
    "broadcast_new_signal",
    "broadcast_position_alert",
    "broadcast_risk_warning",
    "broadcast_report_ready",
    "broadcast_bot_status",
    "broadcast_pre_market_briefing",
]
