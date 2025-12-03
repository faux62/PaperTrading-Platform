"""
Unit Tests - Watchlist and Alert Schemas
Tests for watchlist and alert schema validation.
"""
import pytest
from datetime import datetime
from pydantic import ValidationError

from app.schemas.watchlist import (
    WatchlistBase,
    WatchlistCreate,
    WatchlistUpdate,
    WatchlistResponse,
    WatchlistWithSymbols,
    AddSymbolRequest,
    WatchlistSummary,
    WatchlistSymbolResponse
)


class TestWatchlistCreate:
    """Tests for WatchlistCreate schema."""
    
    def test_valid_watchlist_create(self):
        """Valid data should create WatchlistCreate successfully."""
        data = {
            "name": "Tech Stocks",
            "description": "My favorite tech stocks"
        }
        watchlist = WatchlistCreate(**data)
        assert watchlist.name == "Tech Stocks"
        assert watchlist.description == "My favorite tech stocks"
    
    def test_watchlist_create_without_description(self):
        """Description should be optional."""
        watchlist = WatchlistCreate(name="My Watchlist")
        assert watchlist.name == "My Watchlist"
        assert watchlist.description is None
    
    def test_watchlist_create_empty_name(self):
        """Empty name should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            WatchlistCreate(name="")
        assert "name" in str(exc_info.value).lower()
    
    def test_watchlist_create_long_name(self):
        """Name longer than 255 chars should raise ValidationError."""
        with pytest.raises(ValidationError):
            WatchlistCreate(name="a" * 256)
    
    def test_watchlist_create_long_description(self):
        """Description longer than 500 chars should raise ValidationError."""
        with pytest.raises(ValidationError):
            WatchlistCreate(name="Test", description="a" * 501)


class TestWatchlistUpdate:
    """Tests for WatchlistUpdate schema."""
    
    def test_update_all_fields(self):
        """All fields should be updateable."""
        update = WatchlistUpdate(
            name="New Name",
            description="New description"
        )
        assert update.name == "New Name"
        assert update.description == "New description"
    
    def test_update_partial(self):
        """Partial updates should work."""
        update = WatchlistUpdate(name="Just Name")
        assert update.name == "Just Name"
        assert update.description is None
    
    def test_update_empty(self):
        """Empty update should be valid."""
        update = WatchlistUpdate()
        assert update.name is None
        assert update.description is None


class TestWatchlistResponse:
    """Tests for WatchlistResponse schema."""
    
    def test_valid_response(self):
        """Valid response data should work."""
        data = {
            "id": 1,
            "user_id": 1,
            "name": "Tech Stocks",
            "description": "Tech companies",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        response = WatchlistResponse(**data)
        assert response.id == 1
        assert response.name == "Tech Stocks"


class TestWatchlistWithSymbols:
    """Tests for WatchlistWithSymbols schema."""
    
    def test_with_symbols(self):
        """Watchlist with symbols should work."""
        data = {
            "id": 1,
            "user_id": 1,
            "name": "Tech Stocks",
            "description": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "symbols": [
                {"symbol": "AAPL", "added_at": datetime.utcnow()},
                {"symbol": "GOOGL", "added_at": datetime.utcnow()}
            ]
        }
        response = WatchlistWithSymbols(**data)
        assert len(response.symbols) == 2
        assert response.symbols[0].symbol == "AAPL"
    
    def test_empty_symbols(self):
        """Watchlist without symbols should default to empty list."""
        data = {
            "id": 1,
            "user_id": 1,
            "name": "Empty",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        response = WatchlistWithSymbols(**data)
        assert response.symbols == []


class TestAddSymbolRequest:
    """Tests for AddSymbolRequest schema."""
    
    def test_valid_symbol(self):
        """Valid symbol should work."""
        request = AddSymbolRequest(symbol="AAPL")
        assert request.symbol == "AAPL"
    
    def test_empty_symbol(self):
        """Empty symbol should raise ValidationError."""
        with pytest.raises(ValidationError):
            AddSymbolRequest(symbol="")
    
    def test_long_symbol(self):
        """Symbol longer than 20 chars should raise ValidationError."""
        with pytest.raises(ValidationError):
            AddSymbolRequest(symbol="A" * 21)


class TestWatchlistSummary:
    """Tests for WatchlistSummary schema."""
    
    def test_valid_summary(self):
        """Valid summary should work."""
        summary = WatchlistSummary(
            total_watchlists=3,
            total_symbols=15,
            watchlists=[]
        )
        assert summary.total_watchlists == 3
        assert summary.total_symbols == 15
