"""
Portfolio Service

Core business logic for portfolio management including CRUD operations,
value calculations, performance metrics, and position management.
"""
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_
from loguru import logger

from app.db.models.portfolio import Portfolio, RiskProfile as DBRiskProfile
from app.db.models.position import Position
from app.db.models.trade import Trade, TradeType, TradeStatus
from app.core.portfolio.risk_profiles import get_risk_profile, RiskProfile, get_profile_summary
from app.core.portfolio.allocation import AssetAllocator, AllocationAnalysis
from app.core.portfolio.constraints import ConstraintsValidator, PortfolioSnapshot, ValidationResult


class PortfolioService:
    """
    Service for portfolio management operations.
    
    Handles portfolio CRUD, position management, value calculations,
    and integrates with risk profiles and allocation logic.
    
    Usage:
        service = PortfolioService(db_session)
        
        # Create portfolio
        portfolio = await service.create_portfolio(
            user_id=1,
            name="My Portfolio",
            risk_profile="balanced",
            initial_capital=Decimal("100000"),
        )
        
        # Get portfolio with positions
        portfolio_data = await service.get_portfolio_with_positions(portfolio_id=1)
        
        # Calculate performance
        metrics = await service.calculate_performance(portfolio_id=1)
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ==================== CRUD Operations ====================
    
    async def create_portfolio(
        self,
        user_id: int,
        name: str,
        risk_profile: str = "balanced",
        initial_capital: Decimal = Decimal("100000"),
        description: Optional[str] = None,
        currency: str = "USD",
    ) -> Portfolio:
        """
        Create a new portfolio.
        
        Args:
            user_id: Owner user ID
            name: Portfolio name
            risk_profile: One of 'aggressive', 'balanced', 'prudent'
            initial_capital: Starting capital
            description: Optional description
            currency: Base currency (default USD)
            
        Returns:
            Created Portfolio object
        """
        # Validate risk profile
        profile_enum = DBRiskProfile(risk_profile.lower())
        
        portfolio = Portfolio(
            user_id=user_id,
            name=name,
            description=description,
            risk_profile=profile_enum,
            initial_capital=initial_capital,
            cash_balance=initial_capital,
            currency=currency,
            is_active="active",
        )
        
        self.db.add(portfolio)
        await self.db.commit()
        await self.db.refresh(portfolio)
        
        logger.info(f"Created portfolio {portfolio.id} for user {user_id}")
        return portfolio
    
    async def get_portfolio(self, portfolio_id: int) -> Optional[Portfolio]:
        """Get portfolio by ID."""
        result = await self.db.execute(
            select(Portfolio).where(Portfolio.id == portfolio_id)
        )
        return result.scalar_one_or_none()
    
    async def get_portfolios_by_user(self, user_id: int) -> list[Portfolio]:
        """Get all portfolios for a user."""
        result = await self.db.execute(
            select(Portfolio)
            .where(Portfolio.user_id == user_id)
            .order_by(Portfolio.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def update_portfolio(
        self,
        portfolio_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        risk_profile: Optional[str] = None,
        is_active: Optional[str] = None,
    ) -> Optional[Portfolio]:
        """Update portfolio fields."""
        portfolio = await self.get_portfolio(portfolio_id)
        if not portfolio:
            return None
        
        if name is not None:
            portfolio.name = name
        if description is not None:
            portfolio.description = description
        if risk_profile is not None:
            portfolio.risk_profile = DBRiskProfile(risk_profile.lower())
        if is_active is not None:
            portfolio.is_active = is_active
        
        portfolio.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(portfolio)
        
        return portfolio
    
    async def delete_portfolio(self, portfolio_id: int) -> bool:
        """Delete a portfolio and all associated data."""
        portfolio = await self.get_portfolio(portfolio_id)
        if not portfolio:
            return False
        
        await self.db.delete(portfolio)
        await self.db.commit()
        
        logger.info(f"Deleted portfolio {portfolio_id}")
        return True
    
    # ==================== Position Management ====================
    
    async def get_positions(self, portfolio_id: int) -> list[Position]:
        """Get all positions for a portfolio."""
        result = await self.db.execute(
            select(Position)
            .where(Position.portfolio_id == portfolio_id)
            .order_by(Position.market_value.desc())
        )
        return list(result.scalars().all())
    
    async def get_position(
        self,
        portfolio_id: int,
        symbol: str,
    ) -> Optional[Position]:
        """Get a specific position by symbol."""
        result = await self.db.execute(
            select(Position).where(
                and_(
                    Position.portfolio_id == portfolio_id,
                    Position.symbol == symbol.upper(),
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def update_position_price(
        self,
        portfolio_id: int,
        symbol: str,
        current_price: Decimal,
    ) -> Optional[Position]:
        """Update position with current market price and recalculate P&L."""
        position = await self.get_position(portfolio_id, symbol)
        if not position:
            return None
        
        position.current_price = current_price
        position.market_value = position.quantity * current_price
        
        # Calculate unrealized P&L
        cost_basis = position.quantity * position.avg_cost
        position.unrealized_pnl = position.market_value - cost_basis
        
        if cost_basis > 0:
            position.unrealized_pnl_percent = (
                position.unrealized_pnl / cost_basis * 100
            )
        else:
            position.unrealized_pnl_percent = Decimal("0")
        
        position.updated_at = datetime.utcnow()
        await self.db.commit()
        
        return position
    
    async def update_all_position_prices(
        self,
        portfolio_id: int,
        prices: dict[str, Decimal],
    ) -> int:
        """Update prices for multiple positions at once."""
        updated_count = 0
        
        for symbol, price in prices.items():
            position = await self.update_position_price(portfolio_id, symbol, price)
            if position:
                updated_count += 1
        
        return updated_count
    
    # ==================== Portfolio Value & Metrics ====================
    
    async def calculate_portfolio_value(
        self,
        portfolio_id: int,
    ) -> dict[str, Decimal]:
        """
        Calculate total portfolio value.
        
        Returns dict with:
        - total_value: Total portfolio value
        - equity_value: Value of all positions
        - cash_balance: Available cash
        - unrealized_pnl: Total unrealized P&L
        """
        portfolio = await self.get_portfolio(portfolio_id)
        if not portfolio:
            return {}
        
        positions = await self.get_positions(portfolio_id)
        
        equity_value = sum(
            pos.market_value for pos in positions
        ) or Decimal("0")
        
        unrealized_pnl = sum(
            pos.unrealized_pnl for pos in positions
        ) or Decimal("0")
        
        total_value = equity_value + portfolio.cash_balance
        
        return {
            "total_value": total_value,
            "equity_value": equity_value,
            "cash_balance": portfolio.cash_balance,
            "unrealized_pnl": unrealized_pnl,
        }
    
    async def calculate_performance(
        self,
        portfolio_id: int,
    ) -> dict[str, Any]:
        """
        Calculate portfolio performance metrics.
        
        Returns comprehensive performance data including
        returns, P&L, and allocation breakdown.
        """
        portfolio = await self.get_portfolio(portfolio_id)
        if not portfolio:
            return {}
        
        positions = await self.get_positions(portfolio_id)
        values = await self.calculate_portfolio_value(portfolio_id)
        
        total_value = values.get("total_value", Decimal("0"))
        initial = portfolio.initial_capital
        
        # Calculate returns
        total_return = total_value - initial
        total_return_percent = (
            (total_return / initial * 100) if initial > 0 else Decimal("0")
        )
        
        # Get realized P&L from trades
        realized_pnl = await self._calculate_realized_pnl(portfolio_id)
        
        # Allocation breakdown
        allocation = {}
        for pos in positions:
            weight = (
                (pos.market_value / total_value * 100) if total_value > 0 
                else Decimal("0")
            )
            allocation[pos.symbol] = {
                "market_value": float(pos.market_value),
                "weight": float(weight),
                "unrealized_pnl": float(pos.unrealized_pnl),
                "unrealized_pnl_percent": float(pos.unrealized_pnl_percent),
            }
        
        # Cash allocation
        cash_weight = (
            (portfolio.cash_balance / total_value * 100) if total_value > 0 
            else Decimal("100")
        )
        
        return {
            "portfolio_id": portfolio_id,
            "name": portfolio.name,
            "risk_profile": portfolio.risk_profile.value,
            "currency": portfolio.currency,
            "created_at": portfolio.created_at.isoformat(),
            
            # Values
            "initial_capital": float(initial),
            "total_value": float(total_value),
            "equity_value": float(values.get("equity_value", 0)),
            "cash_balance": float(portfolio.cash_balance),
            "cash_weight": float(cash_weight),
            
            # Returns
            "total_return": float(total_return),
            "total_return_percent": float(total_return_percent),
            "realized_pnl": float(realized_pnl),
            "unrealized_pnl": float(values.get("unrealized_pnl", 0)),
            
            # Positions
            "position_count": len(positions),
            "allocation": allocation,
        }
    
    async def _calculate_realized_pnl(self, portfolio_id: int) -> Decimal:
        """Calculate total realized P&L from executed trades."""
        result = await self.db.execute(
            select(func.sum(Trade.realized_pnl))
            .where(
                and_(
                    Trade.portfolio_id == portfolio_id,
                    Trade.status == TradeStatus.EXECUTED,
                    Trade.realized_pnl.isnot(None),
                )
            )
        )
        total = result.scalar_one_or_none()
        return total or Decimal("0")
    
    # ==================== Allocation Analysis ====================
    
    async def analyze_allocation(
        self,
        portfolio_id: int,
    ) -> AllocationAnalysis:
        """
        Analyze portfolio allocation vs risk profile targets.
        
        Returns allocation analysis with drift metrics
        and rebalancing recommendations.
        """
        portfolio = await self.get_portfolio(portfolio_id)
        if not portfolio:
            return AllocationAnalysis(
                total_value=Decimal("0"),
                cash_balance=Decimal("0"),
                asset_class_allocations=[],
                sector_allocations=[],
                needs_rebalancing=False,
                max_drift=Decimal("0"),
                rebalance_recommendations=[],
            )
        
        positions = await self.get_positions(portfolio_id)
        values = await self.calculate_portfolio_value(portfolio_id)
        
        # Convert positions to dict format
        position_dicts = [
            {
                "symbol": pos.symbol,
                "market_value": pos.market_value,
                "sector": pos.exchange,  # TODO: Add sector field to position model
                "country": "us",  # TODO: Add country field or derive from exchange
            }
            for pos in positions
        ]
        
        allocator = AssetAllocator(portfolio.risk_profile.value)
        return allocator.analyze_allocation(
            total_value=values.get("total_value", Decimal("0")),
            cash_balance=portfolio.cash_balance,
            positions=position_dicts,
        )
    
    async def validate_trade(
        self,
        portfolio_id: int,
        symbol: str,
        trade_type: str,
        quantity: Decimal,
        price: Decimal,
        sector: Optional[str] = None,
        country: Optional[str] = None,
    ) -> ValidationResult:
        """
        Validate a proposed trade against portfolio constraints.
        
        Returns validation result with any violations or warnings.
        """
        portfolio = await self.get_portfolio(portfolio_id)
        if not portfolio:
            result = ValidationResult(is_valid=False)
            return result
        
        positions = await self.get_positions(portfolio_id)
        values = await self.calculate_portfolio_value(portfolio_id)
        
        # Build snapshot
        position_dicts = [
            {
                "symbol": pos.symbol,
                "quantity": pos.quantity,
                "market_value": pos.market_value,
                "sector": sector or "other",
                "country": country or "us",
            }
            for pos in positions
        ]
        
        snapshot = PortfolioSnapshot(
            total_value=values.get("total_value", Decimal("0")),
            cash_balance=portfolio.cash_balance,
            positions=position_dicts,
        )
        
        validator = ConstraintsValidator(portfolio.risk_profile.value)
        return validator.validate_trade(
            snapshot=snapshot,
            symbol=symbol,
            trade_type=trade_type,
            quantity=quantity,
            price=price,
            sector=sector,
            country=country,
        )
    
    # ==================== Portfolio with Full Data ====================
    
    async def get_portfolio_with_positions(
        self,
        portfolio_id: int,
    ) -> Optional[dict[str, Any]]:
        """
        Get portfolio with all positions and calculated values.
        
        Returns comprehensive portfolio data suitable for API response.
        """
        portfolio = await self.get_portfolio(portfolio_id)
        if not portfolio:
            return None
        
        positions = await self.get_positions(portfolio_id)
        performance = await self.calculate_performance(portfolio_id)
        
        # Get risk profile summary
        profile_summary = get_profile_summary(portfolio.risk_profile.value)
        
        return {
            "id": portfolio.id,
            "user_id": portfolio.user_id,
            "name": portfolio.name,
            "description": portfolio.description,
            "risk_profile": portfolio.risk_profile.value,
            "risk_profile_summary": profile_summary,
            "initial_capital": float(portfolio.initial_capital),
            "cash_balance": float(portfolio.cash_balance),
            "currency": portfolio.currency,
            "is_active": portfolio.is_active,
            "created_at": portfolio.created_at.isoformat(),
            "updated_at": portfolio.updated_at.isoformat() if portfolio.updated_at else None,
            
            # Positions
            "positions": [
                {
                    "id": pos.id,
                    "symbol": pos.symbol,
                    "exchange": pos.exchange,
                    "quantity": float(pos.quantity),
                    "avg_cost": float(pos.avg_cost),
                    "current_price": float(pos.current_price),
                    "market_value": float(pos.market_value),
                    "unrealized_pnl": float(pos.unrealized_pnl),
                    "unrealized_pnl_percent": float(pos.unrealized_pnl_percent),
                    "opened_at": pos.opened_at.isoformat() if pos.opened_at else None,
                }
                for pos in positions
            ],
            
            # Performance
            **performance,
        }
    
    async def get_portfolio_summary(
        self,
        portfolio_id: int,
    ) -> Optional[dict[str, Any]]:
        """
        Get a summary of the portfolio for list views.
        
        Returns lightweight summary without full position details.
        """
        portfolio = await self.get_portfolio(portfolio_id)
        if not portfolio:
            return None
        
        values = await self.calculate_portfolio_value(portfolio_id)
        positions = await self.get_positions(portfolio_id)
        
        total_value = values.get("total_value", Decimal("0"))
        initial = portfolio.initial_capital
        total_return = total_value - initial
        total_return_percent = (
            (total_return / initial * 100) if initial > 0 else Decimal("0")
        )
        
        return {
            "id": portfolio.id,
            "name": portfolio.name,
            "risk_profile": portfolio.risk_profile.value,
            "total_value": float(total_value),
            "total_return": float(total_return),
            "total_return_percent": float(total_return_percent),
            "position_count": len(positions),
            "is_active": portfolio.is_active,
            "currency": portfolio.currency,
        }


# ==================== Factory Function ====================

def get_portfolio_service(db: AsyncSession) -> PortfolioService:
    """Factory function to create PortfolioService."""
    return PortfolioService(db)
