"""
PaperTrading Platform - Database Models
"""
from app.db.models.user import User
from app.db.models.user_settings import UserSettings
from app.db.models.portfolio import Portfolio, RiskProfile
from app.db.models.position import Position
from app.db.models.trade import Trade, TradeType, OrderType, TradeStatus
from app.db.models.watchlist import Watchlist, watchlist_symbols
from app.db.models.alert import Alert, AlertType, AlertStatus
from app.db.models.cash_balance import FxTransaction  # CashBalance REMOVED - deprecated
from app.db.models.bot_signal import (
    BotSignal,
    BotReport,
    SignalType,
    SignalPriority,
    SignalStatus,
    SignalDirection,
)
from app.db.models.market_universe import MarketUniverse, MarketRegion, AssetType
from app.db.models.price_bar import PriceBar, TimeFrame
from app.db.models.exchange_rate import ExchangeRate

__all__ = [
    "User",
    "UserSettings",
    "Portfolio",
    "RiskProfile",
    "Position",
    "Trade",
    "TradeType",
    "OrderType",
    "TradeStatus",
    "Watchlist",
    "watchlist_symbols",
    "Alert",
    "AlertType",
    "AlertStatus",
    # "CashBalance",  # REMOVED - deprecated
    "FxTransaction",
    "BotSignal",
    "BotReport",
    "SignalType",
    "SignalPriority",
    "SignalStatus",
    "SignalDirection",
    # Market Universe
    "MarketUniverse",
    "MarketRegion",
    "AssetType",
    # Price Bars
    "PriceBar",
    "TimeFrame",
    # Exchange Rates
    "ExchangeRate",
]
