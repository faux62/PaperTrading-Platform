"""
PaperTrading Platform - Simulated Execution Engine

Simulates realistic order execution with price slippage, partial fills,
bid/ask spread, commissions, and market conditions simulation.
IBKR-style multi-currency support.
"""
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import random
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_

from app.db.models.trade import Trade, TradeType, OrderType, TradeStatus
from app.db.models.portfolio import Portfolio
from app.db.models.position import Position
from app.db.models.cash_balance import CashBalance

logger = logging.getLogger(__name__)


class MarketCondition(str, Enum):
    """Market condition affecting execution."""
    NORMAL = "normal"
    VOLATILE = "volatile"
    LOW_LIQUIDITY = "low_liquidity"
    HIGH_VOLUME = "high_volume"


@dataclass
class BidAskSpreadConfig:
    """Bid/Ask spread simulation configuration.
    
    Simulates realistic market spread based on:
    - Base spread (typical tight spread for liquid stocks)
    - Volatility impact (wider spreads in volatile markets)
    - Liquidity impact (wider spreads for less liquid securities)
    """
    # Base spread percentage (0.01 = 1%)
    # Typical liquid US stocks: 0.01-0.05% 
    # Less liquid: 0.1-0.5%
    base_spread_pct: Decimal = Decimal("0.0005")  # 5 bps (0.05%)
    
    # Multiplier for volatile markets
    volatility_multiplier: Decimal = Decimal("2.5")
    
    # Multiplier for low liquidity
    liquidity_multiplier: Decimal = Decimal("3.0")
    
    # Maximum spread cap
    max_spread_pct: Decimal = Decimal("0.02")  # 2%
    
    # Minimum spread (in price units, e.g., $0.01)
    min_spread_absolute: Decimal = Decimal("0.01")


@dataclass
class CommissionConfig:
    """Commission structure for paper trading.
    
    Supports multiple commission models:
    - Per-share: Fixed amount per share (e.g., $0.005/share)
    - Flat fee: Fixed fee per trade (e.g., $4.95/trade)
    - Percentage: Percentage of trade value (e.g., 0.1%)
    - Tiered: Combination based on trade size
    """
    # Commission model: "per_share", "flat", "percentage", "tiered", "zero"
    model: str = "per_share"
    
    # Per-share commission (typical: $0.005 - $0.01)
    per_share_rate: Decimal = Decimal("0.005")
    
    # Minimum per order
    min_commission: Decimal = Decimal("1.00")
    
    # Maximum per order (cap)
    max_commission: Decimal = Decimal("50.00")
    
    # Flat fee per trade
    flat_fee: Decimal = Decimal("0.00")
    
    # Percentage of trade value
    percentage_rate: Decimal = Decimal("0.001")  # 0.1%
    
    # SEC fee (US regulatory fee: ~$22.10 per million)
    sec_fee_rate: Decimal = Decimal("0.0000221")
    
    # FINRA TAF fee (~$0.000119 per share, max $5.95)
    finra_taf_rate: Decimal = Decimal("0.000119")
    finra_taf_max: Decimal = Decimal("5.95")


@dataclass
class SlippageConfig:
    """Slippage configuration for execution simulation."""
    # Base slippage percentage (0.01 = 1 basis point)
    base_slippage: Decimal = Decimal("0.0005")  # 5 bps
    
    # Volatility multiplier for volatile markets
    volatility_multiplier: Decimal = Decimal("3.0")
    
    # Low liquidity multiplier
    liquidity_multiplier: Decimal = Decimal("2.0")
    
    # Maximum slippage cap
    max_slippage: Decimal = Decimal("0.02")  # 2%
    
    # Order size impact threshold (larger orders = more slippage)
    size_impact_threshold: Decimal = Decimal("10000")  # $10k
    
    # Size impact factor per $10k over threshold
    size_impact_factor: Decimal = Decimal("0.0001")  # 1 bp per $10k


