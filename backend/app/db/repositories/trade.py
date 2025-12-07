"""
PaperTrading Platform - Trade Repository

Repository for trade/order database operations.
Handles trade logging, history queries, and statistics.
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload

from app.db.models.trade import Trade, TradeType, OrderType, TradeStatus

logger = logging.getLogger(__name__)


class TradeRepository:
    """
    Trade Repository
    
    Handles all database operations for trades/orders:
    - CRUD operations
    - Query by various filters
    - Trade statistics
    - History retrieval
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ==================== CREATE ====================
    
    async def create(self, trade: Trade) -> Trade:
        """Create a new trade record."""
        self.db.add(trade)
        await self.db.flush()
        await self.db.refresh(trade)
        return trade
    
    async def create_trade(
        self,
        portfolio_id: int,
        symbol: str,
        trade_type: TradeType,
        quantity: Decimal,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[Decimal] = None,
        exchange: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Trade:
        """Create a new trade with specified parameters."""
        trade = Trade(
            portfolio_id=portfolio_id,
            symbol=symbol.upper(),
            exchange=exchange,
            trade_type=trade_type,
            order_type=order_type,
            quantity=quantity,
            price=price,
            status=TradeStatus.PENDING,
            created_at=datetime.utcnow()
        )
        
        if notes:
            trade.notes = notes
        
        return await self.create(trade)
    
    # ==================== READ ====================
    
    async def get_by_id(self, trade_id: int) -> Optional[Trade]:
        """Get trade by ID."""
        result = await self.db.execute(
            select(Trade).where(Trade.id == trade_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_portfolio(
        self,
        portfolio_id: int,
        status: Optional[TradeStatus] = None,
        trade_type: Optional[TradeType] = None,
        symbol: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Trade]:
        """
        Get trades for a portfolio with optional filters.
        
        Args:
            portfolio_id: Portfolio ID
            status: Optional status filter
            trade_type: Optional trade type filter (BUY/SELL)
            symbol: Optional symbol filter
            start_date: Optional start date filter (inclusive)
            end_date: Optional end date filter (inclusive)
            limit: Max results
            offset: Pagination offset
            
        Returns:
            List of trades
        """
        query = select(Trade).where(Trade.portfolio_id == portfolio_id)
        
        if status:
            query = query.where(Trade.status == status)
        
        if trade_type:
            query = query.where(Trade.trade_type == trade_type)
        
        if symbol:
            query = query.where(Trade.symbol == symbol.upper())
        
        if start_date:
            query = query.where(Trade.created_at >= start_date)
        
        if end_date:
            query = query.where(Trade.created_at <= end_date)
        
        query = query.order_by(desc(Trade.created_at)).limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_pending_orders(
        self,
        portfolio_id: Optional[int] = None
    ) -> List[Trade]:
        """Get all pending orders, optionally filtered by portfolio."""
        query = select(Trade).where(Trade.status == TradeStatus.PENDING)
        
        if portfolio_id:
            query = query.where(Trade.portfolio_id == portfolio_id)
        
        query = query.order_by(Trade.created_at)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_executed_trades(
        self,
        portfolio_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Trade]:
        """Get executed trades in date range."""
        query = select(Trade).where(
            Trade.portfolio_id == portfolio_id,
            Trade.status == TradeStatus.EXECUTED
        )
        
        if start_date:
            query = query.where(Trade.executed_at >= start_date)
        
        if end_date:
            query = query.where(Trade.executed_at <= end_date)
        
        query = query.order_by(desc(Trade.executed_at)).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_trades_by_symbol(
        self,
        portfolio_id: int,
        symbol: str,
        limit: int = 50
    ) -> List[Trade]:
        """Get trade history for a specific symbol."""
        result = await self.db.execute(
            select(Trade)
            .where(
                Trade.portfolio_id == portfolio_id,
                Trade.symbol == symbol.upper()
            )
            .order_by(desc(Trade.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_recent_trades(
        self,
        portfolio_id: int,
        days: int = 7,
        limit: int = 50
    ) -> List[Trade]:
        """Get recent trades in the last N days."""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        result = await self.db.execute(
            select(Trade)
            .where(
                Trade.portfolio_id == portfolio_id,
                Trade.created_at >= start_date
            )
            .order_by(desc(Trade.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())
    
    # ==================== UPDATE ====================
    
    async def update_status(
        self,
        trade_id: int,
        status: TradeStatus
    ) -> Optional[Trade]:
        """Update trade status."""
        trade = await self.get_by_id(trade_id)
        if trade:
            trade.status = status
            await self.db.flush()
        return trade
    
    async def mark_executed(
        self,
        trade_id: int,
        executed_price: Decimal,
        executed_quantity: Decimal,
        total_value: Decimal,
        commission: Decimal = Decimal("0"),
        realized_pnl: Optional[Decimal] = None
    ) -> Optional[Trade]:
        """Mark trade as executed with execution details."""
        trade = await self.get_by_id(trade_id)
        if trade:
            trade.status = TradeStatus.EXECUTED
            trade.executed_price = executed_price
            trade.executed_quantity = executed_quantity
            trade.total_value = total_value
            trade.commission = commission
            trade.executed_at = datetime.utcnow()
            
            if realized_pnl is not None:
                trade.realized_pnl = realized_pnl
            
            await self.db.flush()
        return trade
    
    async def cancel_order(self, trade_id: int) -> Optional[Trade]:
        """Cancel a pending order."""
        trade = await self.get_by_id(trade_id)
        if trade and trade.status == TradeStatus.PENDING:
            trade.status = TradeStatus.CANCELLED
            await self.db.flush()
        return trade
    
    async def update_notes(
        self,
        trade_id: int,
        notes: str
    ) -> Optional[Trade]:
        """Update trade notes."""
        trade = await self.get_by_id(trade_id)
        if trade:
            trade.notes = notes
            await self.db.flush()
        return trade
    
    # ==================== DELETE ====================
    
    async def delete(self, trade_id: int) -> bool:
        """Delete a trade record (use with caution)."""
        trade = await self.get_by_id(trade_id)
        if trade:
            await self.db.delete(trade)
            await self.db.flush()
            return True
        return False
    
    # ==================== STATISTICS ====================
    
    async def count_by_portfolio(
        self,
        portfolio_id: int,
        status: Optional[TradeStatus] = None
    ) -> int:
        """Count trades in portfolio."""
        query = select(func.count(Trade.id)).where(
            Trade.portfolio_id == portfolio_id
        )
        
        if status:
            query = query.where(Trade.status == status)
        
        result = await self.db.execute(query)
        return result.scalar() or 0
    
    async def get_total_volume(
        self,
        portfolio_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Decimal:
        """Get total trading volume."""
        query = select(func.sum(Trade.total_value)).where(
            Trade.portfolio_id == portfolio_id,
            Trade.status == TradeStatus.EXECUTED
        )
        
        if start_date:
            query = query.where(Trade.executed_at >= start_date)
        
        if end_date:
            query = query.where(Trade.executed_at <= end_date)
        
        result = await self.db.execute(query)
        return result.scalar() or Decimal("0")
    
    async def get_realized_pnl_total(
        self,
        portfolio_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Decimal:
        """Get total realized P&L."""
        query = select(func.sum(Trade.realized_pnl)).where(
            Trade.portfolio_id == portfolio_id,
            Trade.status == TradeStatus.EXECUTED,
            Trade.trade_type == TradeType.SELL
        )
        
        if start_date:
            query = query.where(Trade.executed_at >= start_date)
        
        if end_date:
            query = query.where(Trade.executed_at <= end_date)
        
        result = await self.db.execute(query)
        return result.scalar() or Decimal("0")
    
    async def get_trade_summary(
        self,
        portfolio_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get trade summary statistics."""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get executed trades
        trades = await self.get_executed_trades(
            portfolio_id, start_date, limit=1000
        )
        
        if not trades:
            return {
                'total_trades': 0,
                'buy_trades': 0,
                'sell_trades': 0,
                'total_volume': Decimal("0"),
                'realized_pnl': Decimal("0"),
                'avg_trade_size': Decimal("0"),
                'most_traded_symbols': []
            }
        
        buy_trades = [t for t in trades if t.trade_type == TradeType.BUY]
        sell_trades = [t for t in trades if t.trade_type == TradeType.SELL]
        
        total_volume = sum(t.total_value or Decimal("0") for t in trades)
        realized_pnl = sum(
            t.realized_pnl or Decimal("0") 
            for t in sell_trades
        )
        
        # Symbol frequency
        symbol_counts = {}
        for t in trades:
            symbol_counts[t.symbol] = symbol_counts.get(t.symbol, 0) + 1
        
        most_traded = sorted(
            symbol_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return {
            'total_trades': len(trades),
            'buy_trades': len(buy_trades),
            'sell_trades': len(sell_trades),
            'total_volume': total_volume,
            'realized_pnl': realized_pnl,
            'avg_trade_size': total_volume / len(trades) if trades else Decimal("0"),
            'most_traded_symbols': [
                {'symbol': s, 'count': c} for s, c in most_traded
            ],
            'period_days': days
        }
    
    async def get_daily_trade_counts(
        self,
        portfolio_id: int,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get daily trade counts for charting."""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # This is a simplified version - production would use proper date grouping
        trades = await self.get_executed_trades(
            portfolio_id, start_date, limit=1000
        )
        
        daily_counts = {}
        for trade in trades:
            if trade.executed_at:
                day = trade.executed_at.date()
                if day not in daily_counts:
                    daily_counts[day] = {'buys': 0, 'sells': 0, 'volume': Decimal("0")}
                
                if trade.trade_type == TradeType.BUY:
                    daily_counts[day]['buys'] += 1
                else:
                    daily_counts[day]['sells'] += 1
                
                daily_counts[day]['volume'] += trade.total_value or Decimal("0")
        
        return [
            {
                'date': str(day),
                'buys': data['buys'],
                'sells': data['sells'],
                'total': data['buys'] + data['sells'],
                'volume': data['volume']
            }
            for day, data in sorted(daily_counts.items())
        ]
