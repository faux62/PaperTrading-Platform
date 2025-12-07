"""
Phase 3: Trading Simulato - Unit Tests
======================================

Test IDs: SIM-01 to SIM-07
Tests the simulated trading execution engine for realistic behavior.

Run with:
    pytest tests/unit/test_trading_simulation.py -v

Requirements:
    SIM-01: Market order executed at realistic price
    SIM-02: Limit order executed only when price reached
    SIM-03: Realistic bid/ask spread simulation
    SIM-04: Slippage simulated on large orders
    SIM-05: Order rejected if insufficient capital
    SIM-06: Partial fill on limit orders
    SIM-07: Commission calculation
"""
import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.core.trading.execution import (
    ExecutionEngine,
    SlippageConfig,
    BidAskSpreadConfig,
    CommissionConfig,
    MarketCondition,
    ExecutionResult
)
from app.core.trading.order_manager import (
    OrderManager,
    OrderRequest,
    OrderValidationError,
    InsufficientFundsError
)
from app.db.models.trade import Trade, TradeType, OrderType, TradeStatus
from app.db.models.portfolio import Portfolio


class TestSIM01MarketOrderExecution:
    """
    SIM-01: Market order executed at realistic price
    
    Verifies that market orders execute at a price that reflects:
    - Current market price as baseline
    - Bid/ask spread applied correctly
    - Slippage applied for market impact
    """
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()
        db.flush = AsyncMock()
        db.execute = AsyncMock()
        db.add = MagicMock()
        return db
    
    @pytest.fixture
    def execution_engine(self, mock_db):
        """Create execution engine with realistic configs."""
        return ExecutionEngine(
            db=mock_db,
            slippage_config=SlippageConfig(
                base_slippage=Decimal("0.0005"),
                max_slippage=Decimal("0.02")
            ),
            spread_config=BidAskSpreadConfig(
                base_spread_pct=Decimal("0.0005")
            ),
            commission_config=CommissionConfig(model="per_share")
        )
    
    @pytest.fixture
    def mock_trade_buy(self):
        """Create mock BUY trade."""
        trade = MagicMock(spec=Trade)
        trade.id = 1
        trade.portfolio_id = 1
        trade.symbol = "AAPL"
        trade.trade_type = TradeType.BUY
        trade.order_type = OrderType.MARKET
        trade.quantity = Decimal("100")
        trade.status = TradeStatus.PENDING
        return trade
    
    @pytest.fixture
    def mock_trade_sell(self):
        """Create mock SELL trade."""
        trade = MagicMock(spec=Trade)
        trade.id = 2
        trade.portfolio_id = 1
        trade.symbol = "AAPL"
        trade.trade_type = TradeType.SELL
        trade.order_type = OrderType.MARKET
        trade.quantity = Decimal("100")
        trade.status = TradeStatus.PENDING
        return trade
    
    @pytest.mark.asyncio
    async def test_market_buy_executes_at_ask_with_slippage(
        self, execution_engine, mock_trade_buy, mock_db
    ):
        """BUY market orders should execute at ASK price + slippage (worse for buyer)."""
        mid_price = Decimal("150.00")
        
        # Mock portfolio and position queries
        mock_portfolio = MagicMock()
        mock_portfolio.cash_balance = Decimal("100000")
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_portfolio
        
        with patch.object(execution_engine, '_update_portfolio_and_positions', new_callable=AsyncMock):
            result = await execution_engine.execute_market_order(
                mock_trade_buy, mid_price, MarketCondition.NORMAL
            )
        
        assert result.success is True
        # BUY should execute at or above mid price (pays spread + slippage)
        assert result.executed_price >= mid_price
        # Should have bid/ask info
        assert result.bid_price is not None
        assert result.ask_price is not None
        assert result.ask_price > result.bid_price
        # Slippage should be recorded
        assert result.slippage >= Decimal("0")
        print(f"✓ SIM-01: BUY executed at ${result.executed_price} (mid: ${mid_price}, spread: {result.spread:.4%})")
    
    @pytest.mark.asyncio
    async def test_market_sell_executes_at_bid_with_slippage(
        self, execution_engine, mock_trade_sell, mock_db
    ):
        """SELL market orders should execute at BID price - slippage (worse for seller)."""
        mid_price = Decimal("150.00")
        
        mock_position = MagicMock()
        mock_position.avg_cost = Decimal("140.00")
        mock_position.quantity = Decimal("200")
        
        mock_db.execute.return_value.scalar_one_or_none.side_effect = [
            MagicMock(cash_balance=Decimal("100000")),  # portfolio
            mock_position  # position
        ]
        
        with patch.object(execution_engine, '_update_portfolio_and_positions', new_callable=AsyncMock):
            result = await execution_engine.execute_market_order(
                mock_trade_sell, mid_price, MarketCondition.NORMAL
            )
        
        assert result.success is True
        # SELL should execute at or below mid price (receives less)
        assert result.executed_price <= mid_price
        print(f"✓ SIM-01: SELL executed at ${result.executed_price} (mid: ${mid_price})")
    
    @pytest.mark.asyncio
    async def test_market_order_price_within_realistic_bounds(
        self, execution_engine, mock_trade_buy, mock_db
    ):
        """Executed price should be within realistic bounds (max 2% slippage)."""
        mid_price = Decimal("150.00")
        
        mock_db.execute.return_value.scalar_one_or_none.return_value = MagicMock(
            cash_balance=Decimal("100000")
        )
        
        with patch.object(execution_engine, '_update_portfolio_and_positions', new_callable=AsyncMock):
            result = await execution_engine.execute_market_order(
                mock_trade_buy, mid_price, MarketCondition.NORMAL
            )
        
        max_price = mid_price * Decimal("1.025")  # 2.5% max (spread + slippage)
        assert result.executed_price <= max_price, \
            f"Price {result.executed_price} exceeds max {max_price}"
        print(f"✓ SIM-01: Price ${result.executed_price} within bounds (max ${max_price})")


