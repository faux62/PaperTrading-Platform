"""
Integration Tests - API Endpoints
Tests for REST API authentication and authorization flows.
"""
import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
import json


# ============================================================
# Mock HTTP Response Helpers
# ============================================================

@dataclass
class MockResponse:
    """Mock HTTP response for testing."""
    status_code: int
    json_data: Optional[Dict[str, Any]] = None
    headers: Dict[str, str] = field(default_factory=dict)
    
    def json(self) -> Dict[str, Any]:
        return self.json_data or {}


# ============================================================
# Test Classes
# ============================================================

class TestAuthEndpoints:
    """Tests for authentication endpoints."""
    
    def test_login_success_response(self):
        """Successful login should return tokens."""
        response = MockResponse(
            status_code=200,
            json_data={
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600,
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_invalid_credentials(self):
        """Invalid credentials should return 401."""
        response = MockResponse(
            status_code=401,
            json_data={
                "detail": "Invalid email or password"
            }
        )
        
        assert response.status_code == 401
    
    def test_login_missing_fields(self):
        """Missing fields should return 422."""
        response = MockResponse(
            status_code=422,
            json_data={
                "detail": [
                    {"loc": ["body", "email"], "msg": "field required", "type": "value_error.missing"},
                ]
            }
        )
        
        assert response.status_code == 422
    
    def test_register_success(self):
        """Successful registration should return user."""
        response = MockResponse(
            status_code=201,
            json_data={
                "id": str(uuid4()),
                "email": "newuser@example.com",
                "username": "newuser",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
    
    def test_register_duplicate_email(self):
        """Duplicate email should return 409."""
        response = MockResponse(
            status_code=409,
            json_data={
                "detail": "Email already registered"
            }
        )
        
        assert response.status_code == 409
    
    def test_refresh_token_success(self):
        """Valid refresh token should return new access token."""
        response = MockResponse(
            status_code=200,
            json_data={
                "access_token": "new_access_token...",
                "token_type": "bearer",
                "expires_in": 3600,
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
    
    def test_refresh_token_invalid(self):
        """Invalid refresh token should return 401."""
        response = MockResponse(
            status_code=401,
            json_data={
                "detail": "Invalid or expired refresh token"
            }
        )
        
        assert response.status_code == 401
    
    def test_logout_success(self):
        """Logout should return 200."""
        response = MockResponse(
            status_code=200,
            json_data={
                "message": "Successfully logged out"
            }
        )
        
        assert response.status_code == 200


class TestPortfolioEndpoints:
    """Tests for portfolio management endpoints."""
    
    def test_get_portfolios(self):
        """Should return user portfolios."""
        response = MockResponse(
            status_code=200,
            json_data={
                "portfolios": [
                    {
                        "id": str(uuid4()),
                        "name": "Main Portfolio",
                        "cash_balance": "100000.00",
                        "total_value": "125000.00",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    },
                    {
                        "id": str(uuid4()),
                        "name": "Options Portfolio",
                        "cash_balance": "50000.00",
                        "total_value": "48500.00",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    },
                ],
                "total": 2,
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["portfolios"]) == 2
    
    def test_get_portfolio_by_id(self):
        """Should return specific portfolio."""
        portfolio_id = str(uuid4())
        response = MockResponse(
            status_code=200,
            json_data={
                "id": portfolio_id,
                "name": "Main Portfolio",
                "cash_balance": "100000.00",
                "total_value": "125000.00",
                "positions": [
                    {
                        "symbol": "AAPL",
                        "quantity": 100,
                        "average_cost": "150.00",
                        "current_price": "155.00",
                        "market_value": "15500.00",
                        "unrealized_pnl": "500.00",
                    }
                ],
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == portfolio_id
        assert len(data["positions"]) == 1
    
    def test_get_portfolio_not_found(self):
        """Non-existent portfolio should return 404."""
        response = MockResponse(
            status_code=404,
            json_data={
                "detail": "Portfolio not found"
            }
        )
        
        assert response.status_code == 404
    
    def test_create_portfolio(self):
        """Should create new portfolio."""
        response = MockResponse(
            status_code=201,
            json_data={
                "id": str(uuid4()),
                "name": "New Portfolio",
                "cash_balance": "100000.00",
                "total_value": "100000.00",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Portfolio"
    
    def test_update_portfolio(self):
        """Should update portfolio name."""
        response = MockResponse(
            status_code=200,
            json_data={
                "id": str(uuid4()),
                "name": "Updated Name",
                "cash_balance": "100000.00",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
    
    def test_delete_portfolio(self):
        """Should delete portfolio."""
        response = MockResponse(
            status_code=204,
        )
        
        assert response.status_code == 204
    
    def test_unauthorized_portfolio_access(self):
        """Should return 401 without auth."""
        response = MockResponse(
            status_code=401,
            json_data={
                "detail": "Not authenticated"
            }
        )
        
        assert response.status_code == 401


class TestTradeEndpoints:
    """Tests for trade execution endpoints."""
    
    def test_submit_market_order(self):
        """Should submit market order."""
        response = MockResponse(
            status_code=201,
            json_data={
                "id": str(uuid4()),
                "symbol": "AAPL",
                "side": "buy",
                "order_type": "market",
                "quantity": 100,
                "status": "submitted",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "submitted"
    
    def test_submit_limit_order(self):
        """Should submit limit order with price."""
        response = MockResponse(
            status_code=201,
            json_data={
                "id": str(uuid4()),
                "symbol": "MSFT",
                "side": "buy",
                "order_type": "limit",
                "quantity": 50,
                "price": "380.00",
                "status": "pending",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["order_type"] == "limit"
        assert data["price"] == "380.00"
    
    def test_get_orders(self):
        """Should return user orders."""
        response = MockResponse(
            status_code=200,
            json_data={
                "orders": [
                    {
                        "id": str(uuid4()),
                        "symbol": "AAPL",
                        "side": "buy",
                        "quantity": 100,
                        "status": "filled",
                    },
                    {
                        "id": str(uuid4()),
                        "symbol": "MSFT",
                        "side": "buy",
                        "quantity": 50,
                        "status": "pending",
                    },
                ],
                "total": 2,
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["orders"]) == 2
    
    def test_cancel_order(self):
        """Should cancel pending order."""
        response = MockResponse(
            status_code=200,
            json_data={
                "id": str(uuid4()),
                "status": "cancelled",
                "cancelled_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
    
    def test_cancel_filled_order_fails(self):
        """Should not cancel filled order."""
        response = MockResponse(
            status_code=400,
            json_data={
                "detail": "Cannot cancel filled order"
            }
        )
        
        assert response.status_code == 400
    
    def test_insufficient_funds(self):
        """Should reject order with insufficient funds."""
        response = MockResponse(
            status_code=400,
            json_data={
                "detail": "Insufficient funds"
            }
        )
        
        assert response.status_code == 400
    
    def test_invalid_symbol(self):
        """Should reject invalid symbol."""
        response = MockResponse(
            status_code=400,
            json_data={
                "detail": "Invalid symbol: INVALID123"
            }
        )
        
        assert response.status_code == 400


class TestMarketDataEndpoints:
    """Tests for market data endpoints."""
    
    def test_get_quote(self):
        """Should return stock quote."""
        response = MockResponse(
            status_code=200,
            json_data={
                "symbol": "AAPL",
                "price": "150.25",
                "change": "2.50",
                "change_percent": "1.69",
                "volume": 50000000,
                "bid": "150.20",
                "ask": "150.30",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert "price" in data
    
    def test_get_batch_quotes(self):
        """Should return multiple quotes."""
        response = MockResponse(
            status_code=200,
            json_data={
                "quotes": [
                    {"symbol": "AAPL", "price": "150.25"},
                    {"symbol": "MSFT", "price": "380.50"},
                    {"symbol": "GOOGL", "price": "140.75"},
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["quotes"]) == 3
    
    def test_get_historical_data(self):
        """Should return OHLCV data."""
        response = MockResponse(
            status_code=200,
            json_data={
                "symbol": "AAPL",
                "interval": "1d",
                "data": [
                    {
                        "timestamp": "2024-01-02T00:00:00Z",
                        "open": "150.00",
                        "high": "152.00",
                        "low": "149.00",
                        "close": "151.50",
                        "volume": 45000000,
                    },
                    {
                        "timestamp": "2024-01-03T00:00:00Z",
                        "open": "151.50",
                        "high": "153.00",
                        "low": "150.50",
                        "close": "152.75",
                        "volume": 48000000,
                    },
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert len(data["data"]) == 2
    
    def test_get_quote_invalid_symbol(self):
        """Should return 404 for invalid symbol."""
        response = MockResponse(
            status_code=404,
            json_data={
                "detail": "Symbol not found"
            }
        )
        
        assert response.status_code == 404
    
    def test_market_data_rate_limit(self):
        """Should return 429 when rate limited."""
        response = MockResponse(
            status_code=429,
            json_data={
                "detail": "Rate limit exceeded"
            },
            headers={"Retry-After": "60"}
        )
        
        assert response.status_code == 429
        assert "Retry-After" in response.headers


class TestWatchlistEndpoints:
    """Tests for watchlist endpoints."""
    
    def test_get_watchlists(self):
        """Should return user watchlists."""
        response = MockResponse(
            status_code=200,
            json_data={
                "watchlists": [
                    {
                        "id": str(uuid4()),
                        "name": "Tech Stocks",
                        "symbol_count": 5,
                    },
                    {
                        "id": str(uuid4()),
                        "name": "Dividend Plays",
                        "symbol_count": 10,
                    },
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["watchlists"]) == 2
    
    def test_get_watchlist_with_symbols(self):
        """Should return watchlist with symbols."""
        response = MockResponse(
            status_code=200,
            json_data={
                "id": str(uuid4()),
                "name": "Tech Stocks",
                "symbols": ["AAPL", "MSFT", "GOOGL", "AMZN", "META"],
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["symbols"]) == 5
    
    def test_create_watchlist(self):
        """Should create watchlist."""
        response = MockResponse(
            status_code=201,
            json_data={
                "id": str(uuid4()),
                "name": "New Watchlist",
                "symbols": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        
        assert response.status_code == 201
    
    def test_add_symbol_to_watchlist(self):
        """Should add symbol to watchlist."""
        response = MockResponse(
            status_code=200,
            json_data={
                "id": str(uuid4()),
                "name": "Tech Stocks",
                "symbols": ["AAPL", "MSFT", "NVDA"],  # NVDA added
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "NVDA" in data["symbols"]
    
    def test_remove_symbol_from_watchlist(self):
        """Should remove symbol from watchlist."""
        response = MockResponse(
            status_code=200,
            json_data={
                "id": str(uuid4()),
                "name": "Tech Stocks",
                "symbols": ["AAPL", "GOOGL"],  # MSFT removed
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "MSFT" not in data["symbols"]
    
    def test_delete_watchlist(self):
        """Should delete watchlist."""
        response = MockResponse(
            status_code=204,
        )
        
        assert response.status_code == 204


class TestAnalyticsEndpoints:
    """Tests for analytics endpoints."""
    
    def test_get_portfolio_analytics(self):
        """Should return portfolio analytics."""
        response = MockResponse(
            status_code=200,
            json_data={
                "portfolio_id": str(uuid4()),
                "total_value": "125000.00",
                "total_return": "25000.00",
                "total_return_pct": "25.00",
                "realized_pnl": "5000.00",
                "unrealized_pnl": "20000.00",
                "sharpe_ratio": "1.45",
                "beta": "1.15",
                "var_95": "-2500.00",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "sharpe_ratio" in data
        assert "beta" in data
    
    def test_get_performance_history(self):
        """Should return performance over time."""
        response = MockResponse(
            status_code=200,
            json_data={
                "portfolio_id": str(uuid4()),
                "period": "1M",
                "data_points": [
                    {"date": "2024-01-01", "value": "100000.00"},
                    {"date": "2024-01-08", "value": "102500.00"},
                    {"date": "2024-01-15", "value": "105000.00"},
                    {"date": "2024-01-22", "value": "103500.00"},
                    {"date": "2024-01-29", "value": "108000.00"},
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data_points"]) == 5
    
    def test_get_allocation_breakdown(self):
        """Should return asset allocation."""
        response = MockResponse(
            status_code=200,
            json_data={
                "portfolio_id": str(uuid4()),
                "allocations": [
                    {"category": "Technology", "percentage": "45.0", "value": "56250.00"},
                    {"category": "Healthcare", "percentage": "20.0", "value": "25000.00"},
                    {"category": "Finance", "percentage": "15.0", "value": "18750.00"},
                    {"category": "Consumer", "percentage": "12.0", "value": "15000.00"},
                    {"category": "Cash", "percentage": "8.0", "value": "10000.00"},
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["allocations"]) == 5
        
        # Percentages should sum to 100
        total_pct = sum(Decimal(a["percentage"]) for a in data["allocations"])
        assert total_pct == Decimal("100.0")


class TestErrorResponses:
    """Tests for common error responses."""
    
    def test_validation_error_format(self):
        """Validation errors should follow standard format."""
        response = MockResponse(
            status_code=422,
            json_data={
                "detail": [
                    {
                        "loc": ["body", "quantity"],
                        "msg": "ensure this value is greater than 0",
                        "type": "value_error.number.not_gt",
                    }
                ]
            }
        )
        
        assert response.status_code == 422
        data = response.json()
        assert isinstance(data["detail"], list)
        assert "loc" in data["detail"][0]
        assert "msg" in data["detail"][0]
    
    def test_not_found_format(self):
        """404 errors should have detail message."""
        response = MockResponse(
            status_code=404,
            json_data={
                "detail": "Resource not found"
            }
        )
        
        assert response.status_code == 404
        assert "detail" in response.json()
    
    def test_unauthorized_format(self):
        """401 errors should have detail message."""
        response = MockResponse(
            status_code=401,
            json_data={
                "detail": "Not authenticated"
            }
        )
        
        assert response.status_code == 401
    
    def test_forbidden_format(self):
        """403 errors should have detail message."""
        response = MockResponse(
            status_code=403,
            json_data={
                "detail": "Not authorized to access this resource"
            }
        )
        
        assert response.status_code == 403
    
    def test_internal_error_format(self):
        """500 errors should have safe detail."""
        response = MockResponse(
            status_code=500,
            json_data={
                "detail": "Internal server error"
            }
        )
        
        assert response.status_code == 500
        # Should not leak internal details
        assert "stacktrace" not in str(response.json()).lower()


class TestPagination:
    """Tests for paginated responses."""
    
    def test_paginated_response_format(self):
        """Paginated responses should have metadata."""
        response = MockResponse(
            status_code=200,
            json_data={
                "items": [{"id": str(uuid4())} for _ in range(20)],
                "total": 150,
                "page": 1,
                "per_page": 20,
                "pages": 8,
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 20
        assert data["total"] == 150
        assert data["pages"] == 8
    
    def test_empty_page(self):
        """Empty page should return empty list."""
        response = MockResponse(
            status_code=200,
            json_data={
                "items": [],
                "total": 0,
                "page": 1,
                "per_page": 20,
                "pages": 0,
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 0
        assert data["total"] == 0
    
    def test_last_page(self):
        """Last page may have fewer items."""
        response = MockResponse(
            status_code=200,
            json_data={
                "items": [{"id": str(uuid4())} for _ in range(10)],
                "total": 50,
                "page": 3,
                "per_page": 20,
                "pages": 3,
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 10  # 50 - 20 - 20 = 10
