"""
PaperTrading Platform - Order Manager Service

Handles order creation, validation, queueing, and lifecycle management.

SINGLE CURRENCY MODEL:
- Validation checks portfolio.cash_balance (single currency)
- For cross-currency trades, converts estimated cost to portfolio currency
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from enum import Enum
import logging
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.db.models.trade import Trade, TradeType, OrderType, TradeStatus
from app.db.models.portfolio import Portfolio
from app.db.models.position import Position
from app.core.portfolio.service import PortfolioService
from app.core.portfolio.risk_profiles import get_risk_profile
from app.core.currency_service import get_symbol_currency
from app.utils.currency import convert

logger = logging.getLogger(__name__)


class OrderValidationError(Exception):
    """Raised when order validation fails."""
    pass


class InsufficientFundsError(OrderValidationError):
    """Raised when there are insufficient funds for the order."""
    pass


class InsufficientSharesError(OrderValidationError):
    """Raised when there are insufficient shares to sell."""
    pass


class MarketClosedError(OrderValidationError):
    """Raised when trying to execute during closed market hours."""
    pass


@dataclass
class OrderRequest:
    """Order request data."""
    portfolio_id: int
    symbol: str
    trade_type: TradeType
    quantity: Decimal
    order_type: OrderType = OrderType.MARKET
    limit_price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    exchange: Optional[str] = None
    notes: Optional[str] = None
    native_currency: str = "USD"  # Symbol's native currency (IBKR-style)
    
    def __post_init__(self):
        """Validate order request."""
        if self.quantity <= 0:
            raise OrderValidationError("Quantity must be positive")
        
        if self.order_type == OrderType.LIMIT and not self.limit_price:
            raise OrderValidationError("Limit price required for limit orders")
        
        if self.order_type == OrderType.STOP and not self.stop_price:
            raise OrderValidationError("Stop price required for stop orders")
        
        if self.order_type == OrderType.STOP_LIMIT:
            if not self.stop_price or not self.limit_price:
                raise OrderValidationError("Both stop and limit prices required for stop-limit orders")


@dataclass
class OrderResult:
    """Result of order operation."""
    success: bool
    order_id: Optional[int] = None
    message: str = ""
    trade: Optional[Trade] = None
    errors: List[str] = field(default_factory=list)


class OrderManager:
    """
    Order Manager Service
    
    Responsible for:
    - Order validation
    - Order creation and queueing
    - Order cancellation
    - Order status management
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.portfolio_service = PortfolioService(db)
    
    async def create_order(self, request: OrderRequest) -> OrderResult:
        """
        Create a new order.
        
        Args:
            request: Order request data
            
        Returns:
            OrderResult with order details or errors
        """
        try:
            # Validate the order
            validation_errors = await self._validate_order(request)
            if validation_errors:
                return OrderResult(
                    success=False,
                    message="Order validation failed",
                    errors=validation_errors
                )
            
            # Create the trade/order record
            trade = Trade(
                portfolio_id=request.portfolio_id,
                symbol=request.symbol.upper(),
                exchange=request.exchange,
                native_currency=request.native_currency,  # IBKR-style: track trade's native currency
                trade_type=request.trade_type,
                order_type=request.order_type,
                quantity=request.quantity,
                price=request.limit_price or request.stop_price,
                status=TradeStatus.PENDING,
                notes=request.notes,
                created_at=datetime.utcnow()
            )
            
            self.db.add(trade)
            await self.db.flush()
            
            logger.info(f"Order created: {trade.id} - {trade.trade_type.value} {trade.quantity} {trade.symbol}")
            
            return OrderResult(
                success=True,
                order_id=trade.id,
                message="Order created successfully",
                trade=trade
            )
            
        except OrderValidationError as e:
            logger.warning(f"Order validation error: {e}")
            return OrderResult(
                success=False,
                message=str(e),
                errors=[str(e)]
            )
        except Exception as e:
            import traceback
            logger.error(f"Error creating order: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return OrderResult(
                success=False,
                message="Internal error creating order",
                errors=[str(e)]
            )
    
    async def _validate_order(self, request: OrderRequest) -> List[str]:
        """
        Validate order against portfolio constraints.
        
        SINGLE CURRENCY MODEL:
        - Checks portfolio.cash_balance (in portfolio's base currency)
        - For cross-currency trades, converts estimated cost to portfolio currency
        
        Returns list of validation errors (empty if valid).
        """
        errors = []
        
        # Get portfolio
        portfolio = await self.portfolio_service.get_portfolio(request.portfolio_id)
        if not portfolio:
            errors.append(f"Portfolio {request.portfolio_id} not found")
            return errors
        
        # For buy orders, check available funds (converted to portfolio currency)
        if request.trade_type == TradeType.BUY:
            # Estimate order value (use limit price if available, otherwise we need current price)
            estimated_price = request.limit_price or await self._get_estimated_price(request.symbol)
            if estimated_price:
                estimated_value_native = request.quantity * estimated_price
                
                # Get the symbol's native currency
                symbol_currency = get_symbol_currency(request.symbol)
                portfolio_currency = portfolio.currency or "EUR"
                
                # Convert estimated cost to portfolio currency
                if symbol_currency != portfolio_currency:
                    estimated_value_portfolio, exchange_rate = await convert(
                        estimated_value_native,
                        symbol_currency,
                        portfolio_currency
                    )
                else:
                    estimated_value_portfolio = estimated_value_native
                
                # Check against portfolio's single cash balance
                available_balance = portfolio.cash_balance or Decimal("0")
                
                if estimated_value_portfolio > available_balance:
                    errors.append(
                        f"Insufficient funds: need ~{estimated_value_portfolio:.2f} {portfolio_currency} "
                        f"({estimated_value_native:.2f} {symbol_currency}), "
                        f"available {available_balance:.2f} {portfolio_currency}"
                    )
        
        # For sell orders, check available shares
        if request.trade_type == TradeType.SELL:
            position = await self._get_position(request.portfolio_id, request.symbol)
            if not position:
                errors.append(f"No position in {request.symbol} to sell")
            elif position.quantity < request.quantity:
                errors.append(
                    f"Insufficient shares: want to sell {request.quantity}, "
                    f"have {position.quantity}"
                )
        
        # Validate against risk profile constraints
        if portfolio.risk_profile:
            constraint_errors = await self._validate_constraints(
                portfolio, request
            )
            errors.extend(constraint_errors)
        
        return errors
    
    async def _validate_constraints(
        self, 
        portfolio: Portfolio, 
        request: OrderRequest
    ) -> List[str]:
        """Validate order against portfolio risk profile constraints."""
        errors = []
        
        # Get current positions
        positions = await self._get_all_positions(portfolio.id)
        
        # Calculate new position size after order
        if request.trade_type == TradeType.BUY:
            estimated_price = request.limit_price or await self._get_estimated_price(request.symbol)
            if estimated_price:
                # Calculate value in native currency
                new_value_native = request.quantity * estimated_price
                
                # Get currencies
                symbol_currency = get_symbol_currency(request.symbol)
                portfolio_currency = portfolio.currency or "EUR"
                
                # Convert to portfolio currency for proper comparison
                if symbol_currency != portfolio_currency:
                    new_value_portfolio, _ = await convert(
                        new_value_native,
                        symbol_currency,
                        portfolio_currency
                    )
                else:
                    new_value_portfolio = new_value_native
                
                # Get portfolio value (already in portfolio currency)
                portfolio_value = await self.portfolio_service.get_portfolio_value(portfolio.id)
                
                if portfolio_value > 0:
                    position_pct = (float(new_value_portfolio) / float(portfolio_value)) * 100
                    
                    # Check max position size from risk profile
                    risk_profile = get_risk_profile(portfolio.risk_profile.value)
                    max_position = float(risk_profile.position_limits.max_position_size_percent)
                    
                    if position_pct > max_position:
                        errors.append(
                            f"Position size {position_pct:.1f}% exceeds max {max_position}%"
                        )
        
        return errors
    
    async def _get_estimated_price(self, symbol: str) -> Optional[Decimal]:
        """
        Get estimated price for symbol.
        In production, this would fetch from market data providers.
        """
        # TODO: Integrate with market data providers
        # For now, return None to skip price-based validation
        return None
    
    async def _get_position(self, portfolio_id: int, symbol: str) -> Optional[Position]:
        """Get position for symbol in portfolio."""
        result = await self.db.execute(
            select(Position).where(
                Position.portfolio_id == portfolio_id,
                Position.symbol == symbol.upper()
            )
        )
        return result.scalar_one_or_none()
    
    async def _get_all_positions(self, portfolio_id: int) -> List[Position]:
        """Get all positions in portfolio."""
        result = await self.db.execute(
            select(Position).where(Position.portfolio_id == portfolio_id)
        )
        return list(result.scalars().all())
    
    async def cancel_order(self, order_id: int, user_id: int) -> OrderResult:
        """
        Cancel a pending order.
        
        Args:
            order_id: ID of order to cancel
            user_id: ID of user requesting cancellation (for authorization)
            
        Returns:
            OrderResult with cancellation status
        """
        try:
            # Get the order
            result = await self.db.execute(
                select(Trade).where(Trade.id == order_id)
            )
            trade = result.scalar_one_or_none()
            
            if not trade:
                return OrderResult(
                    success=False,
                    message=f"Order {order_id} not found"
                )
            
            # Check if order can be cancelled
            if trade.status != TradeStatus.PENDING:
                return OrderResult(
                    success=False,
                    message=f"Cannot cancel order with status {trade.status.value}"
                )
            
            # Verify user owns the portfolio
            portfolio = await self.portfolio_service.get_portfolio(trade.portfolio_id)
            if not portfolio or portfolio.user_id != user_id:
                return OrderResult(
                    success=False,
                    message="Not authorized to cancel this order"
                )
            
            # Cancel the order
            trade.status = TradeStatus.CANCELLED
            await self.db.flush()
            
            logger.info(f"Order cancelled: {order_id}")
            
            return OrderResult(
                success=True,
                order_id=order_id,
                message="Order cancelled successfully",
                trade=trade
            )
            
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return OrderResult(
                success=False,
                message="Error cancelling order",
                errors=[str(e)]
            )
    
    async def get_pending_orders(
        self, 
        portfolio_id: Optional[int] = None
    ) -> List[Trade]:
        """
        Get all pending orders.
        
        Args:
            portfolio_id: Optional filter by portfolio
            
        Returns:
            List of pending orders
        """
        query = select(Trade).where(Trade.status == TradeStatus.PENDING)
        
        if portfolio_id:
            query = query.where(Trade.portfolio_id == portfolio_id)
        
        query = query.order_by(Trade.created_at)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_order(self, order_id: int) -> Optional[Trade]:
        """Get order by ID."""
        result = await self.db.execute(
            select(Trade).where(Trade.id == order_id)
        )
        return result.scalar_one_or_none()
    
    async def get_orders_by_portfolio(
        self, 
        portfolio_id: int,
        status: Optional[TradeStatus] = None,
        limit: int = 100
    ) -> List[Trade]:
        """
        Get orders for a portfolio.
        
        Args:
            portfolio_id: Portfolio ID
            status: Optional status filter
            limit: Maximum number of orders to return
            
        Returns:
            List of orders
        """
        query = select(Trade).where(Trade.portfolio_id == portfolio_id)
        
        if status:
            query = query.where(Trade.status == status)
        
        query = query.order_by(Trade.created_at.desc()).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
