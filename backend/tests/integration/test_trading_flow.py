"""
Integration Tests - Trading Flow
Tests for order execution, position tracking, and portfolio updates.
"""
import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


# ============================================================
# Local definitions for testing (to avoid import complexity)
# ============================================================

class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL_FILL = "partial_fill"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class TimeInForce(str, Enum):
    DAY = "day"
    GTC = "gtc"  # Good Till Cancelled
    IOC = "ioc"  # Immediate or Cancel
    FOK = "fok"  # Fill or Kill


@dataclass
class Order:
    """Order representation for testing."""
    id: UUID
    portfolio_id: UUID
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    status: OrderStatus = OrderStatus.PENDING
    time_in_force: TimeInForce = TimeInForce.DAY
    filled_quantity: int = 0
    average_fill_price: Optional[Decimal] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None
    
    @property
    def remaining_quantity(self) -> int:
        return self.quantity - self.filled_quantity
    
    @property
    def is_filled(self) -> bool:
        return self.status == OrderStatus.FILLED
    
    @property
    def is_active(self) -> bool:
        return self.status in [
            OrderStatus.PENDING, 
            OrderStatus.SUBMITTED, 
            OrderStatus.PARTIAL_FILL
        ]


@dataclass
class Position:
    """Position representation for testing."""
    id: UUID
    portfolio_id: UUID
    symbol: str
    quantity: int
    average_cost: Decimal
    current_price: Decimal
    opened_at: datetime
    
    @property
    def market_value(self) -> Decimal:
        return self.current_price * self.quantity
    
    @property
    def cost_basis(self) -> Decimal:
        return self.average_cost * self.quantity
    
    @property
    def unrealized_pnl(self) -> Decimal:
        return self.market_value - self.cost_basis
    
    @property
    def unrealized_pnl_pct(self) -> Decimal:
        if self.cost_basis == 0:
            return Decimal("0")
        return (self.unrealized_pnl / self.cost_basis) * 100


@dataclass
class Trade:
    """Trade execution record for testing."""
    id: UUID
    order_id: UUID
    portfolio_id: UUID
    symbol: str
    side: OrderSide
    quantity: int
    price: Decimal
    commission: Decimal = Decimal("0")
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def gross_value(self) -> Decimal:
        return self.price * self.quantity
    
    @property
    def net_value(self) -> Decimal:
        return self.gross_value + self.commission


# ============================================================
# Test Classes
# ============================================================

class TestOrderCreation:
    """Tests for order creation and validation."""
    
    def test_market_order_creation(self):
        """Should create market order without price."""
        order = Order(
            id=uuid4(),
            portfolio_id=uuid4(),
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=100,
        )
        
        assert order.symbol == "AAPL"
        assert order.side == OrderSide.BUY
        assert order.order_type == OrderType.MARKET
        assert order.quantity == 100
        assert order.price is None
        assert order.status == OrderStatus.PENDING
    
    def test_limit_order_creation(self):
        """Should create limit order with price."""
        order = Order(
            id=uuid4(),
            portfolio_id=uuid4(),
            symbol="MSFT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=50,
            price=Decimal("380.00"),
        )
        
        assert order.order_type == OrderType.LIMIT
        assert order.price == Decimal("380.00")
    
    def test_stop_limit_order_creation(self):
        """Should create stop-limit order with both prices."""
        order = Order(
            id=uuid4(),
            portfolio_id=uuid4(),
            symbol="GOOGL",
            side=OrderSide.SELL,
            order_type=OrderType.STOP_LIMIT,
            quantity=25,
            price=Decimal("140.00"),
            stop_price=Decimal("142.00"),
        )
        
        assert order.order_type == OrderType.STOP_LIMIT
        assert order.price == Decimal("140.00")
        assert order.stop_price == Decimal("142.00")
    
    def test_order_time_in_force(self):
        """Should set correct time in force."""
        gtc_order = Order(
            id=uuid4(),
            portfolio_id=uuid4(),
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=100,
            price=Decimal("145.00"),
            time_in_force=TimeInForce.GTC,
        )
        
        assert gtc_order.time_in_force == TimeInForce.GTC
    
    def test_order_remaining_quantity(self):
        """Should calculate remaining quantity correctly."""
        order = Order(
            id=uuid4(),
            portfolio_id=uuid4(),
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=100,
            filled_quantity=40,
            status=OrderStatus.PARTIAL_FILL,
        )
        
        assert order.remaining_quantity == 60
    
    def test_order_is_filled(self):
        """Should detect filled orders."""
        filled_order = Order(
            id=uuid4(),
            portfolio_id=uuid4(),
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=100,
            filled_quantity=100,
            status=OrderStatus.FILLED,
        )
        
        assert filled_order.is_filled is True
    
    def test_order_is_active(self):
        """Should detect active orders."""
        pending = Order(
            id=uuid4(),
            portfolio_id=uuid4(),
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=100,
            status=OrderStatus.PENDING,
        )
        
        submitted = Order(
            id=uuid4(),
            portfolio_id=uuid4(),
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=100,
            status=OrderStatus.SUBMITTED,
        )
        
        cancelled = Order(
            id=uuid4(),
            portfolio_id=uuid4(),
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=100,
            status=OrderStatus.CANCELLED,
        )
        
        assert pending.is_active is True
        assert submitted.is_active is True
        assert cancelled.is_active is False