class TestSIM02LimitOrderExecution:
    """
    SIM-02: Limit order executed only when price reached
    
    Verifies that limit orders:
    - Execute when current price meets limit condition
    - Do NOT execute when limit not reached
    - Execute at the limit price (price improvement)
    """
    
    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.flush = AsyncMock()
        db.execute = AsyncMock()
        return db
    
    @pytest.fixture
    def execution_engine(self, mock_db):
        return ExecutionEngine(db=mock_db)
    
    @pytest.fixture
    def mock_buy_limit_trade(self):
        trade = MagicMock(spec=Trade)
        trade.id = 1
        trade.portfolio_id = 1
        trade.symbol = "AAPL"
        trade.trade_type = TradeType.BUY
        trade.order_type = OrderType.LIMIT
        trade.quantity = Decimal("50")
        trade.price = Decimal("145.00")  # Limit price
        trade.status = TradeStatus.PENDING
        return trade
    
    @pytest.fixture
    def mock_sell_limit_trade(self):
        trade = MagicMock(spec=Trade)
        trade.id = 2
        trade.portfolio_id = 1
        trade.symbol = "AAPL"
        trade.trade_type = TradeType.SELL
        trade.order_type = OrderType.LIMIT
        trade.quantity = Decimal("50")
        trade.price = Decimal("155.00")  # Limit price
        trade.status = TradeStatus.PENDING
        return trade
    
    @pytest.mark.asyncio
    async def test_buy_limit_executes_when_price_at_or_below_limit(
        self, execution_engine, mock_buy_limit_trade, mock_db
    ):
        """BUY limit should execute when current price <= limit price."""
        limit_price = mock_buy_limit_trade.price
        current_price = Decimal("144.00")  # Below limit
        
        mock_db.execute.return_value.scalar_one_or_none.return_value = MagicMock(
            cash_balance=Decimal("100000")
        )
        
        with patch.object(execution_engine, '_update_portfolio_and_positions', new_callable=AsyncMock):
            result = await execution_engine.execute_limit_order(
                mock_buy_limit_trade, 
                current_price,
                available_liquidity=Decimal("1000"),  # Ensure full fill
                enable_partial_fill=False
            )
        
        assert result.success is True
        assert result.executed_price == limit_price  # Executes at limit, not market
        print(f"✓ SIM-02: BUY limit executed at ${limit_price} (market: ${current_price})")
    
    @pytest.mark.asyncio
    async def test_buy_limit_not_executed_when_price_above_limit(
        self, execution_engine, mock_buy_limit_trade, mock_db
    ):
        """BUY limit should NOT execute when current price > limit price."""
        current_price = Decimal("148.00")  # Above limit of 145
        
        result = await execution_engine.execute_limit_order(
            mock_buy_limit_trade, current_price
        )
        
        assert result.success is False
        assert "Limit not met" in result.message
        print(f"✓ SIM-02: BUY limit correctly not triggered at ${current_price}")
    
    @pytest.mark.asyncio
    async def test_sell_limit_executes_when_price_at_or_above_limit(
        self, execution_engine, mock_sell_limit_trade, mock_db
    ):
        """SELL limit should execute when current price >= limit price."""
        limit_price = mock_sell_limit_trade.price
        current_price = Decimal("156.00")  # Above limit
        
        mock_position = MagicMock()
        mock_position.avg_cost = Decimal("140.00")
        mock_position.quantity = Decimal("200")
        
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_position
        
        with patch.object(execution_engine, '_update_portfolio_and_positions', new_callable=AsyncMock):
            result = await execution_engine.execute_limit_order(
                mock_sell_limit_trade, 
                current_price,
                enable_partial_fill=False
            )
        
        assert result.success is True
        assert result.executed_price == limit_price
        print(f"✓ SIM-02: SELL limit executed at ${limit_price} (market: ${current_price})")
    
    @pytest.mark.asyncio
    async def test_sell_limit_not_executed_when_price_below_limit(
        self, execution_engine, mock_sell_limit_trade, mock_db
    ):
        """SELL limit should NOT execute when current price < limit price."""
        current_price = Decimal("152.00")  # Below limit of 155
        
        result = await execution_engine.execute_limit_order(
            mock_sell_limit_trade, current_price
        )
        
        assert result.success is False
        assert "Limit not met" in result.message
        print(f"✓ SIM-02: SELL limit correctly not triggered at ${current_price}")


