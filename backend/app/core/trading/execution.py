"""
PaperTrading Platform - Simulated Execution Engine

Simulates realistic order execution with price slippage, partial fills,
and market conditions simulation.
"""
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import random
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.db.models.trade import Trade, TradeType, OrderType, TradeStatus
from app.db.models.portfolio import Portfolio
from app.db.models.position import Position

logger = logging.getLogger(__name__)


class MarketCondition(str, Enum):
    """Market condition affecting execution."""
    NORMAL = "normal"
    VOLATILE = "volatile"
    LOW_LIQUIDITY = "low_liquidity"
    HIGH_VOLUME = "high_volume"


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
    commission: Decimal = Decimal("0")
    message: str = ""
    executed_at: Optional[datetime] = None


class ExecutionEngine:
    """
    Simulated Execution Engine
    
    Simulates realistic order execution for paper trading:
    - Market orders: Execute at current price with slippage
    - Limit orders: Execute if price meets limit
    - Stop orders: Trigger when price hits stop level
    - Stop-limit orders: Trigger stop then execute as limit
    """
    
    def __init__(
        self, 
        db: AsyncSession,
        slippage_config: Optional[SlippageConfig] = None
    ):
        self.db = db
        self.slippage_config = slippage_config or SlippageConfig()
    
    async def execute_market_order(
        self,
        trade: Trade,
        current_price: Decimal,
        market_condition: MarketCondition = MarketCondition.NORMAL
    ) -> ExecutionResult:
        """
        Execute a market order at current price with slippage.
        
        Args:
            trade: The trade/order to execute
            current_price: Current market price
            market_condition: Current market condition
            
        Returns:
            ExecutionResult with execution details
        """
        try:
            # Calculate slippage
            slippage = self._calculate_slippage(
                current_price=current_price,
                quantity=trade.quantity,
                trade_type=trade.trade_type,
                market_condition=market_condition
            )
            
            # Apply slippage to get executed price
            executed_price = self._apply_slippage(
                price=current_price,
                slippage=slippage,
                trade_type=trade.trade_type
            )
            
            # Calculate total value
            total_value = trade.quantity * executed_price
            
            # Calculate commission (configurable)
            commission = self._calculate_commission(total_value)
            
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
                f"(slippage: {slippage:.4%})"
            )
            
            return ExecutionResult(
                success=True,
                executed_price=executed_price,
                executed_quantity=trade.quantity,
                total_value=total_value,
                slippage=slippage,
                commission=commission,
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
        current_price: Decimal
    ) -> ExecutionResult:
        """
        Execute a limit order if price meets limit.
        
        Args:
            trade: The trade/order to execute
            current_price: Current market price
            
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
        
        # Execute at limit price (better execution)
        executed_price = trade.price
        total_value = trade.quantity * executed_price
        commission = self._calculate_commission(total_value)
        
        # Update trade
        trade.executed_price = executed_price
        trade.executed_quantity = trade.quantity
        trade.total_value = total_value
        trade.commission = commission
        trade.status = TradeStatus.EXECUTED
        trade.executed_at = datetime.utcnow()
        
        await self.db.flush()
        await self._update_portfolio_and_positions(trade)
        
        logger.info(
            f"Executed limit order {trade.id}: {trade.trade_type.value} "
            f"{trade.quantity} {trade.symbol} @ ${executed_price:.4f}"
        )
        
        return ExecutionResult(
            success=True,
            executed_price=executed_price,
            executed_quantity=trade.quantity,
            total_value=total_value,
            slippage=Decimal("0"),
            commission=commission,
            message="Limit order executed",
            executed_at=trade.executed_at
        )
    
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
        Calculate trading commission.
        
        Default: $0 for paper trading (can be configured)
        """
        # Paper trading typically has no commission
        # But can simulate real broker fees if needed
        return Decimal("0")
    
    async def _update_portfolio_and_positions(self, trade: Trade) -> None:
        """
        Update portfolio cash and positions after execution.
        """
        # Get portfolio
        result = await self.db.execute(
            select(Portfolio).where(Portfolio.id == trade.portfolio_id)
        )
        portfolio = result.scalar_one_or_none()
        
        if not portfolio:
            raise ValueError(f"Portfolio {trade.portfolio_id} not found")
        
        total_cost = trade.total_value + trade.commission
        
        if trade.trade_type == TradeType.BUY:
            # Deduct from cash
            portfolio.cash_balance -= total_cost
            
            # Add or update position
            await self._add_to_position(trade)
            
        else:  # SELL
            # Add to cash
            portfolio.cash_balance += (trade.total_value - trade.commission)
            
            # Reduce position
            await self._reduce_position(trade)
        
        await self.db.flush()
    
    async def _add_to_position(self, trade: Trade) -> None:
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
            old_value = position.quantity * position.average_cost
            new_value = trade.executed_quantity * trade.executed_price
            total_quantity = position.quantity + trade.executed_quantity
            
            position.quantity = total_quantity
            position.average_cost = (old_value + new_value) / total_quantity
            position.updated_at = datetime.utcnow()
        else:
            # Create new position
            position = Position(
                portfolio_id=trade.portfolio_id,
                symbol=trade.symbol,
                exchange=trade.exchange,
                quantity=trade.executed_quantity,
                average_cost=trade.executed_price,
                created_at=datetime.utcnow(),
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
        cost_basis = trade.executed_quantity * position.average_cost
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
