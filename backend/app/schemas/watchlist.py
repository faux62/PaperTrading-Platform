"""
PaperTrading Platform - Watchlist Schemas
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class WatchlistSymbolBase(BaseModel):
    """Base schema for watchlist symbol."""
    symbol: str = Field(..., description="Stock ticker symbol")


class WatchlistSymbolResponse(WatchlistSymbolBase):
    """Response schema for watchlist symbol."""
    added_at: datetime


class WatchlistBase(BaseModel):
    """Base watchlist schema."""
    name: str = Field(..., min_length=1, max_length=255, description="Watchlist name")
    description: Optional[str] = Field(None, max_length=500, description="Watchlist description")


class WatchlistCreate(WatchlistBase):
    """Schema for creating a watchlist."""
    pass


class WatchlistUpdate(BaseModel):
    """Schema for updating a watchlist."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)


class WatchlistResponse(WatchlistBase):
    """Response schema for watchlist."""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class WatchlistWithSymbols(WatchlistResponse):
    """Watchlist response with symbols list."""
    symbols: list[WatchlistSymbolResponse] = []


class AddSymbolRequest(BaseModel):
    """Request to add symbol to watchlist."""
    symbol: str = Field(..., min_length=1, max_length=20, description="Stock ticker symbol")


class WatchlistSummary(BaseModel):
    """Summary of user's watchlists."""
    total_watchlists: int
    total_symbols: int
    watchlists: list[WatchlistResponse]