class TestSIM03BidAskSpread:
    """
    SIM-03: Realistic bid/ask spread simulation
    
    Verifies that:
    - Spread is generated around mid price
    - Bid < Mid < Ask
    - Spread widens in volatile/low liquidity conditions
    - Spread stays within realistic bounds
    """
    
    @pytest.fixture
    def execution_engine(self):
        return ExecutionEngine(
            db=AsyncMock(),
            spread_config=BidAskSpreadConfig(
                base_spread_pct=Decimal("0.0005"),  # 5 bps
                volatility_multiplier=Decimal("2.5"),
                liquidity_multiplier=Decimal("3.0"),
                max_spread_pct=Decimal("0.02")  # 2%
            )
        )
    
    def test_spread_bid_below_ask(self, execution_engine):
        """Bid price should always be below ask price."""
        mid_price = Decimal("100.00")
        
        for _ in range(50):  # Test multiple times due to randomness
            bid, ask, spread = execution_engine.simulate_bid_ask(mid_price)
            assert bid < ask, f"Bid {bid} should be < Ask {ask}"
        
        print(f"✓ SIM-03: Bid/Ask spread correctly simulated (bid < ask)")
    
    def test_spread_around_mid_price(self, execution_engine):
        """Spread should be roughly centered around mid price."""
        mid_price = Decimal("100.00")
        
        bid, ask, spread = execution_engine.simulate_bid_ask(mid_price)
        
        # Mid of spread should be close to original mid
        spread_mid = (bid + ask) / 2
        diff_pct = abs(spread_mid - mid_price) / mid_price
        
        assert diff_pct < Decimal("0.01"), \
            f"Spread mid {spread_mid} too far from mid {mid_price}"
        print(f"✓ SIM-03: Spread centered at ${spread_mid} (mid: ${mid_price})")
    
    def test_spread_widens_in_volatile_market(self, execution_engine):
        """Spread should be wider in volatile markets."""
        mid_price = Decimal("100.00")
        
        # Sample multiple times and average
        normal_spreads = []
        volatile_spreads = []
        
        for _ in range(20):
            _, _, normal_spread = execution_engine.simulate_bid_ask(
                mid_price, MarketCondition.NORMAL
            )
            _, _, volatile_spread = execution_engine.simulate_bid_ask(
                mid_price, MarketCondition.VOLATILE
            )
            normal_spreads.append(float(normal_spread))
            volatile_spreads.append(float(volatile_spread))
        
        avg_normal = sum(normal_spreads) / len(normal_spreads)
        avg_volatile = sum(volatile_spreads) / len(volatile_spreads)
        
        assert avg_volatile > avg_normal, \
            f"Volatile spread {avg_volatile:.4%} should be > normal {avg_normal:.4%}"
        print(f"✓ SIM-03: Volatile spread ({avg_volatile:.4%}) > Normal ({avg_normal:.4%})")
    
    def test_spread_widens_in_low_liquidity(self, execution_engine):
        """Spread should be wider in low liquidity conditions."""
        mid_price = Decimal("100.00")
        
        normal_spreads = []
        low_liq_spreads = []
        
        for _ in range(20):
            _, _, normal_spread = execution_engine.simulate_bid_ask(
                mid_price, MarketCondition.NORMAL
            )
            _, _, low_liq_spread = execution_engine.simulate_bid_ask(
                mid_price, MarketCondition.LOW_LIQUIDITY
            )
            normal_spreads.append(float(normal_spread))
            low_liq_spreads.append(float(low_liq_spread))
        
        avg_normal = sum(normal_spreads) / len(normal_spreads)
        avg_low_liq = sum(low_liq_spreads) / len(low_liq_spreads)
        
        assert avg_low_liq > avg_normal, \
            f"Low liquidity spread {avg_low_liq:.4%} should be > normal {avg_normal:.4%}"
        print(f"✓ SIM-03: Low liquidity spread ({avg_low_liq:.4%}) > Normal ({avg_normal:.4%})")
    
    def test_spread_capped_at_maximum(self, execution_engine):
        """Spread should not exceed maximum configured value."""
        mid_price = Decimal("100.00")
        max_spread = execution_engine.spread_config.max_spread_pct
        
        for _ in range(50):
            _, _, spread = execution_engine.simulate_bid_ask(
                mid_price, MarketCondition.LOW_LIQUIDITY
            )
            assert spread <= max_spread, f"Spread {spread:.4%} exceeds max {max_spread:.4%}"
        
        print(f"✓ SIM-03: Spread correctly capped at {max_spread:.2%}")