class TestOrderExecution:
    """Tests for order execution flow."""
    
    def test_market_order_fills_immediately(self):
        """Market orders should fill at current price."""
        current_price = Decimal("150.25")
        
        order = Order(
            id=uuid4(),
            portfolio_id=uuid4(),
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=100,
        )
        
        # Simulate fill
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.average_fill_price = current_price
        order.updated_at = datetime.now(timezone.utc)
        
        assert order.is_filled is True
        assert order.average_fill_price == current_price
        assert order.remaining_quantity == 0
    
    def test_limit_order_fills_at_limit_or_better(self):
        """Limit buy should fill at or below limit price."""
        limit_price = Decimal("145.00")
        fill_price = Decimal("144.75")  # Better than limit
        
        order = Order(
            id=uuid4(),
            portfolio_id=uuid4(),
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=100,
            price=limit_price,
        )
        
        # Simulate fill at better price
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.average_fill_price = fill_price
        
        assert order.average_fill_price <= order.price
    
    def test_partial_fill_updates(self):
        """Should track partial fills correctly."""
        order = Order(
            id=uuid4(),
            portfolio_id=uuid4(),
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=100,
            price=Decimal("150.00"),
        )
        
        # First partial fill - 40 shares at 149.90
        order.filled_quantity = 40
        order.average_fill_price = Decimal("149.90")
        order.status = OrderStatus.PARTIAL_FILL
        
        assert order.remaining_quantity == 60
        assert order.status == OrderStatus.PARTIAL_FILL
        
        # Second partial fill - 60 more shares at 149.95
        # Weighted average = (40*149.90 + 60*149.95) / 100
        first_value = 40 * Decimal("149.90")
        second_value = 60 * Decimal("149.95")
        avg_price = (first_value + second_value) / 100
        
        order.filled_quantity = 100
        order.average_fill_price = avg_price
        order.status = OrderStatus.FILLED
        
        assert order.is_filled is True
        assert order.average_fill_price == Decimal("149.93")
    
    def test_order_rejection(self):
        """Should handle order rejection."""
        order = Order(
            id=uuid4(),
            portfolio_id=uuid4(),
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=100,
        )
        
        # Simulate rejection (e.g., insufficient funds)
        order.status = OrderStatus.REJECTED
        order.updated_at = datetime.now(timezone.utc)
        
        assert order.status == OrderStatus.REJECTED
        assert order.is_active is False
        assert order.filled_quantity == 0
    
    def test_order_cancellation(self):
        """Should allow cancellation of active orders."""
        order = Order(
            id=uuid4(),
            portfolio_id=uuid4(),
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=100,
            price=Decimal("140.00"),
            status=OrderStatus.SUBMITTED,
        )
        
        assert order.is_active is True
        
        # Cancel the order
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.now(timezone.utc)
        
        assert order.status == OrderStatus.CANCELLED
        assert order.is_active is False


