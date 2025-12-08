"""
PaperTrading Platform - API v1 Router
"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth, portfolios, positions, trades, market_data, 
    watchlists, analytics, alerts, ml_features, ml_predictions, currency, settings,
    providers, bot
)
from app.api.v1.websockets import market_stream_router, portfolio_stream_router, bot_stream_router

api_router = APIRouter()


# API v1 root endpoint
@api_router.get("/", tags=["API Info"])
async def api_root():
    """API v1 root - returns version info."""
    return {
        "api": "PaperTrading Platform",
        "version": "v1",
        "status": "operational"
    }


# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(portfolios.router, prefix="/portfolios", tags=["Portfolios"])
api_router.include_router(positions.router, prefix="/positions", tags=["Positions"])
api_router.include_router(trades.router, prefix="/trades", tags=["Trades"])
api_router.include_router(market_data.router, prefix="/market", tags=["Market Data"])
api_router.include_router(watchlists.router, prefix="/watchlists", tags=["Watchlists"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
api_router.include_router(ml_features.router, prefix="/ml/features", tags=["ML Features"])
api_router.include_router(ml_predictions.router, tags=["ML Predictions"])
api_router.include_router(currency.router, prefix="/currency", tags=["Currency"])
api_router.include_router(settings.router, prefix="/settings", tags=["Settings"])
api_router.include_router(providers.router, prefix="/providers", tags=["Provider Monitoring"])
api_router.include_router(bot.router, tags=["Trading Assistant Bot"])

# Include WebSocket routers
api_router.include_router(market_stream_router, tags=["WebSocket - Market"])
api_router.include_router(portfolio_stream_router, tags=["WebSocket - Portfolio"])
api_router.include_router(bot_stream_router, tags=["WebSocket - Bot Advisory"])
