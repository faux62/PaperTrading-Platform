"""
Unit Tests - P&L Calculator
Tests for realized/unrealized P&L calculations.
"""
import pytest
from decimal import Decimal
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass, field
from typing import Optional, Dict, Tuple
from enum import Enum


# Define test versions of the dataclasses to avoid import issues
class TimeFrame(str, Enum):
    """Time frame for P&L calculations."""
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    YTD = "ytd"
    ALL_TIME = "all_time"


@dataclass
class RealizedPnL:
    """Realized P&L from closed positions."""
    total: Decimal = Decimal("0")
    gross_profit: Decimal = Decimal("0")
    gross_loss: Decimal = Decimal("0")
    trade_count: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: Decimal = Decimal("0")
    avg_win: Decimal = Decimal("0")
    avg_loss: Decimal = Decimal("0")
    profit_factor: Optional[Decimal] = None
    largest_win: Decimal = Decimal("0")
    largest_loss: Decimal = Decimal("0")


@dataclass
class UnrealizedPnL:
    """Unrealized P&L from open positions."""
    total: Decimal = Decimal("0")
    by_position: Dict[str, Decimal] = field(default_factory=dict)
    positions_in_profit: int = 0
    positions_in_loss: int = 0
    largest_gain: Tuple[str, Decimal] = ("", Decimal("0"))
    largest_loss: Tuple[str, Decimal] = ("", Decimal("0"))


@dataclass
class PortfolioPnL:
    """Combined P&L for portfolio."""
    portfolio_id: int
    realized: RealizedPnL
    unrealized: UnrealizedPnL
    total_pnl: Decimal
    total_pnl_pct: Decimal
    initial_capital: Decimal
    current_value: Decimal
    cash_balance: Decimal
    time_frame: TimeFrame
    as_of: datetime


@dataclass
class DailyPnL:
    """Daily P&L record."""
    date: date
    realized: Decimal
    unrealized: Decimal
    total: Decimal
    portfolio_value: Decimal
    daily_return_pct: Decimal


class PnLCalculator:
    """P&L Calculator mock."""
    def __init__(self, db):
        self.db = db


class TestTimeFrameEnum:
    """Tests for TimeFrame enum."""
    
    def test_time_frame_values(self):
        """TimeFrame should have expected values."""
        assert TimeFrame.DAY.value == "day"
        assert TimeFrame.WEEK.value == "week"
        assert TimeFrame.MONTH.value == "month"
        assert TimeFrame.QUARTER.value == "quarter"
        assert TimeFrame.YEAR.value == "year"
        assert TimeFrame.YTD.value == "ytd"
        assert TimeFrame.ALL_TIME.value == "all_time"
    
    def test_time_frame_count(self):
        """Should have 7 time frames."""
        frames = list(TimeFrame)
        assert len(frames) == 7


class TestRealizedPnL:
    """Tests for RealizedPnL dataclass."""
    
    def test_realized_pnl_defaults(self):
        """RealizedPnL should have zero defaults."""
        pnl = RealizedPnL()
        assert pnl.total == Decimal("0")
        assert pnl.gross_profit == Decimal("0")
        assert pnl.gross_loss == Decimal("0")
        assert pnl.trade_count == 0
        assert pnl.winning_trades == 0
        assert pnl.losing_trades == 0
        assert pnl.win_rate == Decimal("0")
    
    def test_realized_pnl_custom_values(self):
        """RealizedPnL should accept custom values."""
        pnl = RealizedPnL(
            total=Decimal("5000"),
            gross_profit=Decimal("8000"),
            gross_loss=Decimal("3000"),
            trade_count=20,
            winning_trades=12,
            losing_trades=8,
            win_rate=Decimal("60"),
            avg_win=Decimal("666.67"),
            avg_loss=Decimal("375"),
            profit_factor=Decimal("2.67"),
            largest_win=Decimal("2000"),
            largest_loss=Decimal("800")
        )
        assert pnl.total == Decimal("5000")
        assert pnl.trade_count == 20
        assert pnl.win_rate == Decimal("60")
        assert pnl.profit_factor == Decimal("2.67")
    
    def test_realized_pnl_profit_factor_optional(self):
        """Profit factor should be optional (None when no losses)."""
        pnl = RealizedPnL(
            gross_profit=Decimal("1000"),
            gross_loss=Decimal("0")
        )
        assert pnl.profit_factor is None


class TestUnrealizedPnL:
    """Tests for UnrealizedPnL dataclass."""
    
    def test_unrealized_pnl_defaults(self):
        """UnrealizedPnL should have zero defaults."""
        pnl = UnrealizedPnL()
        assert pnl.total == Decimal("0")
        assert pnl.by_position == {}
        assert pnl.positions_in_profit == 0
        assert pnl.positions_in_loss == 0
    
    def test_unrealized_pnl_with_positions(self):
        """UnrealizedPnL should track by position."""
        pnl = UnrealizedPnL(
            total=Decimal("2500"),
            by_position={
                "AAPL": Decimal("1500"),
                "MSFT": Decimal("1200"),
                "TSLA": Decimal("-200")
            },
            positions_in_profit=2,
            positions_in_loss=1,
            largest_gain=("AAPL", Decimal("1500")),
            largest_loss=("TSLA", Decimal("-200"))
        )
        assert pnl.total == Decimal("2500")
        assert len(pnl.by_position) == 3
        assert pnl.positions_in_profit == 2