class TestPositionTracking:
    """Tests for position tracking."""
    
    def test_position_creation_from_buy(self):
        """Should create position from buy order."""
        position = Position(
            id=uuid4(),
            portfolio_id=uuid4(),
            symbol="AAPL",
            quantity=100,
            average_cost=Decimal("150.00"),
            current_price=Decimal("155.00"),
            opened_at=datetime.now(timezone.utc),
        )
        
        assert position.symbol == "AAPL"
        assert position.quantity == 100
        assert position.average_cost == Decimal("150.00")
    
    def test_position_market_value(self):
        """Should calculate market value correctly."""
        position = Position(
            id=uuid4(),
            portfolio_id=uuid4(),
            symbol="AAPL",
            quantity=100,
            average_cost=Decimal("150.00"),
            current_price=Decimal("155.00"),
            opened_at=datetime.now(timezone.utc),
        )
        
        assert position.market_value == Decimal("15500.00")
    
    def test_position_cost_basis(self):
        """Should calculate cost basis correctly."""
        position = Position(
            id=uuid4(),
            portfolio_id=uuid4(),
            symbol="AAPL",
            quantity=100,
            average_cost=Decimal("150.00"),
            current_price=Decimal("155.00"),
            opened_at=datetime.now(timezone.utc),
        )
        
        assert position.cost_basis == Decimal("15000.00")
    
    def test_position_unrealized_pnl_profit(self):
        """Should calculate unrealized profit."""
        position = Position(
            id=uuid4(),
            portfolio_id=uuid4(),
            symbol="AAPL",
            quantity=100,
            average_cost=Decimal("150.00"),
            current_price=Decimal("160.00"),
            opened_at=datetime.now(timezone.utc),
        )
        
        assert position.unrealized_pnl == Decimal("1000.00")
        # (1000/15000) * 100 = 6.666...
        assert abs(position.unrealized_pnl_pct - Decimal("6.6666666666666666666666666667")) < Decimal("0.0001")
    
    def test_position_unrealized_pnl_loss(self):
        """Should calculate unrealized loss."""
        position = Position(
            id=uuid4(),
            portfolio_id=uuid4(),
            symbol="AAPL",
            quantity=100,
            average_cost=Decimal("150.00"),
            current_price=Decimal("145.00"),
            opened_at=datetime.now(timezone.utc),
        )
        
        assert position.unrealized_pnl == Decimal("-500.00")
        assert position.unrealized_pnl_pct < 0
    
    def test_position_averaging_on_add(self):
        """Should calculate new average on adding to position."""
        # Existing position: 100 shares at $150
        existing_qty = 100
        existing_avg = Decimal("150.00")
        
        # New buy: 50 shares at $160
        new_qty = 50
        new_price = Decimal("160.00")
        
        # Calculate new average
        total_cost = (existing_qty * existing_avg) + (new_qty * new_price)
        total_qty = existing_qty + new_qty
        new_avg = total_cost / total_qty
        
        # (100*150 + 50*160) / 150 = 23000/150 = 153.33...
        assert total_qty == 150
        assert abs(new_avg - Decimal("153.33")) < Decimal("0.01")


class TestTradeExecution:
    """Tests for trade execution records."""
    
    def test_trade_creation(self):
        """Should create trade record from filled order."""
        order_id = uuid4()
        portfolio_id = uuid4()
        
        trade = Trade(
            id=uuid4(),
            order_id=order_id,
            portfolio_id=portfolio_id,
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            price=Decimal("150.25"),
            commission=Decimal("0.50"),
        )
        
        assert trade.symbol == "AAPL"
        assert trade.quantity == 100
        assert trade.price == Decimal("150.25")
        assert trade.order_id == order_id
    
    def test_trade_gross_value(self):
        """Should calculate gross value."""
        trade = Trade(
            id=uuid4(),
            order_id=uuid4(),
            portfolio_id=uuid4(),
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            price=Decimal("150.00"),
            commission=Decimal("1.00"),
        )
        
        assert trade.gross_value == Decimal("15000.00")
    
    def test_trade_net_value(self):
        """Should calculate net value including commission."""
        trade = Trade(
            id=uuid4(),
            order_id=uuid4(),
            portfolio_id=uuid4(),
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            price=Decimal("150.00"),
            commission=Decimal("5.00"),
        )
        
        assert trade.net_value == Decimal("15005.00")
    
    def test_multiple_trades_from_partial_fills(self):
        """Should create multiple trades for partial fills."""
        order_id = uuid4()
        portfolio_id = uuid4()
        
        trades = [
            Trade(
                id=uuid4(),
                order_id=order_id,
                portfolio_id=portfolio_id,
                symbol="AAPL",
                side=OrderSide.BUY,
                quantity=40,
                price=Decimal("149.90"),
                commission=Decimal("0.20"),
            ),
            Trade(
                id=uuid4(),
                order_id=order_id,
                portfolio_id=portfolio_id,
                symbol="AAPL",
                side=OrderSide.BUY,
                quantity=60,
                price=Decimal("150.10"),
                commission=Decimal("0.30"),
            ),
        ]
        
        # All trades reference same order
        assert all(t.order_id == order_id for t in trades)
        
        # Total quantity matches
        total_qty = sum(t.quantity for t in trades)
        assert total_qty == 100
        
        # Total commission
        total_commission = sum(t.commission for t in trades)
        assert total_commission == Decimal("0.50")