class TestSIM04SlippageOnLargeOrders:
    """
    SIM-04: Slippage simulated on large orders
    
    Verifies that:
    - Larger orders have more slippage
    - Slippage increases with order size above threshold
    - Slippage is capped at maximum
    """
    
    @pytest.fixture
    def execution_engine(self):
        return ExecutionEngine(
            db=AsyncMock(),
            slippage_config=SlippageConfig(
                base_slippage=Decimal("0.0005"),  # 5 bps
                size_impact_threshold=Decimal("10000"),  # $10k
                size_impact_factor=Decimal("0.0001"),  # 1 bp per $10k over
                max_slippage=Decimal("0.02")  # 2%
            )
        )
    
    def test_small_order_has_base_slippage(self, execution_engine):
        """Small orders should have approximately base slippage."""
        price = Decimal("100.00")
        small_qty = Decimal("50")  # $5,000 order
        
        slippages = []
        for _ in range(20):
            slippage = execution_engine._calculate_slippage(
                price, small_qty, TradeType.BUY, MarketCondition.NORMAL
            )
            slippages.append(float(slippage))
        
        avg_slippage = sum(slippages) / len(slippages)
        base = float(execution_engine.slippage_config.base_slippage)
        
        # Should be close to base (within 2x due to noise)
        assert avg_slippage < base * 3, \
            f"Small order slippage {avg_slippage:.4%} too high"
        print(f"✓ SIM-04: Small order avg slippage: {avg_slippage:.4%} (base: {base:.4%})")
    
    def test_large_order_has_more_slippage(self, execution_engine):
        """Large orders should have more slippage than small orders."""
        price = Decimal("100.00")
        small_qty = Decimal("50")  # $5,000
        large_qty = Decimal("500")  # $50,000
        
        small_slippages = []
        large_slippages = []
        
        for _ in range(20):
            small_slip = execution_engine._calculate_slippage(
                price, small_qty, TradeType.BUY, MarketCondition.NORMAL
            )
            large_slip = execution_engine._calculate_slippage(
                price, large_qty, TradeType.BUY, MarketCondition.NORMAL
            )
            small_slippages.append(float(small_slip))
            large_slippages.append(float(large_slip))
        
        avg_small = sum(small_slippages) / len(small_slippages)
        avg_large = sum(large_slippages) / len(large_slippages)
        
        assert avg_large > avg_small, \
            f"Large order slippage {avg_large:.4%} should be > small {avg_small:.4%}"
        print(f"✓ SIM-04: Large order slippage ({avg_large:.4%}) > Small ({avg_small:.4%})")
    
    def test_slippage_capped_at_maximum(self, execution_engine):
        """Slippage should not exceed maximum."""
        price = Decimal("100.00")
        huge_qty = Decimal("10000")  # $1M order
        max_slip = execution_engine.slippage_config.max_slippage
        
        for _ in range(50):
            slippage = execution_engine._calculate_slippage(
                price, huge_qty, TradeType.BUY, MarketCondition.VOLATILE
            )
            assert slippage <= max_slip, \
                f"Slippage {slippage:.4%} exceeds max {max_slip:.4%}"
        
        print(f"✓ SIM-04: Slippage correctly capped at {max_slip:.2%}")
    
    def test_volatile_market_increases_slippage(self, execution_engine):
        """Volatile markets should increase slippage."""
        price = Decimal("100.00")
        qty = Decimal("100")
        
        normal_slippages = []
        volatile_slippages = []
        
        for _ in range(20):
            normal_slip = execution_engine._calculate_slippage(
                price, qty, TradeType.BUY, MarketCondition.NORMAL
            )
            volatile_slip = execution_engine._calculate_slippage(
                price, qty, TradeType.BUY, MarketCondition.VOLATILE
            )
            normal_slippages.append(float(normal_slip))
            volatile_slippages.append(float(volatile_slip))
        
        avg_normal = sum(normal_slippages) / len(normal_slippages)
        avg_volatile = sum(volatile_slippages) / len(volatile_slippages)
        
        assert avg_volatile > avg_normal, \
            f"Volatile slippage {avg_volatile:.4%} should be > normal {avg_normal:.4%}"
        print(f"✓ SIM-04: Volatile market slippage ({avg_volatile:.4%}) > Normal ({avg_normal:.4%})")


