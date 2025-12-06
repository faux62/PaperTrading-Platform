"""
PaperTrading Platform - Pydantic Schemas
"""
from app.schemas.user import (
    Token,
    TokenPayload,
    RefreshTokenRequest,
    UserBase,
    UserCreate,
    UserLogin,
    UserUpdate,
    UserInDB,
    User,
    UserWithToken,
    Message,
    ErrorResponse,
    PasswordChange,
)

from app.schemas.watchlist import (
    WatchlistSymbolBase,
    WatchlistSymbolResponse,
    WatchlistBase,
    WatchlistCreate,
    WatchlistUpdate,
    WatchlistResponse,
    WatchlistWithSymbols,
    AddSymbolRequest,
    WatchlistSummary,
)

__all__ = [
    # User schemas
    "Token",
    "TokenPayload",
    "RefreshTokenRequest",
    "UserBase",
    "UserCreate",
    "UserLogin",
    "UserUpdate",
    "UserInDB",
    "User",
    "UserWithToken",
    "Message",
    "ErrorResponse",
    "PasswordChange",
    # Watchlist schemas
    "WatchlistSymbolBase",
    "WatchlistSymbolResponse",
    "WatchlistBase",
    "WatchlistCreate",
    "WatchlistUpdate",
    "WatchlistResponse",
    "WatchlistWithSymbols",
    "AddSymbolRequest",
    "WatchlistSummary",
]
