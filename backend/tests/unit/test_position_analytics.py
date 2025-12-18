"""
Unit Tests - Position Analytics Service
Tests for position analytics and audit helper functions.
"""
import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.position_analytics import (
    get_historical_cost_in_portfolio_currency,
    get_avg_entry_exchange_rate,
    get_position_cost_breakdown,
    calculate_forex_impact,
)
from app.db.models.trade import TradeType, TradeStatus


class TestGetHistoricalCostInPortfolioCurrency:
    """Tests for get_historical_cost_in_portfolio_currency function."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()
    
    @pytest.fixture
    def sample_trades(self):
        """Create sample trade objects."""
        trade1 = MagicMock()
        trade1.executed_price = Decimal("150.00")
        trade1.executed_quantity = Decimal("10")
        trade1.exchange_rate = Decimal("0.92")  # USD to EUR
        trade1.trade_type = TradeType.BUY
        trade1.status = TradeStatus.EXECUTED
        trade1.native_currency = "USD"
        trade1.executed_at = datetime.utcnow() - timedelta(days=30)
        
        trade2 = MagicMock()
        trade2.executed_price = Decimal("160.00")
        trade2.executed_quantity = Decimal("5")
        trade2.exchange_rate = Decimal("0.94")  # USD to EUR
        trade2.trade_type = TradeType.BUY
        trade2.status = TradeStatus.EXECUTED
        trade2.native_currency = "USD"
        trade2.executed_at = datetime.utcnow() - timedelta(days=15)
        
        return [trade1, trade2]
    
    @pytest.mark.asyncio
    async def test_calculate_historical_cost(self, mock_db, sample_trades):
        """Should calculate weighted average cost using historical FX rates."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = sample_trades
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result
        
        result = await get_historical_cost_in_portfolio_currency(mock_db, 1, "AAPL")
        
        # Trade 1: 150 * 10 * 0.92 = 1380 EUR
        # Trade 2: 160 * 5 * 0.94 = 752 EUR
        # Total: 2132 EUR / 15 shares = 142.13 EUR/share (approx)
        expected = (Decimal("1380") + Decimal("752")) / Decimal("15")
        assert result == expected
    
    @pytest.mark.asyncio
    async def test_no_trades_returns_zero(self, mock_db):
        """Should return 0 when no trades exist."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result
        
        result = await get_historical_cost_in_portfolio_currency(mock_db, 1, "AAPL")
        
        assert result == Decimal("0")
    
    @pytest.mark.asyncio
    async def test_handles_none_exchange_rate(self, mock_db):
        """Should use 1.0 as default when exchange_rate is None."""
        trade = MagicMock()
        trade.executed_price = Decimal("100.00")
        trade.executed_quantity = Decimal("10")
        trade.exchange_rate = None  # No FX rate stored
        trade.trade_type = TradeType.BUY
        trade.status = TradeStatus.EXECUTED
        
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [trade]
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result
        
        result = await get_historical_cost_in_portfolio_currency(mock_db, 1, "AAPL")
        
        # 100 * 10 * 1.0 / 10 = 100
        assert result == Decimal("100.00")


class TestGetAvgEntryExchangeRate:
    """Tests for get_avg_entry_exchange_rate function."""
    
    @pytest.fixture
    def mock_db(self):
        return AsyncMock()
    
    @pytest.fixture
    def sample_trades(self):
        """Create sample trades with different FX rates."""
        trade1 = MagicMock()
        trade1.executed_quantity = Decimal("10")
        trade1.exchange_rate = Decimal("0.90")
        
        trade2 = MagicMock()
        trade2.executed_quantity = Decimal("20")
        trade2.exchange_rate = Decimal("0.95")
        
        return [trade1, trade2]
    
    @pytest.mark.asyncio
    async def test_weighted_average_rate(self, mock_db, sample_trades):
        """Should calculate quantity-weighted average FX rate."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = sample_trades
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result
        
        result = await get_avg_entry_exchange_rate(mock_db, 1, "AAPL")
        
        # Weighted: (10 * 0.90 + 20 * 0.95) / 30 = (9 + 19) / 30 = 0.9333...
        expected = (Decimal("10") * Decimal("0.90") + Decimal("20") * Decimal("0.95")) / Decimal("30")
        assert result == expected
    
    @pytest.mark.asyncio
    async def test_no_trades_returns_one(self, mock_db):
        """Should return 1.0 when no trades exist."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result
        
        result = await get_avg_entry_exchange_rate(mock_db, 1, "AAPL")
        
        assert result == Decimal("1.0")
    
    @pytest.mark.asyncio
    async def test_handles_none_exchange_rate(self, mock_db):
        """Should use 1.0 for trades without FX rate."""
        trade = MagicMock()
        trade.executed_quantity = Decimal("10")
        trade.exchange_rate = None
        
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [trade]
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result
        
        result = await get_avg_entry_exchange_rate(mock_db, 1, "AAPL")
        
        assert result == Decimal("1.0")


class TestGetPositionCostBreakdown:
    """Tests for get_position_cost_breakdown function."""
    
    @pytest.fixture
    def mock_db(self):
        return AsyncMock()
    
    @pytest.fixture
    def sample_trades(self):
        """Create sample trades for breakdown."""
        trade1 = MagicMock()
        trade1.executed_price = Decimal("100.00")
        trade1.executed_quantity = Decimal("10")
        trade1.exchange_rate = Decimal("0.92")
        trade1.native_currency = "USD"
        trade1.executed_at = datetime.utcnow()
        
        trade2 = MagicMock()
        trade2.executed_price = Decimal("110.00")
        trade2.executed_quantity = Decimal("10")
        trade2.exchange_rate = Decimal("0.94")
        trade2.native_currency = "USD"
        trade2.executed_at = datetime.utcnow()
        
        return [trade1, trade2]
    
    @pytest.mark.asyncio
    async def test_breakdown_structure(self, mock_db, sample_trades):
        """Should return complete breakdown structure."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = sample_trades
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result
        
        result = await get_position_cost_breakdown(mock_db, 1, "AAPL")
        
        assert "symbol" in result
        assert "total_quantity" in result
        assert "avg_cost_native" in result
        assert "avg_cost_portfolio" in result
        assert "avg_entry_fx_rate" in result
        assert "total_cost_native" in result
        assert "total_cost_portfolio" in result
        assert "trades_count" in result
        assert "native_currency" in result
    
    @pytest.mark.asyncio
    async def test_breakdown_calculations(self, mock_db, sample_trades):
        """Should calculate all values correctly."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = sample_trades
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result
        
        result = await get_position_cost_breakdown(mock_db, 1, "aapl")
        
        assert result["symbol"] == "AAPL"  # Uppercase
        assert result["total_quantity"] == Decimal("20")
        assert result["trades_count"] == 2
        assert result["native_currency"] == "USD"
        
        # Total native: 100*10 + 110*10 = 2100
        assert result["total_cost_native"] == Decimal("2100")
        
        # Total portfolio: 100*10*0.92 + 110*10*0.94 = 920 + 1034 = 1954
        assert result["total_cost_portfolio"] == Decimal("1954")
        
        # Avg native: 2100 / 20 = 105
        assert result["avg_cost_native"] == Decimal("105")
        
        # Avg portfolio: 1954 / 20 = 97.7
        assert result["avg_cost_portfolio"] == Decimal("97.7")
    
    @pytest.mark.asyncio
    async def test_empty_position(self, mock_db):
        """Should return zeros for position with no trades."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result
        
        result = await get_position_cost_breakdown(mock_db, 1, "AAPL")
        
        assert result["total_quantity"] == Decimal("0")
        assert result["avg_cost_native"] == Decimal("0")
        assert result["trades_count"] == 0
        assert result["native_currency"] is None