class TestSIM05InsufficientCapitalRejection:
    """
    SIM-05: Order rejected if insufficient capital
    
    Verifies that orders are rejected when:
    - Buy order value exceeds available cash
    - Sell order quantity exceeds available shares
    """
    
    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        return db
    
    @pytest.fixture
    def order_manager(self, mock_db):
        return OrderManager(db=mock_db)
    
    @pytest.mark.asyncio
    async def test_buy_rejected_insufficient_funds(self, order_manager, mock_db):
        """BUY order should be rejected if insufficient funds."""
        # Mock portfolio with limited cash
        mock_portfolio = MagicMock()
        mock_portfolio.cash_balance = Decimal("1000.00")  # Only $1000
        mock_portfolio.risk_profile = None
        
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_portfolio
        
        with patch.object(order_manager, '_get_estimated_price', return_value=Decimal("150.00")):
            with patch.object(order_manager.portfolio_service, 'get_portfolio', return_value=mock_portfolio):
                request = OrderRequest(
                    portfolio_id=1,
                    symbol="AAPL",
                    trade_type=TradeType.BUY,
                    quantity=Decimal("100"),  # 100 x $150 = $15,000 needed
                    order_type=OrderType.MARKET
                )
                
                errors = await order_manager._validate_order(request)
        
        assert len(errors) > 0
        assert any("Insufficient funds" in e for e in errors)
        print(f"✓ SIM-05: BUY rejected - {errors[0]}")
    
    @pytest.mark.asyncio
    async def test_sell_rejected_insufficient_shares(self, order_manager, mock_db):
        """SELL order should be rejected if insufficient shares."""
        mock_portfolio = MagicMock()
        mock_portfolio.cash_balance = Decimal("100000.00")
        mock_portfolio.risk_profile = None
        
        # Mock position with limited shares
        mock_position = MagicMock()
        mock_position.quantity = Decimal("50")  # Only 50 shares
        
        with patch.object(order_manager.portfolio_service, 'get_portfolio', return_value=mock_portfolio):
            with patch.object(order_manager, '_get_position', return_value=mock_position):
                request = OrderRequest(
                    portfolio_id=1,
                    symbol="AAPL",
                    trade_type=TradeType.SELL,
                    quantity=Decimal("100"),  # Want to sell 100
                    order_type=OrderType.MARKET
                )
                
                errors = await order_manager._validate_order(request)
        
        assert len(errors) > 0
        assert any("Insufficient shares" in e for e in errors)
        print(f"✓ SIM-05: SELL rejected - {errors[0]}")
    
    @pytest.mark.asyncio
    async def test_sell_rejected_no_position(self, order_manager, mock_db):
        """SELL order should be rejected if no position exists."""
        mock_portfolio = MagicMock()
        mock_portfolio.cash_balance = Decimal("100000.00")
        mock_portfolio.risk_profile = None
        
        with patch.object(order_manager.portfolio_service, 'get_portfolio', return_value=mock_portfolio):
            with patch.object(order_manager, '_get_position', return_value=None):
                request = OrderRequest(
                    portfolio_id=1,
                    symbol="AAPL",
                    trade_type=TradeType.SELL,
                    quantity=Decimal("100"),
                    order_type=OrderType.MARKET
                )
                
                errors = await order_manager._validate_order(request)
        
        assert len(errors) > 0
        assert any("No position" in e for e in errors)
        print(f"✓ SIM-05: SELL rejected - {errors[0]}")


