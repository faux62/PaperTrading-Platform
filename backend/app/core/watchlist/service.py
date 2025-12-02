"""
PaperTrading Platform - Watchlist Service
Business logic for watchlist operations
"""
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, insert
from sqlalchemy.orm import selectinload

from app.db.models.watchlist import Watchlist, watchlist_symbols


class WatchlistService:
    """Service for watchlist business logic."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_watchlist(
        self,
        user_id: int,
        name: str,
        description: Optional[str] = None
    ) -> Watchlist:
        """Create a new watchlist for user."""
        watchlist = Watchlist(
            user_id=user_id,
            name=name,
            description=description
        )
        self.db.add(watchlist)
        await self.db.commit()
        await self.db.refresh(watchlist)
        return watchlist
    
    async def get_watchlist(
        self,
        watchlist_id: int,
        user_id: int
    ) -> Optional[Watchlist]:
        """Get watchlist by ID for specific user."""
        stmt = select(Watchlist).where(
            Watchlist.id == watchlist_id,
            Watchlist.user_id == user_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_watchlists(self, user_id: int) -> list[Watchlist]:
        """Get all watchlists for user."""
        stmt = select(Watchlist).where(
            Watchlist.user_id == user_id
        ).order_by(Watchlist.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def update_watchlist(
        self,
        watchlist_id: int,
        user_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[Watchlist]:
        """Update watchlist details."""
        watchlist = await self.get_watchlist(watchlist_id, user_id)
        if not watchlist:
            return None
        
        if name is not None:
            watchlist.name = name
        if description is not None:
            watchlist.description = description
        
        watchlist.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(watchlist)
        return watchlist
    
    async def delete_watchlist(
        self,
        watchlist_id: int,
        user_id: int
    ) -> bool:
        """Delete a watchlist."""
        watchlist = await self.get_watchlist(watchlist_id, user_id)
        if not watchlist:
            return False
        
        # Delete symbols first
        await self.db.execute(
            delete(watchlist_symbols).where(
                watchlist_symbols.c.watchlist_id == watchlist_id
            )
        )
        
        await self.db.delete(watchlist)
        await self.db.commit()
        return True
    
    async def get_watchlist_symbols(self, watchlist_id: int) -> list[dict]:
        """Get all symbols in a watchlist."""
        stmt = select(
            watchlist_symbols.c.symbol,
            watchlist_symbols.c.added_at
        ).where(watchlist_symbols.c.watchlist_id == watchlist_id)
        
        result = await self.db.execute(stmt)
        return [
            {"symbol": row.symbol, "added_at": row.added_at}
            for row in result.fetchall()
        ]
    
    async def add_symbol(
        self,
        watchlist_id: int,
        user_id: int,
        symbol: str
    ) -> bool:
        """Add a symbol to watchlist."""
        # Verify ownership
        watchlist = await self.get_watchlist(watchlist_id, user_id)
        if not watchlist:
            return False
        
        # Check if symbol already exists
        stmt = select(watchlist_symbols).where(
            watchlist_symbols.c.watchlist_id == watchlist_id,
            watchlist_symbols.c.symbol == symbol.upper()
        )
        result = await self.db.execute(stmt)
        if result.first():
            return True  # Already exists
        
        # Add symbol
        await self.db.execute(
            insert(watchlist_symbols).values(
                watchlist_id=watchlist_id,
                symbol=symbol.upper(),
                added_at=datetime.utcnow()
            )
        )
        
        # Update watchlist timestamp
        watchlist.updated_at = datetime.utcnow()
        await self.db.commit()
        return True
    
    async def remove_symbol(
        self,
        watchlist_id: int,
        user_id: int,
        symbol: str
    ) -> bool:
        """Remove a symbol from watchlist."""
        # Verify ownership
        watchlist = await self.get_watchlist(watchlist_id, user_id)
        if not watchlist:
            return False
        
        result = await self.db.execute(
            delete(watchlist_symbols).where(
                watchlist_symbols.c.watchlist_id == watchlist_id,
                watchlist_symbols.c.symbol == symbol.upper()
            )
        )
        
        if result.rowcount > 0:
            watchlist.updated_at = datetime.utcnow()
            await self.db.commit()
            return True
        
        return False
    
    async def get_all_user_symbols(self, user_id: int) -> list[str]:
        """Get all unique symbols across user's watchlists."""
        stmt = select(watchlist_symbols.c.symbol).distinct().join(
            Watchlist,
            watchlist_symbols.c.watchlist_id == Watchlist.id
        ).where(Watchlist.user_id == user_id)
        
        result = await self.db.execute(stmt)
        return [row.symbol for row in result.fetchall()]
    
    async def symbol_in_any_watchlist(
        self,
        user_id: int,
        symbol: str
    ) -> bool:
        """Check if symbol is in any of user's watchlists."""
        symbols = await self.get_all_user_symbols(user_id)
        return symbol.upper() in symbols