class TestCalculateForexImpact:
    """Tests for calculate_forex_impact function."""
    
    @pytest.fixture
    def mock_db(self):
        return AsyncMock()
    
    @pytest.mark.asyncio
    async def test_forex_impact_calculation(self, mock_db):
        """Should calculate forex impact correctly."""
        # Mock the breakdown function
        mock_breakdown = {
            "symbol": "AAPL",
            "total_quantity": Decimal("100"),
            "avg_cost_native": Decimal("150.00"),
            "avg_cost_portfolio": Decimal("138.00"),  # Entry rate 0.92
            "avg_entry_fx_rate": Decimal("0.92"),
            "total_cost_native": Decimal("15000"),
            "total_cost_portfolio": Decimal("13800"),
            "trades_count": 1,
            "native_currency": "USD",
        }
        
        with patch('app.services.position_analytics.get_position_cost_breakdown', 
                   return_value=mock_breakdown):
            result = await calculate_forex_impact(
                mock_db, 1, "AAPL", 
                current_fx_rate=Decimal("0.95")  # Rate improved
            )
        
        assert result["symbol"] == "AAPL"
        assert result["avg_entry_fx_rate"] == Decimal("0.92")
        assert result["current_fx_rate"] == Decimal("0.95")
        
        # FX change: (0.95 - 0.92) / 0.92 * 100 = 3.26%
        expected_pct = (Decimal("0.95") - Decimal("0.92")) / Decimal("0.92") * 100
        assert result["fx_change_percent"] == expected_pct
        
        # Impact per share: 150 * (0.95 - 0.92) = 4.50
        expected_impact_per_share = Decimal("150.00") * (Decimal("0.95") - Decimal("0.92"))
        assert result["fx_impact_per_share"] == expected_impact_per_share
        
        # Total impact: 4.50 * 100 = 450
        expected_total = expected_impact_per_share * Decimal("100")
        assert result["total_fx_impact"] == expected_total
    
    @pytest.mark.asyncio
    async def test_forex_impact_empty_position(self, mock_db):
        """Should return zeros for empty position."""
        mock_breakdown = {
            "symbol": "AAPL",
            "total_quantity": Decimal("0"),
            "avg_cost_native": Decimal("0"),
            "avg_cost_portfolio": Decimal("0"),
            "avg_entry_fx_rate": Decimal("1.0"),
            "total_cost_native": Decimal("0"),
            "total_cost_portfolio": Decimal("0"),
            "trades_count": 0,
            "native_currency": None,
        }
        
        with patch('app.services.position_analytics.get_position_cost_breakdown', 
                   return_value=mock_breakdown):
            result = await calculate_forex_impact(
                mock_db, 1, "AAPL",
                current_fx_rate=Decimal("0.95")
            )
        
        assert result["total_fx_impact"] == Decimal("0")
        assert result["fx_change_percent"] == Decimal("0")
    
    @pytest.mark.asyncio
    async def test_forex_negative_impact(self, mock_db):
        """Should correctly calculate negative forex impact."""
        mock_breakdown = {
            "symbol": "AAPL",
            "total_quantity": Decimal("50"),
            "avg_cost_native": Decimal("200.00"),
            "avg_cost_portfolio": Decimal("190.00"),
            "avg_entry_fx_rate": Decimal("0.95"),
            "total_cost_native": Decimal("10000"),
            "total_cost_portfolio": Decimal("9500"),
            "trades_count": 1,
            "native_currency": "USD",
        }
        
        with patch('app.services.position_analytics.get_position_cost_breakdown', 
                   return_value=mock_breakdown):
            result = await calculate_forex_impact(
                mock_db, 1, "AAPL",
                current_fx_rate=Decimal("0.90")  # Rate worsened
            )
        
        # Rate decreased from 0.95 to 0.90 = negative impact
        assert result["fx_change_percent"] < 0
        assert result["total_fx_impact"] < 0
        
        # Impact per share: 200 * (0.90 - 0.95) = -10
        expected = Decimal("200.00") * (Decimal("0.90") - Decimal("0.95"))
        assert result["fx_impact_per_share"] == expected