class TestSIM06PartialFill:
    """
    SIM-06: Partial fill on limit orders
    
    Verifies that limit orders can be partially filled based on
    simulated liquidity conditions.
    """
    
    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.flush = AsyncMock()
        db.execute = AsyncMock()
        return db
    
    @pytest.fixture
    def execution_engine(self, mock_db):
        return ExecutionEngine(db=mock_db)
    
    @pytest.fixture
    def mock_limit_trade(self):
        trade = MagicMock(spec=Trade)
        trade.id = 1
        trade.portfolio_id = 1
        trade.symbol = "AAPL"
        trade.trade_type = TradeType.BUY
        trade.order_type = OrderType.LIMIT
        trade.quantity = Decimal("1000")  # Large order
        trade.price = Decimal("150.00")
        trade.status = TradeStatus.PENDING
        return trade
    
    @pytest.mark.asyncio
    async def test_partial_fill_when_limited_liquidity(
        self, execution_engine, mock_limit_trade, mock_db
    ):
        """Limit order should partial fill when liquidity is limited."""
        current_price = Decimal("149.00")  # Below limit, should trigger
        available_liquidity = Decimal("300")  # Only 300 shares available
        
        mock_db.execute.return_value.scalar_one_or_none.return_value = MagicMock(
            cash_balance=Decimal("1000000")
        )
        
        with patch.object(execution_engine, '_update_portfolio_and_positions', new_callable=AsyncMock):
            result = await execution_engine.execute_limit_order(
                mock_limit_trade,
                current_price,
                available_liquidity=available_liquidity,
                enable_partial_fill=True
            )
        
        assert result.success is True
        assert result.is_partial_fill is True
        assert result.executed_quantity == available_liquidity
        assert result.remaining_quantity == Decimal("700")
        print(f"✓ SIM-06: Partial fill {result.executed_quantity}/{mock_limit_trade.quantity} shares")
    
    @pytest.mark.asyncio
    async def test_full_fill_when_sufficient_liquidity(
        self, execution_engine, mock_limit_trade, mock_db
    ):
        """Limit order should fully fill when liquidity is sufficient."""
        current_price = Decimal("149.00")
        available_liquidity = Decimal("2000")  # Plenty of liquidity
        
        mock_db.execute.return_value.scalar_one_or_none.return_value = MagicMock(
            cash_balance=Decimal("1000000")
        )
        
        with patch.object(execution_engine, '_update_portfolio_and_positions', new_callable=AsyncMock):
            result = await execution_engine.execute_limit_order(
                mock_limit_trade,
                current_price,
                available_liquidity=available_liquidity,
                enable_partial_fill=True
            )
        
        assert result.success is True
        assert result.is_partial_fill is False
        assert result.executed_quantity == mock_limit_trade.quantity
        assert result.remaining_quantity is None
        print(f"✓ SIM-06: Full fill {result.executed_quantity} shares")
    
    @pytest.mark.asyncio
    async def test_partial_fill_sets_trade_status(
        self, execution_engine, mock_limit_trade, mock_db
    ):
        """Partial fill should set trade status to PARTIAL."""
        current_price = Decimal("149.00")
        available_liquidity = Decimal("300")
        
        mock_db.execute.return_value.scalar_one_or_none.return_value = MagicMock(
            cash_balance=Decimal("1000000")
        )
        
        with patch.object(execution_engine, '_update_portfolio_and_positions', new_callable=AsyncMock):
            await execution_engine.execute_limit_order(
                mock_limit_trade,
                current_price,
                available_liquidity=available_liquidity,
                enable_partial_fill=True
            )
        
        assert mock_limit_trade.status == TradeStatus.PARTIAL
        print(f"✓ SIM-06: Trade status set to {mock_limit_trade.status.value}")
    
    def test_simulated_liquidity_varies_by_order_size(self, execution_engine):
        """Simulated liquidity should produce partial fills more often for large orders."""
        price = Decimal("100.00")
        
        small_qty = Decimal("50")
        large_qty = Decimal("2000")
        
        small_fill_rates = []
        large_fill_rates = []
        
        for _ in range(50):
            small_liq = execution_engine._simulate_liquidity(small_qty, price)
            large_liq = execution_engine._simulate_liquidity(large_qty, price)
            
            small_fill_rates.append(float(small_liq / small_qty))
            large_fill_rates.append(float(large_liq / large_qty))
        
        avg_small_rate = sum(small_fill_rates) / len(small_fill_rates)
        avg_large_rate = sum(large_fill_rates) / len(large_fill_rates)
        
        # Small orders should have higher fill rate on average
        assert avg_small_rate > avg_large_rate, \
            f"Small fill rate {avg_small_rate:.2%} should be > large {avg_large_rate:.2%}"
        print(f"✓ SIM-06: Small order fill rate ({avg_small_rate:.2%}) > Large ({avg_large_rate:.2%})")


