"""
PaperTrading Platform - P&L Calculator

Calculates realized and unrealized profit/loss,
performance metrics, and trading statistics.
"""
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.db.models.trade import Trade, TradeType, TradeStatus
from app.db.models.position import Position
from app.db.models.portfolio import Portfolio

logger = logging.getLogger(__name__)


class TimeFrame(str, Enum):
    """Time frame for P&L calculations."""
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    YTD = "ytd"
    ALL_TIME = "all_time"


@dataclass
class RealizedPnL:
    """Realized P&L from closed positions."""
    total: Decimal = Decimal("0")
    gross_profit: Decimal = Decimal("0")
    gross_loss: Decimal = Decimal("0")
    trade_count: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: Decimal = Decimal("0")
    avg_win: Decimal = Decimal("0")
    avg_loss: Decimal = Decimal("0")
    profit_factor: Optional[Decimal] = None
    largest_win: Decimal = Decimal("0")
    largest_loss: Decimal = Decimal("0")


@dataclass
class UnrealizedPnL:
    """Unrealized P&L from open positions."""
    total: Decimal = Decimal("0")
    by_position: Dict[str, Decimal] = field(default_factory=dict)
    positions_in_profit: int = 0
    positions_in_loss: int = 0
    largest_gain: Tuple[str, Decimal] = ("", Decimal("0"))
    largest_loss: Tuple[str, Decimal] = ("", Decimal("0"))


@dataclass
class PortfolioPnL:
    """Combined P&L for portfolio."""
    portfolio_id: int
    realized: RealizedPnL
    unrealized: UnrealizedPnL
    total_pnl: Decimal
    total_pnl_pct: Decimal
    initial_capital: Decimal
    current_value: Decimal
    cash_balance: Decimal
    time_frame: TimeFrame
    as_of: datetime


@dataclass
class DailyPnL:
    """Daily P&L record."""
    date: date
    realized: Decimal
    unrealized: Decimal
    total: Decimal
    portfolio_value: Decimal
    daily_return_pct: Decimal