class TestEdgeCases:
    """Edge case tests for position analytics."""
    
    @pytest.fixture
    def mock_db(self):
        return AsyncMock()
    
    @pytest.mark.asyncio
    async def test_symbol_case_normalization(self, mock_db):
        """Should normalize symbol to uppercase."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result
        
        result = await get_position_cost_breakdown(mock_db, 1, "aapl")
        
        assert result["symbol"] == "AAPL"
    
    @pytest.mark.asyncio
    async def test_zero_quantity_handling(self, mock_db):
        """Should handle zero quantity without division error."""
        trade = MagicMock()
        trade.executed_price = Decimal("100.00")
        trade.executed_quantity = Decimal("0")  # Zero quantity
        trade.exchange_rate = Decimal("0.92")
        trade.native_currency = "USD"
        trade.executed_at = datetime.utcnow()
        
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [trade]
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result
        
        # Should not raise ZeroDivisionError
        result = await get_position_cost_breakdown(mock_db, 1, "AAPL")
        
        assert result["avg_cost_native"] == Decimal("0")
    
    @pytest.mark.asyncio
    async def test_very_small_amounts(self, mock_db):
        """Should handle very small decimal amounts."""
        trade = MagicMock()
        trade.executed_price = Decimal("0.0001")  # Very small price
        trade.executed_quantity = Decimal("1000000")  # Large quantity
        trade.exchange_rate = Decimal("0.92")
        trade.native_currency = "USD"
        trade.executed_at = datetime.utcnow()
        
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [trade]
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result
        
        result = await get_position_cost_breakdown(mock_db, 1, "DOGE")
        
        assert result["avg_cost_native"] == Decimal("0.0001")
        assert result["total_cost_native"] == Decimal("100")  # 0.0001 * 1000000
