"""
Portfolio Rebalancing Service

Orchestrates portfolio rebalancing with batch order execution,
trade preview, and transaction management.
"""
from decimal import Decimal
from typing import Optional
from datetime import datetime
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.portfolio.allocation import (
    AssetAllocator,
    AllocationAnalysis,
    RebalanceRecommendation,
)
from app.core.trading.order_manager import OrderManager
from app.core.trading.execution import ExecutionEngine
from app.db.models.trade import TradeType, OrderType


@dataclass
class RebalancePreview:
    """Preview of rebalancing trades before execution."""
    analysis: AllocationAnalysis
    orders_to_create: list[dict]
    estimated_commissions: Decimal
    total_buy_value: Decimal
    total_sell_value: Decimal
    net_cash_change: Decimal
    warnings: list[str]
    
    def to_dict(self) -> dict:
        return {
            "analysis": self.analysis.to_dict(),
            "orders_to_create": self.orders_to_create,
            "estimated_commissions": float(self.estimated_commissions),
            "total_buy_value": float(self.total_buy_value),
            "total_sell_value": float(self.total_sell_value),
            "net_cash_change": float(self.net_cash_change),
            "warnings": self.warnings,
        }


@dataclass
class RebalanceResult:
    """Result of rebalancing execution."""
    success: bool
    orders_created: list[dict]
    orders_executed: list[dict]
    orders_failed: list[dict]
    total_trades: int
    execution_time: float
    errors: list[str]
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "orders_created": self.orders_created,
            "orders_executed": self.orders_executed,
            "orders_failed": self.orders_failed,
            "total_trades": self.total_trades,
            "execution_time": self.execution_time,
            "errors": self.errors,
        }