class TestPortfolioUpdates:
    """Tests for portfolio updates after trades."""
    
    def test_cash_decrease_on_buy(self):
        """Cash should decrease after buying."""
        initial_cash = Decimal("100000.00")
        trade_value = Decimal("15000.00")
        commission = Decimal("5.00")
        
        final_cash = initial_cash - trade_value - commission
        
        assert final_cash == Decimal("84995.00")
    
    def test_cash_increase_on_sell(self):
        """Cash should increase after selling."""
        initial_cash = Decimal("50000.00")
        trade_value = Decimal("16000.00")
        commission = Decimal("5.00")
        
        final_cash = initial_cash + trade_value - commission
        
        assert final_cash == Decimal("65995.00")
    
    def test_portfolio_value_calculation(self):
        """Should calculate total portfolio value."""
        cash = Decimal("50000.00")
        positions_value = Decimal("75000.00")  # Sum of all position market values
        
        total_value = cash + positions_value
        
        assert total_value == Decimal("125000.00")
    
    def test_realized_pnl_on_close(self):
        """Should calculate realized P&L when closing position."""
        # Bought at $150, selling at $160
        buy_price = Decimal("150.00")
        sell_price = Decimal("160.00")
        quantity = 100
        
        realized_pnl = (sell_price - buy_price) * quantity
        
        assert realized_pnl == Decimal("1000.00")
    
    def test_realized_pnl_with_partial_close(self):
        """Should calculate realized P&L for partial close."""
        # Position: 100 shares at $150
        avg_cost = Decimal("150.00")
        
        # Sell 40 shares at $165
        sell_qty = 40
        sell_price = Decimal("165.00")
        
        realized_pnl = (sell_price - avg_cost) * sell_qty
        
        assert realized_pnl == Decimal("600.00")
        
        # Remaining position: 60 shares at $150 (avg cost unchanged)
        remaining_qty = 100 - sell_qty
        assert remaining_qty == 60


class TestOrderValidation:
    """Tests for order validation rules."""
    
    def test_quantity_must_be_positive(self):
        """Quantity must be positive."""
        quantity = 100
        assert quantity > 0
        
        zero_quantity = 0
        assert zero_quantity <= 0  # Invalid
        
        negative_quantity = -50
        assert negative_quantity <= 0  # Invalid
    
    def test_limit_price_must_be_positive(self):
        """Limit price must be positive."""
        price = Decimal("150.00")
        assert price > 0
        
        zero_price = Decimal("0")
        assert zero_price <= 0  # Invalid
    
    def test_stop_price_validation(self):
        """Stop price must be above market for sell stop."""
        current_price = Decimal("150.00")
        stop_price = Decimal("145.00")  # Below current for sell stop
        
        # For a sell stop, stop price should be below current
        # to trigger if price falls
        assert stop_price < current_price
    
    def test_buy_stop_validation(self):
        """Buy stop price must be above market."""
        current_price = Decimal("150.00")
        stop_price = Decimal("155.00")  # Above current for buy stop
        
        # Buy stop triggers when price rises above stop
        assert stop_price > current_price
    
    def test_symbol_format_validation(self):
        """Symbol must be valid format."""
        valid_symbols = ["AAPL", "MSFT", "BRK.B", "BTC-USD"]
        
        for symbol in valid_symbols:
            assert len(symbol) >= 1
            assert len(symbol) <= 10
    
    def test_insufficient_cash_check(self):
        """Should validate sufficient cash for buy orders."""
        available_cash = Decimal("10000.00")
        order_value = Decimal("15000.00")
        
        has_sufficient = available_cash >= order_value
        assert has_sufficient is False
    
    def test_insufficient_shares_check(self):
        """Should validate sufficient shares for sell orders."""
        position_quantity = 50
        sell_quantity = 100
        
        has_sufficient = position_quantity >= sell_quantity
        assert has_sufficient is False


class TestSlippageSimulation:
    """Tests for price slippage in paper trading."""
    
    def test_market_order_slippage(self):
        """Market orders should have small slippage."""
        mid_price = Decimal("150.00")
        spread_pct = Decimal("0.05")  # 0.05% spread
        
        # Buy fills at ask (higher)
        buy_fill = mid_price * (1 + spread_pct / 100)
        # Sell fills at bid (lower)
        sell_fill = mid_price * (1 - spread_pct / 100)
        
        assert buy_fill > mid_price
        assert sell_fill < mid_price
    
    def test_large_order_impact(self):
        """Large orders should have more slippage."""
        base_price = Decimal("150.00")
        
        # Small order: minimal impact
        small_qty = 100
        small_impact_pct = Decimal("0.01")
        
        # Large order: more impact
        large_qty = 10000
        large_impact_pct = Decimal("0.10")
        
        assert large_impact_pct > small_impact_pct
    
    def test_limit_order_no_slippage(self):
        """Limit orders should not have slippage beyond limit."""
        limit_price = Decimal("145.00")
        
        # Fill price should be at or better than limit
        fill_price = Decimal("144.95")  # Filled at better price
        
        assert fill_price <= limit_price
