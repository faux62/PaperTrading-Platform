"""
Position Repository

Database operations for position management.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_
from loguru import logger

from app.db.models.position import Position


class PositionRepository:
    """
    Repository for Position database operations.
    
    Provides low-level CRUD operations for positions.
    For business logic, use PortfolioService instead.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(
        self,
        portfolio_id: int,
        symbol: str,
        quantity: Decimal,
        avg_cost: Decimal,
        exchange: Optional[str] = None,
    ) -> Position:
        """Create a new position."""
        position = Position(
            portfolio_id=portfolio_id,
            symbol=symbol.upper(),
            exchange=exchange,
            quantity=quantity,
            avg_cost=avg_cost,
            current_price=avg_cost,  # Initial price = cost
            market_value=quantity * avg_cost,
            unrealized_pnl=Decimal("0"),
            unrealized_pnl_percent=Decimal("0"),
        )
        
        self.db.add(position)
        await self.db.commit()
        await self.db.refresh(position)
        
        logger.info(f"Created position: {symbol} qty={quantity} in portfolio {portfolio_id}")
        return position
    
    async def get_by_id(self, position_id: int) -> Optional[Position]:
        """Get position by ID."""
        result = await self.db.execute(
            select(Position).where(Position.id == position_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_symbol(
        self,
        portfolio_id: int,
        symbol: str,
    ) -> Optional[Position]:
        """Get position by portfolio and symbol."""
        result = await self.db.execute(
            select(Position).where(
                and_(
                    Position.portfolio_id == portfolio_id,
                    Position.symbol == symbol.upper(),
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_all_by_portfolio(
        self,
        portfolio_id: int,
    ) -> list[Position]:
        """Get all positions for a portfolio."""
        result = await self.db.execute(
            select(Position)
            .where(Position.portfolio_id == portfolio_id)
            .order_by(Position.market_value.desc())
        )
        return list(result.scalars().all())
    
    async def update(
        self,
        position_id: int,
        quantity: Optional[Decimal] = None,
        avg_cost: Optional[Decimal] = None,
        current_price: Optional[Decimal] = None,
    ) -> Optional[Position]:
        """Update position fields."""
        position = await self.get_by_id(position_id)
        if not position:
            return None
        
        if quantity is not None:
            position.quantity = quantity
        if avg_cost is not None:
            position.avg_cost = avg_cost
        if current_price is not None:
            position.current_price = current_price
        
        # Recalculate derived fields
        position.market_value = position.quantity * position.current_price
        cost_basis = position.quantity * position.avg_cost
        position.unrealized_pnl = position.market_value - cost_basis
        position.unrealized_pnl_percent = (
            (position.unrealized_pnl / cost_basis * 100) if cost_basis > 0 
            else Decimal("0")
        )
        position.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(position)
        
        return position
    
    async def add_to_position(
        self,
        portfolio_id: int,
        symbol: str,
        quantity: Decimal,
        price: Decimal,
        exchange: Optional[str] = None,
    ) -> Position:
        """
        Add to an existing position or create new.
        
        Updates average cost using weighted average.
        """
        position = await self.get_by_symbol(portfolio_id, symbol)
        
        if position:
            # Calculate new average cost
            old_value = position.quantity * position.avg_cost
            new_value = quantity * price
            total_qty = position.quantity + quantity
            
            if total_qty > 0:
                new_avg_cost = (old_value + new_value) / total_qty
            else:
                new_avg_cost = price
            
            return await self.update(
                position_id=position.id,
                quantity=total_qty,
                avg_cost=new_avg_cost,
                current_price=price,
            )
        else:
            # Create new position
            return await self.create(
                portfolio_id=portfolio_id,
                symbol=symbol,
                quantity=quantity,
                avg_cost=price,
                exchange=exchange,
            )
    
    async def reduce_position(
        self,
        portfolio_id: int,
        symbol: str,
        quantity: Decimal,
    ) -> Optional[Position]:
        """
        Reduce position quantity (for sells).
        
        If quantity >= current quantity, deletes the position.
        Returns None if position was deleted.
        """
        position = await self.get_by_symbol(portfolio_id, symbol)
        if not position:
            raise ValueError(f"Position {symbol} not found in portfolio {portfolio_id}")
        
        new_quantity = position.quantity - quantity
        
        if new_quantity <= 0:
            # Close position entirely
            await self.delete(position.id)
            return None
        else:
            # Reduce position
            return await self.update(
                position_id=position.id,
                quantity=new_quantity,
            )
    
    async def delete(self, position_id: int) -> bool:
        """Delete a position."""
        position = await self.get_by_id(position_id)
        if not position:
            return False
        
        await self.db.delete(position)
        await self.db.commit()
        
        logger.info(f"Deleted position {position_id}")
        return True
    
    async def delete_all_by_portfolio(self, portfolio_id: int) -> int:
        """Delete all positions for a portfolio."""
        result = await self.db.execute(
            delete(Position).where(Position.portfolio_id == portfolio_id)
        )
        await self.db.commit()
        
        deleted_count = result.rowcount
        logger.info(f"Deleted {deleted_count} positions from portfolio {portfolio_id}")
        return deleted_count
    
    async def update_prices(
        self,
        portfolio_id: int,
        prices: dict[str, Decimal],
    ) -> int:
        """
        Update current prices for multiple positions.
        
        Args:
            portfolio_id: Portfolio ID
            prices: Dict mapping symbol to current price
            
        Returns:
            Number of positions updated
        """
        updated_count = 0
        
        for symbol, price in prices.items():
            position = await self.get_by_symbol(portfolio_id, symbol)
            if position:
                await self.update(
                    position_id=position.id,
                    current_price=price,
                )
                updated_count += 1
        
        return updated_count


def get_position_repository(db: AsyncSession) -> PositionRepository:
    """Factory function to create PositionRepository."""
    return PositionRepository(db)
