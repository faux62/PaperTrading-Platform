"""
PaperTrading Platform - API v1 Router
"""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, portfolios, positions, trades, market_data, watchlists, analytics

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(portfolios.router, prefix="/portfolios", tags=["Portfolios"])
api_router.include_router(positions.router, prefix="/positions", tags=["Positions"])
api_router.include_router(trades.router, prefix="/trades", tags=["Trades"])
api_router.include_router(market_data.router, prefix="/market", tags=["Market Data"])
api_router.include_router(watchlists.router, prefix="/watchlists", tags=["Watchlists"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
