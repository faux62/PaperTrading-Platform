"""
PaperTrading Platform - Test Configuration
Shared fixtures and test configuration.
"""
import os
import sys
from typing import Generator, AsyncGenerator
from datetime import datetime, timedelta
from decimal import Decimal
import pytest
from unittest.mock import AsyncMock, MagicMock

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test environment
os.environ["APP_ENV"] = "testing"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key"
os.environ["POSTGRES_HOST"] = "localhost"
os.environ["POSTGRES_DB"] = "papertrading_test"


# =========================
# User Fixtures
# =========================

@pytest.fixture
def sample_user_data() -> dict:
    """Sample user registration data."""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "SecurePassword123!",
        "full_name": "Test User"
    }


@pytest.fixture
def sample_user():
    """Sample user object mock."""
    from app.db.models.user import User
    user = MagicMock(spec=User)
    user.id = 1
    user.email = "test@example.com"
    user.username = "testuser"
    user.hashed_password = "$2b$12$test_hashed_password"
    user.full_name = "Test User"
    user.is_active = True
    user.is_superuser = False
    user.created_at = datetime.utcnow()
    user.updated_at = datetime.utcnow()
    return user


# =========================
# Portfolio Fixtures
# =========================

@pytest.fixture
def sample_portfolio_data() -> dict:
    """Sample portfolio creation data."""
    return {
        "name": "Test Portfolio",
        "description": "A test portfolio for unit testing",
        "risk_profile": "balanced",
        "initial_capital": 100000.00,
        "currency": "USD"
    }


@pytest.fixture
def sample_portfolio():
    """Sample portfolio object mock."""
    from app.db.models.portfolio import Portfolio, RiskProfile
    portfolio = MagicMock(spec=Portfolio)
    portfolio.id = 1
    portfolio.user_id = 1
    portfolio.name = "Test Portfolio"
    portfolio.description = "A test portfolio"
    portfolio.risk_profile = RiskProfile.BALANCED
    portfolio.initial_capital = Decimal("100000.00")
    portfolio.cash_balance = Decimal("100000.00")
    portfolio.currency = "USD"
    portfolio.is_active = "active"
    portfolio.created_at = datetime.utcnow()
    portfolio.updated_at = datetime.utcnow()
    return portfolio


# =========================
# Trade Fixtures
# =========================

@pytest.fixture
def sample_trade_data() -> dict:
    """Sample trade data."""
    return {
        "symbol": "AAPL",
        "trade_type": "buy",
        "order_type": "market",
        "quantity": 10,
        "price": None
    }


@pytest.fixture
def sample_trade():
    """Sample trade object mock."""
    from app.db.models.trade import Trade, TradeType, OrderType, TradeStatus
    trade = MagicMock(spec=Trade)
    trade.id = 1
    trade.portfolio_id = 1
    trade.symbol = "AAPL"
    trade.exchange = "NASDAQ"
    trade.trade_type = TradeType.BUY
    trade.order_type = OrderType.MARKET
    trade.status = TradeStatus.EXECUTED
    trade.quantity = Decimal("10")
    trade.price = None
    trade.executed_price = Decimal("150.00")
    trade.executed_quantity = Decimal("10")
    trade.total_value = Decimal("1500.00")
    trade.commission = Decimal("0")
    trade.created_at = datetime.utcnow()
    trade.executed_at = datetime.utcnow()
    return trade


# =========================
# Position Fixtures
# =========================

@pytest.fixture
def sample_position():
    """Sample position object mock."""
    from app.db.models.position import Position
    position = MagicMock(spec=Position)
    position.id = 1
    position.portfolio_id = 1
    position.symbol = "AAPL"
    position.quantity = Decimal("10")
    position.avg_cost = Decimal("150.00")
    position.current_price = Decimal("155.00")
    position.market_value = Decimal("1550.00")
    position.unrealized_pnl = Decimal("50.00")
    position.unrealized_pnl_pct = Decimal("3.33")
    return position


# =========================
# Market Data Fixtures
# =========================

@pytest.fixture
def sample_quote() -> dict:
    """Sample stock quote data."""
    return {
        "symbol": "AAPL",
        "price": 150.00,
        "change": 2.50,
        "change_percent": 1.69,
        "volume": 50000000,
        "open": 148.00,
        "high": 151.00,
        "low": 147.50,
        "prev_close": 147.50,
        "timestamp": datetime.utcnow().isoformat()
    }


@pytest.fixture
def sample_historical_data() -> list:
    """Sample historical price data."""
    base_date = datetime.utcnow()
    return [
        {
            "date": (base_date - timedelta(days=i)).strftime("%Y-%m-%d"),
            "open": 148.0 + i * 0.5,
            "high": 151.0 + i * 0.5,
            "low": 147.0 + i * 0.5,
            "close": 150.0 + i * 0.5,
            "volume": 50000000 + i * 100000
        }
        for i in range(30)
    ]


# =========================
# Database Mocks
# =========================

@pytest.fixture
def mock_db_session():
    """Mock async database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.delete = MagicMock()
    return session


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=True)
    redis.exists = AsyncMock(return_value=False)
    redis.expire = AsyncMock(return_value=True)
    return redis


# =========================
# API Client Fixtures
# =========================

@pytest.fixture
def mock_httpx_client():
    """Mock httpx async client."""
    client = AsyncMock()
    client.get = AsyncMock()
    client.post = AsyncMock()
    return client


# =========================
# Settings Override
# =========================

@pytest.fixture
def test_settings():
    """Test settings override."""
    from app.config import Settings
    return Settings(
        APP_ENV="testing",
        DEBUG=True,
        SECRET_KEY="test-secret-key",
        JWT_SECRET_KEY="test-jwt-secret-key",
        POSTGRES_HOST="localhost",
        POSTGRES_DB="papertrading_test",
        REDIS_HOST="localhost",
        ACCESS_TOKEN_EXPIRE_MINUTES=30,
        REFRESH_TOKEN_EXPIRE_DAYS=7
    )


# =========================
# Authentication Fixtures
# =========================

@pytest.fixture
def valid_access_token(sample_user) -> str:
    """Generate a valid access token for testing."""
    from app.core.security import create_access_token
    token, _ = create_access_token(subject=str(sample_user.id))
    return token


@pytest.fixture
def expired_access_token(sample_user) -> str:
    """Generate an expired access token for testing."""
    from app.core.security import create_access_token
    from datetime import timedelta
    token, _ = create_access_token(
        subject=str(sample_user.id),
        expires_delta=timedelta(seconds=-1)  # Already expired
    )
    return token