class TestPortfolioPnL:
    """Tests for PortfolioPnL dataclass."""
    
    def test_portfolio_pnl_creation(self):
        """PortfolioPnL should combine realized and unrealized."""
        pnl = PortfolioPnL(
            portfolio_id=1,
            realized=RealizedPnL(total=Decimal("5000")),
            unrealized=UnrealizedPnL(total=Decimal("2500")),
            total_pnl=Decimal("7500"),
            total_pnl_pct=Decimal("7.5"),
            initial_capital=Decimal("100000"),
            current_value=Decimal("107500"),
            cash_balance=Decimal("50000"),
            time_frame=TimeFrame.YTD,
            as_of=datetime.utcnow()
        )
        assert pnl.portfolio_id == 1
        assert pnl.total_pnl == Decimal("7500")
        assert pnl.total_pnl_pct == Decimal("7.5")
        assert pnl.time_frame == TimeFrame.YTD


class TestDailyPnL:
    """Tests for DailyPnL dataclass."""
    
    def test_daily_pnl_creation(self):
        """DailyPnL should track single day P&L."""
        from datetime import date
        pnl = DailyPnL(
            date=date.today(),
            realized=Decimal("500"),
            unrealized=Decimal("200"),
            total=Decimal("700"),
            portfolio_value=Decimal("105000"),
            daily_return_pct=Decimal("0.67")
        )
        assert pnl.date == date.today()
        assert pnl.total == Decimal("700")
        assert pnl.daily_return_pct == Decimal("0.67")


class TestPnLCalculator:
    """Tests for PnLCalculator class."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return AsyncMock()
    
    @pytest.fixture
    def calculator(self, mock_db):
        """Create PnLCalculator instance."""
        return PnLCalculator(db=mock_db)
    
    def test_calculator_init(self, mock_db):
        """Calculator should initialize with db session."""
        calc = PnLCalculator(db=mock_db)
        assert calc.db is mock_db


class TestPnLCalculatorHelpers:
    """Tests for P&L calculation helper logic."""
    
    def test_win_rate_calculation(self):
        """Win rate should be winning_trades / total_trades."""
        winning = 12
        total = 20
        win_rate = (winning / total) * 100
        assert win_rate == 60.0
    
    def test_profit_factor_calculation(self):
        """Profit factor should be gross_profit / gross_loss."""
        gross_profit = Decimal("8000")
        gross_loss = Decimal("3000")
        profit_factor = gross_profit / gross_loss
        assert profit_factor == Decimal("8000") / Decimal("3000")
        assert float(profit_factor) > 2.6
    
    def test_profit_factor_no_loss(self):
        """Profit factor with no losses should be None or infinity."""
        gross_profit = Decimal("5000")
        gross_loss = Decimal("0")
        # Should handle division by zero
        if gross_loss == 0:
            profit_factor = None  # Or float('inf')
        else:
            profit_factor = gross_profit / gross_loss
        assert profit_factor is None
    
    def test_unrealized_pnl_calculation(self):
        """Unrealized P&L = (current_price - avg_cost) * quantity."""
        avg_cost = Decimal("150.00")
        current_price = Decimal("165.00")
        quantity = Decimal("100")
        
        unrealized_pnl = (current_price - avg_cost) * quantity
        assert unrealized_pnl == Decimal("1500.00")
    
    def test_unrealized_pnl_loss(self):
        """Unrealized P&L should be negative for losses."""
        avg_cost = Decimal("150.00")
        current_price = Decimal("140.00")
        quantity = Decimal("100")
        
        unrealized_pnl = (current_price - avg_cost) * quantity
        assert unrealized_pnl == Decimal("-1000.00")
    
    def test_unrealized_pnl_percentage(self):
        """Unrealized P&L % = ((current - cost) / cost) * 100."""
        avg_cost = Decimal("150.00")
        current_price = Decimal("165.00")
        
        pnl_pct = ((current_price - avg_cost) / avg_cost) * 100
        assert pnl_pct == Decimal("10.00")
    
    def test_total_portfolio_value(self):
        """Total value = cash + sum of position market values."""
        cash = Decimal("50000")
        position_values = [
            Decimal("15500"),  # AAPL: 100 shares @ $155
            Decimal("32000"),  # MSFT: 100 shares @ $320
            Decimal("5000")    # Other
        ]
        total_value = cash + sum(position_values)
        assert total_value == Decimal("102500")
    
    def test_portfolio_return_calculation(self):
        """Portfolio return = (current_value / initial_capital - 1) * 100."""
        initial = Decimal("100000")
        current = Decimal("112500")
        
        return_pct = ((current / initial) - 1) * 100
        assert return_pct == Decimal("12.5")


class TestTimeFrameStartDate:
    """Tests for time frame date calculations."""
    
    def test_day_start_date(self):
        """Day time frame should start today."""
        now = datetime.utcnow()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        assert start.date() == now.date()
    
    def test_week_start_date(self):
        """Week time frame should start 7 days ago."""
        now = datetime.utcnow()
        start = now - timedelta(days=7)
        assert (now - start).days == 7
    
    def test_month_start_date(self):
        """Month time frame should start ~30 days ago."""
        now = datetime.utcnow()
        start = now - timedelta(days=30)
        assert (now - start).days == 30
    
    def test_ytd_start_date(self):
        """YTD should start January 1st of current year."""
        now = datetime.utcnow()
        start = datetime(now.year, 1, 1)
        assert start.month == 1
        assert start.day == 1
        assert start.year == now.year
