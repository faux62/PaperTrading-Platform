"""
Unit Tests - Database Models
Tests for SQLAlchemy models structure and enums.
"""
import pytest
from decimal import Decimal
from datetime import datetime

from app.db.models.user import User
from app.db.models.portfolio import Portfolio, RiskProfile
from app.db.models.trade import Trade, TradeType, OrderType, TradeStatus
from app.db.models.position import Position


class TestUserModel:
    """Tests for User model."""
    
    def test_user_model_attributes(self):
        """User model should have all expected attributes."""
        assert hasattr(User, 'id')
        assert hasattr(User, 'email')
        assert hasattr(User, 'username')
        assert hasattr(User, 'hashed_password')
        assert hasattr(User, 'full_name')
        assert hasattr(User, 'is_active')
        assert hasattr(User, 'is_superuser')
        assert hasattr(User, 'created_at')
        assert hasattr(User, 'updated_at')
        assert hasattr(User, 'last_login')
    
    def test_user_relationships(self):
        """User model should have relationships defined."""
        assert hasattr(User, 'portfolios')
        assert hasattr(User, 'watchlists')
        assert hasattr(User, 'alerts')
    
    def test_user_tablename(self):
        """User model should have correct tablename."""
        assert User.__tablename__ == "users"


class TestRiskProfileEnum:
    """Tests for RiskProfile enum."""
    
    def test_risk_profile_values(self):
        """RiskProfile should have expected values."""
        assert RiskProfile.AGGRESSIVE.value == "aggressive"
        assert RiskProfile.BALANCED.value == "balanced"
        assert RiskProfile.PRUDENT.value == "prudent"
    
    def test_risk_profile_count(self):
        """RiskProfile should have exactly 3 options."""
        profiles = list(RiskProfile)
        assert len(profiles) == 3
    
    def test_risk_profile_is_string_enum(self):
        """RiskProfile should be string enum."""
        assert issubclass(RiskProfile, str)


class TestPortfolioModel:
    """Tests for Portfolio model."""
    
    def test_portfolio_model_attributes(self):
        """Portfolio model should have all expected attributes."""
        assert hasattr(Portfolio, 'id')
        assert hasattr(Portfolio, 'user_id')
        assert hasattr(Portfolio, 'name')
        assert hasattr(Portfolio, 'description')
        assert hasattr(Portfolio, 'risk_profile')
        assert hasattr(Portfolio, 'initial_capital')
        assert hasattr(Portfolio, 'cash_balance')
        assert hasattr(Portfolio, 'currency')
        assert hasattr(Portfolio, 'is_active')
        assert hasattr(Portfolio, 'created_at')
        assert hasattr(Portfolio, 'updated_at')
    
    def test_portfolio_relationships(self):
        """Portfolio model should have relationships defined."""
        assert hasattr(Portfolio, 'user')
        assert hasattr(Portfolio, 'positions')
        assert hasattr(Portfolio, 'trades')
    
    def test_portfolio_tablename(self):
        """Portfolio model should have correct tablename."""
        assert Portfolio.__tablename__ == "portfolios"


class TestTradeTypeEnum:
    """Tests for TradeType enum."""
    
    def test_trade_type_values(self):
        """TradeType should have expected values."""
        assert TradeType.BUY.value == "buy"
        assert TradeType.SELL.value == "sell"
    
    def test_trade_type_count(self):
        """TradeType should have exactly 2 options."""
        types = list(TradeType)
        assert len(types) == 2


class TestOrderTypeEnum:
    """Tests for OrderType enum."""
    
    def test_order_type_values(self):
        """OrderType should have expected values."""
        assert OrderType.MARKET.value == "market"
        assert OrderType.LIMIT.value == "limit"
        assert OrderType.STOP.value == "stop"
        assert OrderType.STOP_LIMIT.value == "stop_limit"
    
    def test_order_type_count(self):
        """OrderType should have exactly 4 options."""
        types = list(OrderType)
        assert len(types) == 4


class TestTradeStatusEnum:
    """Tests for TradeStatus enum."""
    
    def test_trade_status_values(self):
        """TradeStatus should have expected values."""
        assert TradeStatus.PENDING.value == "pending"
        assert TradeStatus.EXECUTED.value == "executed"
        assert TradeStatus.CANCELLED.value == "cancelled"
        assert TradeStatus.FAILED.value == "failed"
    
    def test_trade_status_count(self):
        """TradeStatus should have exactly 4 options."""
        statuses = list(TradeStatus)
        assert len(statuses) == 4


class TestTradeModel:
    """Tests for Trade model."""
    
    def test_trade_model_attributes(self):
        """Trade model should have all expected attributes."""
        assert hasattr(Trade, 'id')
        assert hasattr(Trade, 'portfolio_id')
        assert hasattr(Trade, 'symbol')
        assert hasattr(Trade, 'exchange')
        assert hasattr(Trade, 'trade_type')
        assert hasattr(Trade, 'order_type')
        assert hasattr(Trade, 'status')
        assert hasattr(Trade, 'quantity')
        assert hasattr(Trade, 'price')
        assert hasattr(Trade, 'executed_price')
        assert hasattr(Trade, 'executed_quantity')
        assert hasattr(Trade, 'total_value')
        assert hasattr(Trade, 'commission')
        assert hasattr(Trade, 'realized_pnl')
        assert hasattr(Trade, 'created_at')
        assert hasattr(Trade, 'executed_at')
        assert hasattr(Trade, 'notes')
    
    def test_trade_relationships(self):
        """Trade model should have relationships defined."""
        assert hasattr(Trade, 'portfolio')
    
    def test_trade_tablename(self):
        """Trade model should have correct tablename."""
        assert Trade.__tablename__ == "trades"


class TestPositionModel:
    """Tests for Position model."""
    
    def test_position_model_attributes(self):
        """Position model should have expected attributes."""
        assert hasattr(Position, 'id')
        assert hasattr(Position, 'portfolio_id')
        assert hasattr(Position, 'symbol')
    
    def test_position_relationships(self):
        """Position model should have relationships defined."""
        assert hasattr(Position, 'portfolio')
    
    def test_position_tablename(self):
        """Position model should have correct tablename."""
        assert Position.__tablename__ == "positions"
