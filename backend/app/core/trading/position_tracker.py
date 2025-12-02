"""
PaperTrading Platform - Position Tracker

Tracks open and closed positions, calculates current values,
and manages position lifecycle.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.models.position import Position
from app.db.models.trade import Trade, TradeType, TradeStatus
from app.db.models.portfolio import Portfolio

logger = logging.getLogger(__name__)


@dataclass
class PositionSummary:
    """Summary of a single position."""
    symbol: str
    exchange: Optional[str]
    quantity: Decimal
    average_cost: Decimal
    cost_basis: Decimal
    current_price: Optional[Decimal]
    current_value: Optional[Decimal]
    unrealized_pnl: Optional[Decimal]
    unrealized_pnl_pct: Optional[Decimal]
    day_change: Optional[Decimal]
    day_change_pct: Optional[Decimal]
    weight_pct: Optional[Decimal]
    created_at: datetime
    updated_at: datetime


@dataclass
class PortfolioPositions:
    """Summary of all positions in a portfolio."""
    portfolio_id: int
    positions: List[PositionSummary]
    total_positions: int
    total_cost_basis: Decimal
    total_current_value: Optional[Decimal]
    total_unrealized_pnl: Optional[Decimal]
    total_unrealized_pnl_pct: Optional[Decimal]


class PositionTracker:
    """
    Position Tracker
    
    Responsible for:
    - Tracking open positions
    - Calculating position values and P&L
    - Managing position history
    - Aggregating portfolio position data
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_position(
        self, 
        portfolio_id: int, 
        symbol: str
    ) -> Optional[Position]:
        """
        Get a specific position.
        
        Args:
            portfolio_id: Portfolio ID
            symbol: Stock symbol
            
        Returns:
            Position or None if not found
        """
        result = await self.db.execute(
            select(Position).where(
                Position.portfolio_id == portfolio_id,
                Position.symbol == symbol.upper()
            )
        )
        return result.scalar_one_or_none()
    
    async def get_all_positions(
        self, 
        portfolio_id: int
    ) -> List[Position]:
        """
        Get all positions for a portfolio.
        
        Args:
            portfolio_id: Portfolio ID
            
        Returns:
            List of positions
        """
        result = await self.db.execute(
            select(Position)
            .where(Position.portfolio_id == portfolio_id)
            .order_by(Position.symbol)
        )
        return list(result.scalars().all())
    
    async def get_position_summary(
        self,
        position: Position,
        current_price: Optional[Decimal] = None,
        previous_close: Optional[Decimal] = None,
        portfolio_value: Optional[Decimal] = None
    ) -> PositionSummary:
        """
        Get summary for a position with calculated metrics.
        
        Args:
            position: Position to summarize
            current_price: Current market price (optional)
            previous_close: Previous day close price (optional)
            portfolio_value: Total portfolio value for weight calculation
            
        Returns:
            PositionSummary with all calculated fields
        """
        cost_basis = position.quantity * position.average_cost
        
        # Calculate current value and unrealized P&L if price available
        current_value = None
        unrealized_pnl = None
        unrealized_pnl_pct = None
        day_change = None
        day_change_pct = None
        weight_pct = None
        
        if current_price is not None:
            current_value = position.quantity * current_price
            unrealized_pnl = current_value - cost_basis
            
            if cost_basis > 0:
                unrealized_pnl_pct = (unrealized_pnl / cost_basis) * 100
        
        if current_price is not None and previous_close is not None:
            day_change = (current_price - previous_close) * position.quantity
            if previous_close > 0:
                day_change_pct = ((current_price - previous_close) / previous_close) * 100
        
        if current_value is not None and portfolio_value and portfolio_value > 0:
            weight_pct = (current_value / portfolio_value) * 100
        
        return PositionSummary(
            symbol=position.symbol,
            exchange=position.exchange,
            quantity=position.quantity,
            average_cost=position.average_cost,
            cost_basis=cost_basis,
            current_price=current_price,
            current_value=current_value,
            unrealized_pnl=unrealized_pnl,
            unrealized_pnl_pct=unrealized_pnl_pct,
            day_change=day_change,
            day_change_pct=day_change_pct,
            weight_pct=weight_pct,
            created_at=position.created_at,
            updated_at=position.updated_at
        )
    
    async def get_portfolio_positions(
        self,
        portfolio_id: int,
        prices: Optional[Dict[str, Decimal]] = None,
        previous_closes: Optional[Dict[str, Decimal]] = None
    ) -> PortfolioPositions:
        """
        Get all positions for a portfolio with summaries.
        
        Args:
            portfolio_id: Portfolio ID
            prices: Dict of symbol -> current price
            previous_closes: Dict of symbol -> previous close
            
        Returns:
            PortfolioPositions with all position summaries
        """
        positions = await self.get_all_positions(portfolio_id)
        
        # Calculate total portfolio value first for weight percentages
        total_cost_basis = Decimal("0")
        total_current_value = Decimal("0") if prices else None
        
        for pos in positions:
            total_cost_basis += pos.quantity * pos.average_cost
            if prices and pos.symbol in prices:
                total_current_value += pos.quantity * prices[pos.symbol]
        
        # Build position summaries
        summaries = []
        for pos in positions:
            current_price = prices.get(pos.symbol) if prices else None
            prev_close = previous_closes.get(pos.symbol) if previous_closes else None
            
            summary = await self.get_position_summary(
                pos,
                current_price=current_price,
                previous_close=prev_close,
                portfolio_value=total_current_value
            )
            summaries.append(summary)
        
        # Calculate total unrealized P&L
        total_unrealized_pnl = None
        total_unrealized_pnl_pct = None
        
        if total_current_value is not None:
            total_unrealized_pnl = total_current_value - total_cost_basis
            if total_cost_basis > 0:
                total_unrealized_pnl_pct = (total_unrealized_pnl / total_cost_basis) * 100
        
        return PortfolioPositions(
            portfolio_id=portfolio_id,
            positions=summaries,
            total_positions=len(positions),
            total_cost_basis=total_cost_basis,
            total_current_value=total_current_value,
            total_unrealized_pnl=total_unrealized_pnl,
            total_unrealized_pnl_pct=total_unrealized_pnl_pct
        )
    
    async def get_position_history(
        self,
        portfolio_id: int,
        symbol: str,
        limit: int = 50
    ) -> List[Trade]:
        """
        Get trade history for a specific position.
        
        Args:
            portfolio_id: Portfolio ID
            symbol: Stock symbol
            limit: Maximum number of trades to return
            
        Returns:
            List of trades for this position
        """
        result = await self.db.execute(
            select(Trade)
            .where(
                Trade.portfolio_id == portfolio_id,
                Trade.symbol == symbol.upper(),
                Trade.status == TradeStatus.EXECUTED
            )
            .order_by(Trade.executed_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_position_count(self, portfolio_id: int) -> int:
        """Get number of open positions in portfolio."""
        result = await self.db.execute(
            select(func.count(Position.id))
            .where(Position.portfolio_id == portfolio_id)
        )
        return result.scalar() or 0
    
    async def get_top_positions(
        self,
        portfolio_id: int,
        prices: Dict[str, Decimal],
        limit: int = 5,
        by: str = "value"
    ) -> List[PositionSummary]:
        """
        Get top positions by value or P&L.
        
        Args:
            portfolio_id: Portfolio ID
            prices: Dict of symbol -> current price
            limit: Number of positions to return
            by: Sort by "value", "pnl", or "weight"
            
        Returns:
            List of top position summaries
        """
        portfolio_positions = await self.get_portfolio_positions(
            portfolio_id, prices
        )
        
        positions = portfolio_positions.positions
        
        if by == "value":
            positions.sort(
                key=lambda p: p.current_value or Decimal("0"),
                reverse=True
            )
        elif by == "pnl":
            positions.sort(
                key=lambda p: p.unrealized_pnl or Decimal("0"),
                reverse=True
            )
        elif by == "weight":
            positions.sort(
                key=lambda p: p.weight_pct or Decimal("0"),
                reverse=True
            )
        
        return positions[:limit]
    
    async def get_position_allocation(
        self,
        portfolio_id: int,
        prices: Dict[str, Decimal]
    ) -> Dict[str, Decimal]:
        """
        Get position allocation percentages.
        
        Args:
            portfolio_id: Portfolio ID
            prices: Dict of symbol -> current price
            
        Returns:
            Dict of symbol -> allocation percentage
        """
        portfolio_positions = await self.get_portfolio_positions(
            portfolio_id, prices
        )
        
        allocation = {}
        for pos in portfolio_positions.positions:
            if pos.weight_pct is not None:
                allocation[pos.symbol] = pos.weight_pct
        
        return allocation
    
    async def check_position_exists(
        self,
        portfolio_id: int,
        symbol: str
    ) -> bool:
        """Check if a position exists in portfolio."""
        position = await self.get_position(portfolio_id, symbol)
        return position is not None and position.quantity > 0
    
    async def get_symbols_in_portfolio(self, portfolio_id: int) -> List[str]:
        """Get list of symbols with open positions."""
        positions = await self.get_all_positions(portfolio_id)
        return [pos.symbol for pos in positions if pos.quantity > 0]