class RebalancingService:
    """
    Service for portfolio rebalancing operations.
    
    Handles:
    - Analyzing allocation drift
    - Generating rebalancing recommendations
    - Creating batch orders
    - Executing rebalancing trades
    """
    
    # Commission per trade (simulated)
    COMMISSION_PER_TRADE = Decimal("0.00")  # Zero for paper trading
    
    def __init__(
        self,
        db: AsyncSession,
        order_manager: Optional[OrderManager] = None,
        execution_engine: Optional[ExecutionEngine] = None,
    ):
        self.db = db
        self.order_manager = order_manager or OrderManager(db)
        self.execution_engine = execution_engine or ExecutionEngine()
    
    async def analyze_portfolio(
        self,
        portfolio_id: int,
        user_id: int,
        risk_profile: str = "balanced",
    ) -> AllocationAnalysis:
        """
        Analyze portfolio allocation and get rebalancing recommendations.
        
        Returns allocation analysis with drift metrics and suggestions.
        """
        # Get portfolio data
        portfolio_data = await self._get_portfolio_data(portfolio_id, user_id)
        if not portfolio_data:
            raise ValueError(f"Portfolio {portfolio_id} not found")
        
        # Create allocator with risk profile
        allocator = AssetAllocator(risk_profile)
        
        # Analyze allocation
        analysis = allocator.analyze_allocation(
            total_value=portfolio_data["total_value"],
            cash_balance=portfolio_data["cash_balance"],
            positions=portfolio_data["positions"],
        )
        
        return analysis
    
    async def preview_rebalance(
        self,
        portfolio_id: int,
        user_id: int,
        risk_profile: str = "balanced",
        min_trade_value: Decimal = Decimal("100"),
    ) -> RebalancePreview:
        """
        Generate preview of rebalancing trades without executing.
        
        Args:
            portfolio_id: Portfolio to rebalance
            user_id: Owner user ID
            risk_profile: Target risk profile
            min_trade_value: Minimum trade value (skip smaller trades)
            
        Returns:
            RebalancePreview with orders to create and estimates
        """
        analysis = await self.analyze_portfolio(portfolio_id, user_id, risk_profile)
        
        warnings = []
        orders_to_create = []
        total_buy = Decimal("0")
        total_sell = Decimal("0")
        
        for rec in analysis.rebalance_recommendations:
            # Skip small trades
            if abs(rec.trade_value) < min_trade_value:
                warnings.append(
                    f"Skipping {rec.symbol}: trade value ${abs(rec.trade_value):.2f} "
                    f"below minimum ${min_trade_value:.2f}"
                )
                continue
            
            # Determine order parameters
            if rec.action == "buy":
                trade_type = TradeType.BUY
                total_buy += rec.trade_value
            elif rec.action == "sell":
                trade_type = TradeType.SELL
                total_sell += abs(rec.trade_value)
            else:
                continue
            
            # Estimate shares (using current price approximation)
            estimated_price = rec.current_value / max(Decimal("1"), rec.current_weight * 100)
            estimated_shares = int(abs(rec.trade_value) / max(estimated_price, Decimal("1")))
            
            if estimated_shares <= 0:
                warnings.append(f"Cannot calculate shares for {rec.symbol}")
                continue
            
            orders_to_create.append({
                "symbol": rec.symbol,
                "trade_type": trade_type.value,
                "order_type": OrderType.MARKET.value,
                "quantity": estimated_shares,
                "estimated_value": float(abs(rec.trade_value)),
                "reason": rec.reason,
                "priority": rec.priority,
            })
        
        # Calculate estimates
        num_orders = len(orders_to_create)
        estimated_commissions = self.COMMISSION_PER_TRADE * num_orders
        net_cash_change = total_sell - total_buy - estimated_commissions
        
        # Add warnings
        if analysis.cash_balance < total_buy:
            warnings.append(
                f"Insufficient cash: need ${total_buy:.2f}, have ${analysis.cash_balance:.2f}. "
                f"Sell orders will execute first."
            )
        
        if not analysis.needs_rebalancing:
            warnings.append("Portfolio is within acceptable drift thresholds. Rebalancing optional.")
        
        return RebalancePreview(
            analysis=analysis,
            orders_to_create=orders_to_create,
            estimated_commissions=estimated_commissions,
            total_buy_value=total_buy,
            total_sell_value=total_sell,
            net_cash_change=net_cash_change,
            warnings=warnings,
        )
    
    async def execute_rebalance(
        self,
        portfolio_id: int,
        user_id: int,
        risk_profile: str = "balanced",
        min_trade_value: Decimal = Decimal("100"),
        execute_sells_first: bool = True,
    ) -> RebalanceResult:
        """
        Execute rebalancing trades.
        
        Args:
            portfolio_id: Portfolio to rebalance
            user_id: Owner user ID
            risk_profile: Target risk profile
            min_trade_value: Minimum trade value
            execute_sells_first: Execute sell orders before buys (frees up cash)
            
        Returns:
            RebalanceResult with execution details
        """
        start_time = datetime.utcnow()
        errors = []
        orders_created = []
        orders_executed = []
        orders_failed = []
        
        try:
            # Get preview
            preview = await self.preview_rebalance(
                portfolio_id, user_id, risk_profile, min_trade_value
            )
            
            if not preview.orders_to_create:
                return RebalanceResult(
                    success=True,
                    orders_created=[],
                    orders_executed=[],
                    orders_failed=[],
                    total_trades=0,
                    execution_time=0,
                    errors=["No trades to execute"],
                )
            
            # Sort orders: sells first if requested
            orders = preview.orders_to_create
            if execute_sells_first:
                sells = [o for o in orders if o["trade_type"] == TradeType.SELL.value]
                buys = [o for o in orders if o["trade_type"] == TradeType.BUY.value]
                orders = sells + buys
            
            # Execute orders
            for order_data in orders:
                try:
                    # Create order
                    order = await self.order_manager.create_order(
                        portfolio_id=portfolio_id,
                        user_id=user_id,
                        symbol=order_data["symbol"],
                        trade_type=TradeType(order_data["trade_type"]),
                        order_type=OrderType(order_data["order_type"]),
                        quantity=order_data["quantity"],
                    )
                    orders_created.append({
                        "order_id": order.id,
                        "symbol": order.symbol,
                        "type": order.trade_type.value,
                        "quantity": order.quantity,
                    })
                    
                    # Execute order (paper trading - immediate execution)
                    execution = await self.execution_engine.execute_order(order)
                    
                    if execution.get("success"):
                        orders_executed.append({
                            "order_id": order.id,
                            "symbol": order.symbol,
                            "filled_price": execution.get("filled_price"),
                            "filled_quantity": execution.get("filled_quantity"),
                        })
                    else:
                        orders_failed.append({
                            "order_id": order.id,
                            "symbol": order.symbol,
                            "error": execution.get("error", "Unknown error"),
                        })
                        
                except Exception as e:
                    logger.error(f"Failed to execute order for {order_data['symbol']}: {e}")
                    orders_failed.append({
                        "symbol": order_data["symbol"],
                        "error": str(e),
                    })
                    errors.append(f"Order failed for {order_data['symbol']}: {e}")
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return RebalanceResult(
                success=len(orders_failed) == 0,
                orders_created=orders_created,
                orders_executed=orders_executed,
                orders_failed=orders_failed,
                total_trades=len(orders_executed),
                execution_time=execution_time,
                errors=errors,
            )
            
        except Exception as e:
            logger.exception(f"Rebalancing failed: {e}")
            return RebalanceResult(
                success=False,
                orders_created=orders_created,
                orders_executed=orders_executed,
                orders_failed=orders_failed,
                total_trades=0,
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
                errors=[str(e)],
            )
    
    async def _get_portfolio_data(
        self,
        portfolio_id: int,
        user_id: int,
    ) -> Optional[dict]:
        """Get portfolio data with positions for analysis."""
        from app.db.models.portfolio import Portfolio
        from app.db.models.position import Position
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        
        stmt = select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == user_id,
        ).options(selectinload(Portfolio.positions))
        
        result = await self.db.execute(stmt)
        portfolio = result.scalar_one_or_none()
        
        if not portfolio:
            return None
        
        # Calculate totals
        positions_data = []
        positions_value = Decimal("0")
        
        for pos in portfolio.positions:
            market_value = Decimal(str(pos.quantity * pos.current_price))
            positions_value += market_value
            
            positions_data.append({
                "symbol": pos.symbol,
                "market_value": market_value,
                "quantity": pos.quantity,
                "current_price": Decimal(str(pos.current_price)),
                "sector": getattr(pos, "sector", "Unknown"),
                "asset_class": getattr(pos, "asset_class", "equity"),
            })
        
        total_value = Decimal(str(portfolio.cash_balance)) + positions_value
        
        return {
            "portfolio_id": portfolio.id,
            "cash_balance": Decimal(str(portfolio.cash_balance)),
            "positions_value": positions_value,
            "total_value": total_value,
            "positions": positions_data,
        }