@dataclass
class ExecutionResult:
    """Result of order execution."""
    success: bool
    executed_price: Optional[Decimal] = None
    executed_quantity: Optional[Decimal] = None
    total_value: Optional[Decimal] = None
    slippage: Optional[Decimal] = None
    slippage_cost: Optional[Decimal] = None  # Actual cost from slippage
    bid_price: Optional[Decimal] = None  # Simulated bid
    ask_price: Optional[Decimal] = None  # Simulated ask
    spread: Optional[Decimal] = None  # Bid/ask spread
    spread_cost: Optional[Decimal] = None  # Cost from spread
    commission: Decimal = Decimal("0")
    commission_breakdown: Optional[Dict[str, Decimal]] = None  # Detail breakdown
    message: str = ""
    executed_at: Optional[datetime] = None
    is_partial_fill: bool = False
    remaining_quantity: Optional[Decimal] = None


class ExecutionEngine:
    """
    Simulated Execution Engine
    
    Simulates realistic order execution for paper trading:
    - Market orders: Execute at current price with slippage and spread
    - Limit orders: Execute if price meets limit (with optional partial fills)
    - Stop orders: Trigger when price hits stop level
    - Stop-limit orders: Trigger stop then execute as limit
    - Realistic bid/ask spread simulation
    - Configurable commission structures
    """
    
    def __init__(
        self, 
        db: AsyncSession,
        slippage_config: Optional[SlippageConfig] = None,
        spread_config: Optional[BidAskSpreadConfig] = None,
        commission_config: Optional[CommissionConfig] = None
    ):
        self.db = db
        self.slippage_config = slippage_config or SlippageConfig()
        self.spread_config = spread_config or BidAskSpreadConfig()
        self.commission_config = commission_config or CommissionConfig()
    
    def simulate_bid_ask(
        self,
        mid_price: Decimal,
        market_condition: MarketCondition = MarketCondition.NORMAL
    ) -> Tuple[Decimal, Decimal, Decimal]:
        """
        Simulate realistic bid/ask prices from mid price.
        
        Args:
            mid_price: The mid/last price
            market_condition: Current market condition
            
        Returns:
            Tuple of (bid_price, ask_price, spread_pct)
        """
        config = self.spread_config
        
        # Calculate spread percentage based on conditions
        spread_pct = config.base_spread_pct
        
        if market_condition == MarketCondition.VOLATILE:
            spread_pct *= config.volatility_multiplier
        elif market_condition == MarketCondition.LOW_LIQUIDITY:
            spread_pct *= config.liquidity_multiplier
        elif market_condition == MarketCondition.HIGH_VOLUME:
            # High volume = tighter spreads
            spread_pct *= Decimal("0.5")
        
        # Add random noise (±30%)
        noise = Decimal(str(random.uniform(0.7, 1.3)))
        spread_pct *= noise
        
        # Cap spread
        spread_pct = min(spread_pct, config.max_spread_pct)
        
        # Calculate absolute spread
        spread_abs = mid_price * spread_pct
        spread_abs = max(spread_abs, config.min_spread_absolute)
        
        # Calculate bid and ask (split spread around mid)
        half_spread = spread_abs / 2
        bid_price = (mid_price - half_spread).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        ask_price = (mid_price + half_spread).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        return bid_price, ask_price, spread_pct
    
    async def execute_market_order(
        self,
        trade: Trade,
        current_price: Decimal,
        market_condition: MarketCondition = MarketCondition.NORMAL
    ) -> ExecutionResult:
        """
        Execute a market order at current price with bid/ask spread and slippage.
        
        For market orders:
        - BUY: Execute at ASK price + slippage (pays spread)
        - SELL: Execute at BID price - slippage (pays spread)
        
        Args:
            trade: The trade/order to execute
            current_price: Current market mid price
            market_condition: Current market condition
            
        Returns:
            ExecutionResult with execution details including spread info
        """
        try:
            # Simulate bid/ask spread
            bid_price, ask_price, spread_pct = self.simulate_bid_ask(
                current_price, market_condition
            )
            
            # Determine base price based on trade type
            # BUY orders execute at ASK, SELL at BID
            if trade.trade_type == TradeType.BUY:
                base_price = ask_price
            else:
                base_price = bid_price
            
            # Calculate additional slippage on top of spread
            slippage = self._calculate_slippage(
                current_price=base_price,
                quantity=trade.quantity,
                trade_type=trade.trade_type,
                market_condition=market_condition
            )
            
            # Apply slippage to get executed price
            executed_price = self._apply_slippage(
                price=base_price,
                slippage=slippage,
                trade_type=trade.trade_type
            )
            
            # Calculate total value
            total_value = trade.quantity * executed_price
            
            # Calculate commission with breakdown
            commission, commission_breakdown = self._calculate_commission_with_breakdown(
                trade_value=total_value,
                quantity=trade.quantity,
                trade_type=trade.trade_type
            )
            
            # Calculate costs from spread and slippage
            spread_cost = abs(base_price - current_price) * trade.quantity
            slippage_cost = abs(executed_price - base_price) * trade.quantity
            
            # Update the trade record
            trade.executed_price = executed_price
            trade.executed_quantity = trade.quantity
            trade.total_value = total_value
            trade.commission = commission
            trade.status = TradeStatus.EXECUTED
            trade.executed_at = datetime.utcnow()
            
            await self.db.flush()
            
            # Update portfolio and positions
            await self._update_portfolio_and_positions(trade)
            
            logger.info(
                f"Executed market order {trade.id}: {trade.trade_type.value} "
                f"{trade.quantity} {trade.symbol} @ ${executed_price:.4f} "
                f"(spread: {spread_pct:.4%}, slippage: {slippage:.4%}, commission: ${commission:.2f})"
            )
            
            return ExecutionResult(
                success=True,
                executed_price=executed_price,
                executed_quantity=trade.quantity,
                total_value=total_value,
                slippage=slippage,
                slippage_cost=slippage_cost,
                bid_price=bid_price,
                ask_price=ask_price,
                spread=spread_pct,
                spread_cost=spread_cost,
                commission=commission,
                commission_breakdown=commission_breakdown,
                message="Order executed successfully",
                executed_at=trade.executed_at
            )
            
        except Exception as e:
            logger.error(f"Error executing market order {trade.id}: {e}")
            trade.status = TradeStatus.FAILED
            await self.db.flush()
            
            return ExecutionResult(
                success=False,
                message=f"Execution failed: {str(e)}"
            )
    
    async def execute_limit_order(
        self,
        trade: Trade,
        current_price: Decimal,
        available_liquidity: Optional[Decimal] = None,
        enable_partial_fill: bool = True
    ) -> ExecutionResult:
        """
        Execute a limit order if price meets limit.
        
        Supports partial fills based on available liquidity simulation.
        
        Args:
            trade: The trade/order to execute
            current_price: Current market price
            available_liquidity: Simulated available shares at price level
                               If None, generates random liquidity
            enable_partial_fill: Whether to allow partial fills
            
        Returns:
            ExecutionResult with execution details or None if not triggered
        """
        if not trade.price:
            return ExecutionResult(
                success=False,
                message="Limit order requires a limit price"
            )
        
        # Check if limit is met
        limit_met = False
        if trade.trade_type == TradeType.BUY:
            # Buy limit: execute if current price <= limit price
            limit_met = current_price <= trade.price
        else:
            # Sell limit: execute if current price >= limit price
            limit_met = current_price >= trade.price
        
        if not limit_met:
            return ExecutionResult(
                success=False,
                message=f"Limit not met: current ${current_price:.4f}, limit ${trade.price:.4f}"
            )
        
        # Determine fill quantity based on liquidity
        requested_quantity = trade.quantity
        
        if enable_partial_fill:
            # Simulate available liquidity if not provided
            if available_liquidity is None:
                available_liquidity = self._simulate_liquidity(
                    requested_quantity,
                    current_price
                )
            
            # Calculate fill quantity
            fill_quantity = min(requested_quantity, available_liquidity)
            
            # Ensure minimum fill (at least 1 share or 10% of order)
            min_fill = max(Decimal("1"), requested_quantity * Decimal("0.1"))
            if fill_quantity < min_fill and fill_quantity < requested_quantity:
                fill_quantity = min_fill
        else:
            fill_quantity = requested_quantity
        
        is_partial = fill_quantity < requested_quantity
        remaining = requested_quantity - fill_quantity if is_partial else None
        
        # Execute at limit price
        executed_price = trade.price
        total_value = fill_quantity * executed_price
        commission, breakdown = self._calculate_commission_with_breakdown(
            total_value, fill_quantity, trade.trade_type
        )
        
        # Update trade
        trade.executed_price = executed_price
        trade.executed_quantity = fill_quantity
        trade.total_value = total_value
        trade.commission = commission
        
        if is_partial:
            trade.status = TradeStatus.PARTIAL
            trade.notes = f"Partial fill: {fill_quantity}/{requested_quantity} shares"
        else:
            trade.status = TradeStatus.EXECUTED
        
        trade.executed_at = datetime.utcnow()
        
        await self.db.flush()
        await self._update_portfolio_and_positions(trade)
        
        fill_type = "partial fill" if is_partial else "full fill"
        logger.info(
            f"Executed limit order {trade.id} ({fill_type}): {trade.trade_type.value} "
            f"{fill_quantity}/{requested_quantity} {trade.symbol} @ ${executed_price:.4f}"
        )
        
        return ExecutionResult(
            success=True,
            executed_price=executed_price,
            executed_quantity=fill_quantity,
            total_value=total_value,
            slippage=Decimal("0"),
            commission=commission,
            commission_breakdown=breakdown,
            message=f"Limit order {fill_type}" + (f" ({remaining} remaining)" if remaining else ""),
            executed_at=trade.executed_at,
            is_partial_fill=is_partial,
            remaining_quantity=remaining
        )
    
    def _simulate_liquidity(
        self,
        requested_quantity: Decimal,
        price: Decimal
    ) -> Decimal:
        """
        Simulate available liquidity at a price level.
        
        Uses a probabilistic model:
        - Small orders (<100 shares): Usually full fill
        - Medium orders (100-1000): Sometimes partial
        - Large orders (>1000): Higher chance of partial
        
        Returns simulated available shares.
        """
        qty = float(requested_quantity)
        
        # Base fill probability decreases with order size
        if qty < 100:
            # Small orders: 95% chance of full fill
            fill_pct = random.uniform(0.95, 1.0) if random.random() < 0.95 else random.uniform(0.5, 0.95)
        elif qty < 1000:
            # Medium orders: 75% chance of full fill
            fill_pct = random.uniform(0.85, 1.0) if random.random() < 0.75 else random.uniform(0.3, 0.85)
        else:
            # Large orders: 50% chance of full fill
            fill_pct = random.uniform(0.7, 1.0) if random.random() < 0.50 else random.uniform(0.2, 0.7)
        
        available = Decimal(str(qty * fill_pct)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return max(Decimal("1"), available)  # At least 1 share
    
    async def check_stop_order(
        self,
        trade: Trade,
        current_price: Decimal
    ) -> bool:
        """
        Check if stop order should be triggered.
        
        Returns True if stop is triggered, False otherwise.
        """
        if not trade.price:
            return False
        
        if trade.trade_type == TradeType.BUY:
            # Buy stop: trigger if current price >= stop price
            return current_price >= trade.price
        else:
            # Sell stop: trigger if current price <= stop price
            return current_price <= trade.price
    
    async def execute_stop_order(
        self,
        trade: Trade,
        current_price: Decimal,
        market_condition: MarketCondition = MarketCondition.NORMAL
    ) -> ExecutionResult:
        """
        Execute a stop order if triggered.
        
        Stop orders convert to market orders when triggered.
        """
        # Check if stop is triggered
        if not await self.check_stop_order(trade, current_price):
            return ExecutionResult(
                success=False,
                message=f"Stop not triggered: current ${current_price:.4f}, stop ${trade.price:.4f}"
            )
        
        # Execute as market order
        logger.info(f"Stop triggered for order {trade.id} at ${current_price:.4f}")
        return await self.execute_market_order(trade, current_price, market_condition)
    
    def _calculate_slippage(
        self,
        current_price: Decimal,
        quantity: Decimal,
        trade_type: TradeType,
        market_condition: MarketCondition
    ) -> Decimal:
        """
        Calculate realistic slippage based on multiple factors.
        
        Factors considered:
        - Base slippage rate
        - Market condition (volatility, liquidity)
        - Order size impact
        - Random market microstructure noise
        """
        config = self.slippage_config
        
        # Start with base slippage
        slippage = config.base_slippage
        
        # Apply market condition multiplier
        if market_condition == MarketCondition.VOLATILE:
            slippage *= config.volatility_multiplier
        elif market_condition == MarketCondition.LOW_LIQUIDITY:
            slippage *= config.liquidity_multiplier
        elif market_condition == MarketCondition.HIGH_VOLUME:
            # High volume = better liquidity = less slippage
            slippage *= Decimal("0.5")
        
        # Apply order size impact
        order_value = quantity * current_price
        if order_value > config.size_impact_threshold:
            excess = order_value - config.size_impact_threshold
            size_impact = (excess / config.size_impact_threshold) * config.size_impact_factor
            slippage += size_impact
        
        # Add random microstructure noise (-20% to +50% of calculated slippage)
        noise_factor = Decimal(str(random.uniform(0.8, 1.5)))
        slippage *= noise_factor
        
        # Cap at maximum slippage
        slippage = min(slippage, config.max_slippage)
        
        return slippage.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    
    def _apply_slippage(
        self,
        price: Decimal,
        slippage: Decimal,
        trade_type: TradeType
    ) -> Decimal:
        """
        Apply slippage to price.
        
        For buys: price goes up (worse execution)
        For sells: price goes down (worse execution)
        """
        if trade_type == TradeType.BUY:
            executed_price = price * (1 + slippage)
        else:
            executed_price = price * (1 - slippage)
        
        return executed_price.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    
    def _calculate_commission(self, total_value: Decimal) -> Decimal:
        """
        Calculate trading commission (simplified version for backward compatibility).
        """
        commission, _ = self._calculate_commission_with_breakdown(total_value, Decimal("0"), TradeType.BUY)
        return commission
    
    def _calculate_commission_with_breakdown(
        self,
        trade_value: Decimal,
        quantity: Decimal,
        trade_type: TradeType
    ) -> Tuple[Decimal, Dict[str, Decimal]]:
        """
        Calculate trading commission with detailed breakdown.
        
        Supports multiple commission models:
        - zero: No commission (free trading, but still includes regulatory fees)
        - per_share: Commission per share traded
        - flat: Flat fee per trade
        - percentage: Percentage of trade value
        - tiered: Combination of models
        
        Args:
            trade_value: Total trade value
            quantity: Number of shares
            trade_type: BUY or SELL
            
        Returns:
            Tuple of (total_commission, breakdown_dict)
        """
        config = self.commission_config
        breakdown = {}
        base_commission = Decimal("0")
        
        if config.model == "zero":
            breakdown["base"] = Decimal("0")
        
        elif config.model == "per_share":
            # Per-share commission with min/max
            base_commission = quantity * config.per_share_rate
            base_commission = max(base_commission, config.min_commission)
            base_commission = min(base_commission, config.max_commission)
            breakdown["per_share"] = base_commission
            
        elif config.model == "flat":
            # Flat fee per trade
            base_commission = config.flat_fee
            breakdown["flat_fee"] = base_commission
            
        elif config.model == "percentage":
            # Percentage of trade value
            base_commission = trade_value * config.percentage_rate
            base_commission = max(base_commission, config.min_commission)
            base_commission = min(base_commission, config.max_commission)
            breakdown["percentage"] = base_commission
            
        elif config.model == "tiered":
            # Combination: flat + per_share for large orders
            base_commission = config.flat_fee
            if quantity > 1000:
                per_share_part = (quantity - 1000) * config.per_share_rate
                base_commission += per_share_part
                breakdown["flat_fee"] = config.flat_fee
                breakdown["per_share_excess"] = per_share_part
            else:
                breakdown["flat_fee"] = base_commission
        else:
            # Default to zero
            breakdown["base"] = Decimal("0")
        
        # Add regulatory fees for SELL orders (US markets simulation)
        if trade_type == TradeType.SELL:
            # SEC fee
            sec_fee = (trade_value * config.sec_fee_rate).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            breakdown["sec_fee"] = sec_fee
            
            # FINRA TAF fee
            finra_fee = min(
                quantity * config.finra_taf_rate,
                config.finra_taf_max
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            breakdown["finra_taf"] = finra_fee
            
            base_commission = base_commission + sec_fee + finra_fee
        
        total = base_commission.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        return total, breakdown
    
    async def _get_or_create_cash_balance(
        self, 
        portfolio_id: int, 
        currency: str
    ) -> CashBalance:
        """Get or create a cash balance for a specific currency (IBKR-style)."""
        result = await self.db.execute(
            select(CashBalance).where(
                and_(
                    CashBalance.portfolio_id == portfolio_id,
                    CashBalance.currency == currency
                )
            )
        )
        balance = result.scalar_one_or_none()
        
        if not balance:
            balance = CashBalance(
                portfolio_id=portfolio_id,
                currency=currency,
                balance=Decimal("0.00")
            )
            self.db.add(balance)
            await self.db.flush()
        
        return balance
    
    async def _update_portfolio_and_positions(self, trade: Trade) -> None:
        """
        Update portfolio cash and positions after execution.
        IBKR-style: Uses multi-currency cash balances.
        """
        # Get portfolio
        result = await self.db.execute(
            select(Portfolio).where(Portfolio.id == trade.portfolio_id)
        )
        portfolio = result.scalar_one_or_none()
        
        if not portfolio:
            raise ValueError(f"Portfolio {trade.portfolio_id} not found")
        
        # Determine the currency of the trade
        # Use trade's native_currency, or default to portfolio currency
        trade_currency = trade.native_currency or portfolio.currency or "USD"
        
        total_cost = trade.total_value + trade.commission
        
        # Get the cash balance for this currency
        cash_balance = await self._get_or_create_cash_balance(
            trade.portfolio_id, 
            trade_currency
        )
        
        if trade.trade_type == TradeType.BUY:
            # Deduct from currency-specific cash balance
            cash_balance.balance -= total_cost
            
            # Also update legacy cash_balance for backwards compatibility
            # (only if same currency as portfolio base)
            if trade_currency == portfolio.currency:
                portfolio.cash_balance -= total_cost
            
            # Add or update position
            await self._add_to_position(trade, trade_currency)
            
        else:  # SELL
            # Add to currency-specific cash balance
            cash_balance.balance += (trade.total_value - trade.commission)
            
            # Update legacy field
            if trade_currency == portfolio.currency:
                portfolio.cash_balance += (trade.total_value - trade.commission)
            
            # Reduce position
            await self._reduce_position(trade)
        
        cash_balance.updated_at = datetime.utcnow()
        await self.db.flush()
    
    async def _add_to_position(self, trade: Trade, currency: str) -> None:
        """Add bought shares to position."""
        # Check for existing position
        result = await self.db.execute(
            select(Position).where(
                Position.portfolio_id == trade.portfolio_id,
                Position.symbol == trade.symbol
            )
        )
        position = result.scalar_one_or_none()
        
        if position:
            # Update existing position (average cost basis)
            old_value = position.quantity * position.avg_cost
            new_value = trade.executed_quantity * trade.executed_price
            total_quantity = position.quantity + trade.executed_quantity
            
            position.quantity = total_quantity
            position.avg_cost = (old_value + new_value) / total_quantity
            position.updated_at = datetime.utcnow()
        else:
            # Create new position
            position = Position(
                portfolio_id=trade.portfolio_id,
                symbol=trade.symbol,
                exchange=trade.exchange,
                quantity=trade.executed_quantity,
                avg_cost=trade.executed_price,
                current_price=trade.executed_price,
                market_value=trade.total_value,
                native_currency=currency,  # Track position's native currency (IBKR-style)
                opened_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            self.db.add(position)
    
    async def _reduce_position(self, trade: Trade) -> None:
        """Reduce position from sold shares and calculate realized P&L."""
        result = await self.db.execute(
            select(Position).where(
                Position.portfolio_id == trade.portfolio_id,
                Position.symbol == trade.symbol
            )
        )
        position = result.scalar_one_or_none()
        
        if not position:
            raise ValueError(f"No position found for {trade.symbol}")
        
        # Calculate realized P&L
        cost_basis = trade.executed_quantity * position.avg_cost
        sale_proceeds = trade.executed_quantity * trade.executed_price
        realized_pnl = sale_proceeds - cost_basis
        
        # Update trade with realized P&L
        trade.realized_pnl = realized_pnl
        
        # Update position
        position.quantity -= trade.executed_quantity
        position.updated_at = datetime.utcnow()
        
        # Remove position if fully closed
        if position.quantity <= 0:
            await self.db.delete(position)


class OrderExecutor:
    """
    High-level order executor that processes pending orders.
    
    Coordinates order manager and execution engine.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.execution_engine = ExecutionEngine(db)
    
    async def execute_order(
        self,
        trade: Trade,
        current_price: Decimal,
        market_condition: MarketCondition = MarketCondition.NORMAL
    ) -> ExecutionResult:
        """
        Execute an order based on its type.
        
        Args:
            trade: The order to execute
            current_price: Current market price
            market_condition: Current market condition
            
        Returns:
            ExecutionResult with execution details
        """
        if trade.status != TradeStatus.PENDING:
            return ExecutionResult(
                success=False,
                message=f"Order is not pending (status: {trade.status.value})"
            )
        
        if trade.order_type == OrderType.MARKET:
            return await self.execution_engine.execute_market_order(
                trade, current_price, market_condition
            )
        
        elif trade.order_type == OrderType.LIMIT:
            return await self.execution_engine.execute_limit_order(
                trade, current_price
            )
        
        elif trade.order_type == OrderType.STOP:
            return await self.execution_engine.execute_stop_order(
                trade, current_price, market_condition
            )
        
        elif trade.order_type == OrderType.STOP_LIMIT:
            # Check if stop triggered, then execute as limit
            if await self.execution_engine.check_stop_order(trade, current_price):
                return await self.execution_engine.execute_limit_order(
                    trade, current_price
                )
            return ExecutionResult(
                success=False,
                message="Stop-limit not triggered"
            )
        
        return ExecutionResult(
            success=False,
            message=f"Unknown order type: {trade.order_type}"
        )
    
    async def process_pending_orders(
        self,
        prices: Dict[str, Decimal],
        market_condition: MarketCondition = MarketCondition.NORMAL
    ) -> Dict[int, ExecutionResult]:
        """
        Process all pending orders with current prices.
        
        Args:
            prices: Dict of symbol -> current price
            market_condition: Current market condition
            
        Returns:
            Dict of order_id -> ExecutionResult
        """
        results = {}
        
        # Get all pending orders
        query = select(Trade).where(Trade.status == TradeStatus.PENDING)
        result = await self.db.execute(query)
        pending_orders = result.scalars().all()
        
        for trade in pending_orders:
            if trade.symbol in prices:
                current_price = prices[trade.symbol]
                exec_result = await self.execute_order(
                    trade, current_price, market_condition
                )
                results[trade.id] = exec_result
        
        return results