class TestSIM07CommissionCalculation:
    """
    SIM-07: Commission calculation
    
    Verifies that commissions are calculated correctly for different models:
    - Per-share commission
    - Flat fee
    - Percentage-based
    - Regulatory fees (SEC, FINRA TAF)
    """
    
    @pytest.fixture
    def mock_db(self):
        return AsyncMock()
    
    def test_per_share_commission(self, mock_db):
        """Per-share commission should calculate correctly."""
        engine = ExecutionEngine(
            db=mock_db,
            commission_config=CommissionConfig(
                model="per_share",
                per_share_rate=Decimal("0.005"),  # $0.005/share
                min_commission=Decimal("1.00"),
                max_commission=Decimal("50.00")
            )
        )
        
        trade_value = Decimal("10000")
        quantity = Decimal("200")
        
        commission, breakdown = engine._calculate_commission_with_breakdown(
            trade_value, quantity, TradeType.BUY
        )
        
        expected = quantity * Decimal("0.005")  # 200 * 0.005 = $1.00
        assert commission == expected
        assert "per_share" in breakdown
        print(f"✓ SIM-07: Per-share commission: ${commission} (200 shares @ $0.005)")
    
    def test_per_share_commission_with_minimum(self, mock_db):
        """Per-share commission should respect minimum."""
        engine = ExecutionEngine(
            db=mock_db,
            commission_config=CommissionConfig(
                model="per_share",
                per_share_rate=Decimal("0.005"),
                min_commission=Decimal("1.00")
            )
        )
        
        # Small order: 10 shares * $0.005 = $0.05, should be bumped to $1.00
        commission, _ = engine._calculate_commission_with_breakdown(
            Decimal("1500"), Decimal("10"), TradeType.BUY
        )
        
        assert commission >= Decimal("1.00")
        print(f"✓ SIM-07: Minimum commission applied: ${commission}")
    
    def test_flat_fee_commission(self, mock_db):
        """Flat fee commission should be constant."""
        engine = ExecutionEngine(
            db=mock_db,
            commission_config=CommissionConfig(
                model="flat",
                flat_fee=Decimal("4.95")
            )
        )
        
        # Test with different quantities
        comm1, _ = engine._calculate_commission_with_breakdown(
            Decimal("1000"), Decimal("10"), TradeType.BUY
        )
        comm2, _ = engine._calculate_commission_with_breakdown(
            Decimal("100000"), Decimal("1000"), TradeType.BUY
        )
        
        assert comm1 == Decimal("4.95")
        assert comm2 == Decimal("4.95")
        print(f"✓ SIM-07: Flat fee commission: ${comm1} (same for all orders)")
    
    def test_percentage_commission(self, mock_db):
        """Percentage commission should scale with trade value."""
        engine = ExecutionEngine(
            db=mock_db,
            commission_config=CommissionConfig(
                model="percentage",
                percentage_rate=Decimal("0.001"),  # 0.1%
                min_commission=Decimal("0")
            )
        )
        
        trade_value = Decimal("10000")
        commission, _ = engine._calculate_commission_with_breakdown(
            trade_value, Decimal("100"), TradeType.BUY
        )
        
        expected = trade_value * Decimal("0.001")
        assert commission == expected
        print(f"✓ SIM-07: Percentage commission: ${commission} (0.1% of ${trade_value})")
    
    def test_regulatory_fees_on_sell(self, mock_db):
        """SELL orders should include SEC and FINRA TAF fees."""
        engine = ExecutionEngine(
            db=mock_db,
            commission_config=CommissionConfig(
                model="zero",  # No base commission
                sec_fee_rate=Decimal("0.0000221"),  # $22.10 per million
                finra_taf_rate=Decimal("0.000119")  # Per share
            )
        )
        
        trade_value = Decimal("10000")
        quantity = Decimal("100")
        
        commission, breakdown = engine._calculate_commission_with_breakdown(
            trade_value, quantity, TradeType.SELL
        )
        
        # Should have SEC and FINRA fees
        assert "sec_fee" in breakdown
        assert "finra_taf" in breakdown
        assert breakdown["sec_fee"] > 0
        assert breakdown["finra_taf"] > 0
        
        print(f"✓ SIM-07: Regulatory fees on SELL: SEC=${breakdown['sec_fee']}, TAF=${breakdown['finra_taf']}")
    
    def test_no_regulatory_fees_on_buy(self, mock_db):
        """BUY orders should NOT include SEC/FINRA fees."""
        engine = ExecutionEngine(
            db=mock_db,
            commission_config=CommissionConfig(model="zero")
        )
        
        commission, breakdown = engine._calculate_commission_with_breakdown(
            Decimal("10000"), Decimal("100"), TradeType.BUY
        )
        
        assert "sec_fee" not in breakdown
        assert "finra_taf" not in breakdown
        print(f"✓ SIM-07: No regulatory fees on BUY (commission: ${commission})")
    
    def test_zero_commission_model(self, mock_db):
        """Zero commission model should return 0."""
        engine = ExecutionEngine(
            db=mock_db,
            commission_config=CommissionConfig(model="zero")
        )
        
        commission, _ = engine._calculate_commission_with_breakdown(
            Decimal("100000"), Decimal("1000"), TradeType.BUY
        )
        
        assert commission == Decimal("0")
        print(f"✓ SIM-07: Zero commission model works correctly")


# Run summary if executed directly
if __name__ == "__main__":
    print("\n" + "="*60)
    print("Phase 3: Trading Simulato - Test Summary")
    print("="*60)
    print("""
Tests Implemented:
    SIM-01: Market order executed at realistic price    ✓
    SIM-02: Limit order executed only when price reached ✓
    SIM-03: Realistic bid/ask spread simulation          ✓
    SIM-04: Slippage simulated on large orders          ✓
    SIM-05: Order rejected if insufficient capital      ✓
    SIM-06: Partial fill on limit orders                ✓
    SIM-07: Commission calculation                      ✓
    
Run with: pytest tests/unit/test_trading_simulation.py -v
    """)