class PnLCalculator:
    """
    P&L Calculator
    
    Responsible for:
    - Calculating realized P&L from executed trades
    - Calculating unrealized P&L from open positions
    - Tracking daily, weekly, monthly performance
    - Computing trading statistics
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def calculate_realized_pnl(
        self,
        portfolio_id: int,
        time_frame: TimeFrame = TimeFrame.ALL_TIME,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> RealizedPnL:
        """
        Calculate realized P&L from executed sell trades.
        
        Args:
            portfolio_id: Portfolio ID
            time_frame: Time frame for calculation
            start_date: Optional start date override
            end_date: Optional end date override
            
        Returns:
            RealizedPnL with trading statistics
        """
        # Determine date range
        if not start_date:
            start_date = self._get_start_date(time_frame)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Get all executed sell trades in time frame
        query = select(Trade).where(
            Trade.portfolio_id == portfolio_id,
            Trade.trade_type == TradeType.SELL,
            Trade.status == TradeStatus.EXECUTED,
            Trade.executed_at >= start_date,
            Trade.executed_at <= end_date
        )
        
        result = await self.db.execute(query)
        trades = list(result.scalars().all())
        
        if not trades:
            return RealizedPnL()
        
        # Calculate statistics
        total_pnl = Decimal("0")
        gross_profit = Decimal("0")
        gross_loss = Decimal("0")
        winning_trades = 0
        losing_trades = 0
        largest_win = Decimal("0")
        largest_loss = Decimal("0")
        
        for trade in trades:
            pnl = trade.realized_pnl or Decimal("0")
            total_pnl += pnl
            
            if pnl > 0:
                gross_profit += pnl
                winning_trades += 1
                if pnl > largest_win:
                    largest_win = pnl
            elif pnl < 0:
                gross_loss += abs(pnl)
                losing_trades += 1
                if abs(pnl) > largest_loss:
                    largest_loss = abs(pnl)
        
        trade_count = len(trades)
        win_rate = Decimal(winning_trades) / Decimal(trade_count) * 100 if trade_count > 0 else Decimal("0")
        avg_win = gross_profit / Decimal(winning_trades) if winning_trades > 0 else Decimal("0")
        avg_loss = gross_loss / Decimal(losing_trades) if losing_trades > 0 else Decimal("0")
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else None
        
        return RealizedPnL(
            total=total_pnl,
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            trade_count=trade_count,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate.quantize(Decimal("0.01")),
            avg_win=avg_win.quantize(Decimal("0.01")),
            avg_loss=avg_loss.quantize(Decimal("0.01")),
            profit_factor=profit_factor.quantize(Decimal("0.01")) if profit_factor else None,
            largest_win=largest_win,
            largest_loss=largest_loss
        )
    
    async def calculate_unrealized_pnl(
        self,
        portfolio_id: int,
        prices: Dict[str, Decimal]
    ) -> UnrealizedPnL:
        """
        Calculate unrealized P&L from open positions.
        
        Args:
            portfolio_id: Portfolio ID
            prices: Dict of symbol -> current price
            
        Returns:
            UnrealizedPnL with position breakdown
        """
        # Get all positions
        result = await self.db.execute(
            select(Position).where(Position.portfolio_id == portfolio_id)
        )
        positions = list(result.scalars().all())
        
        if not positions:
            return UnrealizedPnL()
        
        total = Decimal("0")
        by_position = {}
        positions_in_profit = 0
        positions_in_loss = 0
        largest_gain = ("", Decimal("0"))
        largest_loss = ("", Decimal("0"))
        
        for pos in positions:
            if pos.symbol not in prices:
                continue
            
            current_price = prices[pos.symbol]
            cost_basis = pos.quantity * pos.average_cost
            current_value = pos.quantity * current_price
            pnl = current_value - cost_basis
            
            total += pnl
            by_position[pos.symbol] = pnl
            
            if pnl > 0:
                positions_in_profit += 1
                if pnl > largest_gain[1]:
                    largest_gain = (pos.symbol, pnl)
            elif pnl < 0:
                positions_in_loss += 1
                if pnl < largest_loss[1]:
                    largest_loss = (pos.symbol, pnl)
        
        return UnrealizedPnL(
            total=total,
            by_position=by_position,
            positions_in_profit=positions_in_profit,
            positions_in_loss=positions_in_loss,
            largest_gain=largest_gain,
            largest_loss=largest_loss
        )
    
    async def calculate_portfolio_pnl(
        self,
        portfolio_id: int,
        prices: Dict[str, Decimal],
        time_frame: TimeFrame = TimeFrame.ALL_TIME
    ) -> PortfolioPnL:
        """
        Calculate combined portfolio P&L.
        
        Args:
            portfolio_id: Portfolio ID
            prices: Dict of symbol -> current price
            time_frame: Time frame for realized P&L
            
        Returns:
            PortfolioPnL with full breakdown
        """
        # Get portfolio
        result = await self.db.execute(
            select(Portfolio).where(Portfolio.id == portfolio_id)
        )
        portfolio = result.scalar_one_or_none()
        
        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found")
        
        # Calculate realized and unrealized P&L
        realized = await self.calculate_realized_pnl(portfolio_id, time_frame)
        unrealized = await self.calculate_unrealized_pnl(portfolio_id, prices)
        
        # Calculate current portfolio value
        positions_value = Decimal("0")
        positions_result = await self.db.execute(
            select(Position).where(Position.portfolio_id == portfolio_id)
        )
        for pos in positions_result.scalars():
            if pos.symbol in prices:
                positions_value += pos.quantity * prices[pos.symbol]
        
        current_value = portfolio.cash_balance + positions_value
        total_pnl = realized.total + unrealized.total
        
        # Calculate return percentage
        initial_capital = portfolio.initial_capital or current_value
        total_pnl_pct = Decimal("0")
        if initial_capital > 0:
            total_pnl_pct = ((current_value - initial_capital) / initial_capital) * 100
        
        return PortfolioPnL(
            portfolio_id=portfolio_id,
            realized=realized,
            unrealized=unrealized,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct.quantize(Decimal("0.01")),
            initial_capital=initial_capital,
            current_value=current_value,
            cash_balance=portfolio.cash_balance,
            time_frame=time_frame,
            as_of=datetime.utcnow()
        )
    
    async def get_daily_pnl(
        self,
        portfolio_id: int,
        days: int = 30
    ) -> List[DailyPnL]:
        """
        Get daily P&L history.
        
        Args:
            portfolio_id: Portfolio ID
            days: Number of days to look back
            
        Returns:
            List of daily P&L records
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get all trades in period
        result = await self.db.execute(
            select(Trade).where(
                Trade.portfolio_id == portfolio_id,
                Trade.status == TradeStatus.EXECUTED,
                Trade.executed_at >= start_date,
                Trade.executed_at <= end_date
            ).order_by(Trade.executed_at)
        )
        trades = list(result.scalars().all())
        
        # Group by date and calculate daily P&L
        daily_data = {}
        for trade in trades:
            trade_date = trade.executed_at.date()
            if trade_date not in daily_data:
                daily_data[trade_date] = {
                    'realized': Decimal("0"),
                    'trades': []
                }
            
            if trade.trade_type == TradeType.SELL and trade.realized_pnl:
                daily_data[trade_date]['realized'] += trade.realized_pnl
            daily_data[trade_date]['trades'].append(trade)
        
        # Build daily records
        # Note: Full implementation would need historical portfolio values
        daily_records = []
        for day in sorted(daily_data.keys()):
            data = daily_data[day]
            daily_records.append(DailyPnL(
                date=day,
                realized=data['realized'],
                unrealized=Decimal("0"),  # Would need historical prices
                total=data['realized'],
                portfolio_value=Decimal("0"),  # Would need historical snapshots
                daily_return_pct=Decimal("0")
            ))
        
        return daily_records
    
    async def get_trade_statistics(
        self,
        portfolio_id: int,
        time_frame: TimeFrame = TimeFrame.ALL_TIME
    ) -> Dict[str, Any]:
        """
        Get comprehensive trading statistics.
        
        Returns various metrics for performance analysis.
        """
        start_date = self._get_start_date(time_frame)
        
        # Get all executed trades
        result = await self.db.execute(
            select(Trade).where(
                Trade.portfolio_id == portfolio_id,
                Trade.status == TradeStatus.EXECUTED,
                Trade.executed_at >= start_date
            )
        )
        trades = list(result.scalars().all())
        
        if not trades:
            return {
                'total_trades': 0,
                'buy_trades': 0,
                'sell_trades': 0,
                'total_volume': Decimal("0"),
                'avg_trade_size': Decimal("0"),
                'most_traded_symbol': None,
                'avg_holding_period_days': None
            }
        
        buy_trades = [t for t in trades if t.trade_type == TradeType.BUY]
        sell_trades = [t for t in trades if t.trade_type == TradeType.SELL]
        
        total_volume = sum(t.total_value or Decimal("0") for t in trades)
        avg_trade_size = total_volume / len(trades) if trades else Decimal("0")
        
        # Most traded symbol
        symbol_counts = {}
        for t in trades:
            symbol_counts[t.symbol] = symbol_counts.get(t.symbol, 0) + 1
        most_traded = max(symbol_counts.items(), key=lambda x: x[1])[0] if symbol_counts else None
        
        return {
            'total_trades': len(trades),
            'buy_trades': len(buy_trades),
            'sell_trades': len(sell_trades),
            'total_volume': total_volume,
            'avg_trade_size': avg_trade_size.quantize(Decimal("0.01")),
            'most_traded_symbol': most_traded,
            'symbols_traded': len(symbol_counts),
            'time_frame': time_frame.value
        }
    
    async def calculate_position_pnl(
        self,
        portfolio_id: int,
        symbol: str,
        current_price: Decimal
    ) -> Dict[str, Any]:
        """
        Calculate P&L for a specific position.
        
        Args:
            portfolio_id: Portfolio ID
            symbol: Stock symbol
            current_price: Current price
            
        Returns:
            Position P&L details
        """
        # Get position
        result = await self.db.execute(
            select(Position).where(
                Position.portfolio_id == portfolio_id,
                Position.symbol == symbol.upper()
            )
        )
        position = result.scalar_one_or_none()
        
        if not position:
            return {'error': f'No position found for {symbol}'}
        
        cost_basis = position.quantity * position.average_cost
        current_value = position.quantity * current_price
        unrealized_pnl = current_value - cost_basis
        unrealized_pnl_pct = (unrealized_pnl / cost_basis * 100) if cost_basis > 0 else Decimal("0")
        
        # Get realized P&L from closed trades
        trade_result = await self.db.execute(
            select(func.sum(Trade.realized_pnl)).where(
                Trade.portfolio_id == portfolio_id,
                Trade.symbol == symbol.upper(),
                Trade.trade_type == TradeType.SELL,
                Trade.status == TradeStatus.EXECUTED
            )
        )
        realized_pnl = trade_result.scalar() or Decimal("0")
        
        return {
            'symbol': symbol.upper(),
            'quantity': position.quantity,
            'average_cost': position.average_cost,
            'cost_basis': cost_basis,
            'current_price': current_price,
            'current_value': current_value,
            'unrealized_pnl': unrealized_pnl,
            'unrealized_pnl_pct': unrealized_pnl_pct.quantize(Decimal("0.01")),
            'realized_pnl': realized_pnl,
            'total_pnl': unrealized_pnl + realized_pnl
        }
    
    def _get_start_date(self, time_frame: TimeFrame) -> datetime:
        """Get start date for time frame."""
        now = datetime.utcnow()
        
        if time_frame == TimeFrame.DAY:
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_frame == TimeFrame.WEEK:
            return now - timedelta(days=7)
        elif time_frame == TimeFrame.MONTH:
            return now - timedelta(days=30)
        elif time_frame == TimeFrame.QUARTER:
            return now - timedelta(days=90)
        elif time_frame == TimeFrame.YEAR:
            return now - timedelta(days=365)
        elif time_frame == TimeFrame.YTD:
            return datetime(now.year, 1, 1)
        else:  # ALL_TIME
            return datetime(2000, 1, 1)
