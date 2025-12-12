"""
Trading Assistant Bot - Report Generator

Generates automated reports:
- Daily summary
- Weekly performance report
- Trade journal auto-compilation
"""
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from loguru import logger

from app.db.models import (
    User,
    Portfolio,
    Position,
    Trade,
    TradeStatus,
    BotSignal,
    BotReport,
    SignalStatus,
)


class ReportGenerator:
    """
    Automated report generation engine.
    
    Generates:
    - Daily trading summary
    - Weekly performance report
    - Trade journal entries
    - Performance analytics
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def generate_daily_summary(self, user_id: int) -> BotReport:
        """
        Generate end-of-day trading summary.
        
        Includes:
        - P/L for the day
        - Trades executed
        - Signals reviewed
        - Open positions status
        """
        logger.info(f"Generating daily summary for user {user_id}")
        
        today = date.today()
        start_of_day = datetime.combine(today, datetime.min.time())
        end_of_day = datetime.combine(today, datetime.max.time())
        
        # Get today's trades
        trades_data = await self._get_daily_trades(user_id, start_of_day, end_of_day)
        
        # Get signals reviewed
        signals_data = await self._get_daily_signals(user_id, start_of_day, end_of_day)
        
        # Get current positions
        positions_data = await self._get_positions_summary(user_id)
        
        # Calculate daily P/L
        daily_pnl = await self._calculate_daily_pnl(user_id, trades_data)
        
        # Build report content
        content = {
            'date': today.isoformat(),
            'summary': {
                'daily_pnl': daily_pnl['total'],
                'daily_pnl_percent': daily_pnl['percent'],
                'trades_executed': trades_data['count'],
                'winning_trades': trades_data['winners'],
                'losing_trades': trades_data['losers'],
                'win_rate': trades_data['win_rate'],
                'signals_received': signals_data['total'],
                'signals_accepted': signals_data['accepted'],
                'signals_ignored': signals_data['ignored'],
                'open_positions': positions_data['count'],
                'unrealized_pnl': positions_data['unrealized_pnl'],
            },
            'trades': trades_data['trades'][:20],  # Top 20 trades
            'positions': positions_data['positions'][:20],
            'top_performers': trades_data['top_performers'],
            'worst_performers': trades_data['worst_performers'],
            'signals': signals_data['signals'][:10],
        }
        
        # Create report
        pnl_emoji = "📈" if daily_pnl['total'] >= 0 else "📉"
        
        report = BotReport(
            user_id=user_id,
            report_type='daily_summary',
            report_date=datetime.utcnow(),
            title=f"{pnl_emoji} Daily Summary - {today.strftime('%B %d, %Y')}",
            content=content,
            total_signals=signals_data['total'],
            trades_suggested=trades_data['count'],
            alerts_triggered=0,
            is_read=False
        )
        
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        
        logger.info(f"Created daily summary report {report.id} for user {user_id}")
        return report
    
    async def generate_weekly_report(self, user_id: int) -> BotReport:
        """
        Generate weekly performance report.
        
        Includes:
        - Weekly P/L
        - Performance vs benchmark
        - Best/worst trades
        - Pattern analysis
        - Recommendations
        """
        logger.info(f"Generating weekly report for user {user_id}")
        
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        
        start_dt = datetime.combine(week_start, datetime.min.time())
        end_dt = datetime.combine(week_end, datetime.max.time())
        
        # Get week's trades
        trades_data = await self._get_weekly_trades(user_id, start_dt, end_dt)
        
        # Get week's signals
        signals_data = await self._get_weekly_signals(user_id, start_dt, end_dt)
        
        # Calculate weekly P/L
        weekly_pnl = await self._calculate_weekly_pnl(user_id, trades_data)
        
        # Analyze patterns
        patterns = await self._analyze_trading_patterns(trades_data)
        
        # Build report content
        content = {
            'period': {
                'start': week_start.isoformat(),
                'end': week_end.isoformat(),
            },
            'performance': {
                'weekly_pnl': weekly_pnl['total'],
                'weekly_pnl_percent': weekly_pnl['percent'],
                'benchmark_return': 0,  # Would compare to SPY
                'alpha': 0,  # weekly_pnl_percent - benchmark
            },
            'trading_activity': {
                'total_trades': trades_data['count'],
                'winning_trades': trades_data['winners'],
                'losing_trades': trades_data['losers'],
                'win_rate': trades_data['win_rate'],
                'avg_win': trades_data['avg_win'],
                'avg_loss': trades_data['avg_loss'],
                'profit_factor': trades_data['profit_factor'],
                'largest_win': trades_data['largest_win'],
                'largest_loss': trades_data['largest_loss'],
            },
            'signals': {
                'total_received': signals_data['total'],
                'accepted': signals_data['accepted'],
                'ignored': signals_data['ignored'],
                'acceptance_rate': signals_data['acceptance_rate'],
            },
            'patterns': patterns,
            'best_trades': trades_data['top_performers'][:5],
            'worst_trades': trades_data['worst_performers'][:5],
            'recommendations': self._generate_recommendations(trades_data, patterns),
        }
        
        # Create report
        pnl_emoji = "🟢" if weekly_pnl['total'] >= 0 else "🔴"
        
        report = BotReport(
            user_id=user_id,
            report_type='weekly_report',
            report_date=datetime.utcnow(),
            title=f"{pnl_emoji} Weekly Report - Week of {week_start.strftime('%B %d, %Y')}",
            content=content,
            total_signals=signals_data['total'],
            trades_suggested=trades_data['count'],
            alerts_triggered=0,
            is_read=False
        )
        
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        
        logger.info(f"Created weekly report {report.id} for user {user_id}")
        return report
    
    async def _get_daily_trades(
        self,
        user_id: int,
        start: datetime,
        end: datetime
    ) -> Dict[str, Any]:
        """Get trades for the day."""
        # Get user's portfolios first
        portfolio_result = await self.db.execute(
            select(Portfolio.id).where(Portfolio.user_id == user_id)
        )
        portfolio_ids = [p for p in portfolio_result.scalars().all()]
        
        if not portfolio_ids:
            return self._empty_trades_data()
        
        # Get trades
        result = await self.db.execute(
            select(Trade).where(
                and_(
                    Trade.portfolio_id.in_(portfolio_ids),
                    Trade.status == TradeStatus.FILLED,
                    Trade.executed_at >= start,
                    Trade.executed_at <= end
                )
            ).order_by(Trade.executed_at.desc())
        )
        trades = result.scalars().all()
        
        return self._analyze_trades(trades)
    
    async def _get_weekly_trades(
        self,
        user_id: int,
        start: datetime,
        end: datetime
    ) -> Dict[str, Any]:
        """Get trades for the week."""
        return await self._get_daily_trades(user_id, start, end)
    
    async def _get_daily_signals(
        self,
        user_id: int,
        start: datetime,
        end: datetime
    ) -> Dict[str, Any]:
        """Get signals for the day."""
        result = await self.db.execute(
            select(BotSignal).where(
                and_(
                    BotSignal.user_id == user_id,
                    BotSignal.created_at >= start,
                    BotSignal.created_at <= end
                )
            ).order_by(BotSignal.created_at.desc())
        )
        signals = result.scalars().all()
        
        return self._analyze_signals(signals)
    
    async def _get_weekly_signals(
        self,
        user_id: int,
        start: datetime,
        end: datetime
    ) -> Dict[str, Any]:
        """Get signals for the week."""
        return await self._get_daily_signals(user_id, start, end)
    
    async def _get_positions_summary(self, user_id: int) -> Dict[str, Any]:
        """Get summary of current positions."""
        # Get portfolios
        portfolio_result = await self.db.execute(
            select(Portfolio).where(
                and_(
                    Portfolio.user_id == user_id,
                    Portfolio.is_active == True
                )
            )
        )
        portfolios = portfolio_result.scalars().all()
        
        positions_list = []
        total_unrealized = 0.0
        
        for portfolio in portfolios:
            result = await self.db.execute(
                select(Position).where(
                    and_(
                        Position.portfolio_id == portfolio.id,
                        Position.quantity != 0
                    )
                )
            )
            positions = result.scalars().all()
            
            for pos in positions:
                # In production, would fetch current prices
                positions_list.append({
                    'symbol': pos.symbol,
                    'quantity': pos.quantity,
                    'avg_price': float(pos.average_price),
                    'portfolio': portfolio.name
                })
        
        return {
            'count': len(positions_list),
            'positions': positions_list,
            'unrealized_pnl': total_unrealized
        }
    
    async def _calculate_daily_pnl(
        self,
        user_id: int,
        trades_data: Dict
    ) -> Dict[str, float]:
        """Calculate daily P/L from trades."""
        # Simplified - in production would calculate from actual trade P/L
        total_pnl = sum(t.get('pnl', 0) for t in trades_data.get('trades', []))
        
        return {
            'total': total_pnl,
            'percent': 0  # Would need portfolio value to calculate
        }
    
    async def _calculate_weekly_pnl(
        self,
        user_id: int,
        trades_data: Dict
    ) -> Dict[str, float]:
        """Calculate weekly P/L."""
        return await self._calculate_daily_pnl(user_id, trades_data)
    
    def _analyze_trades(self, trades: List[Trade]) -> Dict[str, Any]:
        """Analyze a list of trades."""
        if not trades:
            return self._empty_trades_data()
        
        trades_list = []
        winners = 0
        losers = 0
        total_profit = 0.0
        total_loss = 0.0
        
        for trade in trades:
            # Simplified P/L calculation
            pnl = 0  # Would calculate actual P/L
            
            trade_data = {
                'id': trade.id,
                'symbol': trade.symbol,
                'side': trade.trade_type.value if trade.trade_type else 'unknown',
                'quantity': trade.quantity,
                'price': float(trade.price) if trade.price else 0,
                'executed_at': trade.executed_at.isoformat() if trade.executed_at else None,
                'pnl': pnl
            }
            trades_list.append(trade_data)
            
            if pnl > 0:
                winners += 1
                total_profit += pnl
            elif pnl < 0:
                losers += 1
                total_loss += abs(pnl)
        
        count = len(trades_list)
        win_rate = (winners / count * 100) if count > 0 else 0
        avg_win = (total_profit / winners) if winners > 0 else 0
        avg_loss = (total_loss / losers) if losers > 0 else 0
        profit_factor = (total_profit / total_loss) if total_loss > 0 else 0
        
        # Sort for top/worst
        sorted_trades = sorted(trades_list, key=lambda x: x['pnl'], reverse=True)
        
        return {
            'count': count,
            'trades': trades_list,
            'winners': winners,
            'losers': losers,
            'win_rate': round(win_rate, 1),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'profit_factor': round(profit_factor, 2),
            'largest_win': sorted_trades[0] if sorted_trades else None,
            'largest_loss': sorted_trades[-1] if sorted_trades else None,
            'top_performers': sorted_trades[:5],
            'worst_performers': sorted_trades[-5:] if len(sorted_trades) > 5 else sorted_trades[::-1][:5]
        }
    
    def _analyze_signals(self, signals: List[BotSignal]) -> Dict[str, Any]:
        """Analyze signals received."""
        total = len(signals)
        accepted = sum(1 for s in signals if s.status == SignalStatus.ACCEPTED)
        ignored = sum(1 for s in signals if s.status == SignalStatus.IGNORED)
        
        signals_list = [{
            'id': s.id,
            'type': s.signal_type.value if s.signal_type else 'unknown',
            'symbol': s.symbol,
            'title': s.title,
            'status': s.status.value if s.status else 'unknown',
            'created_at': s.created_at.isoformat() if s.created_at else None
        } for s in signals]
        
        return {
            'total': total,
            'accepted': accepted,
            'ignored': ignored,
            'pending': total - accepted - ignored,
            'acceptance_rate': round((accepted / total * 100) if total > 0 else 0, 1),
            'signals': signals_list
        }
    
    async def _analyze_trading_patterns(self, trades_data: Dict) -> Dict[str, Any]:
        """Analyze trading patterns for insights."""
        # Simplified pattern analysis
        return {
            'best_day': None,  # Would analyze by day of week
            'best_hour': None,  # Would analyze by hour
            'most_traded_symbol': None,  # Would count symbol frequency
            'avg_hold_time': None,  # Would calculate hold duration
            'notes': []
        }
    
    def _generate_recommendations(
        self,
        trades_data: Dict,
        patterns: Dict
    ) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []
        
        win_rate = trades_data.get('win_rate', 0)
        profit_factor = trades_data.get('profit_factor', 0)
        
        if win_rate < 40:
            recommendations.append(
                "📊 Win rate is below 40%. Consider reviewing your entry criteria and waiting for higher-probability setups."
            )
        
        if profit_factor < 1.5 and profit_factor > 0:
            recommendations.append(
                "⚖️ Profit factor is below 1.5. Focus on letting winners run longer or cutting losses faster."
            )
        
        avg_loss = trades_data.get('avg_loss', 0)
        avg_win = trades_data.get('avg_win', 0)
        if avg_loss > avg_win and avg_loss > 0:
            recommendations.append(
                "📉 Average loss exceeds average win. Consider tighter stop-losses or better position sizing."
            )
        
        if not recommendations:
            recommendations.append(
                "✅ Trading metrics look healthy. Keep following your strategy!"
            )
        
        return recommendations
    
    def _empty_trades_data(self) -> Dict[str, Any]:
        """Return empty trades data structure."""
        return {
            'count': 0,
            'trades': [],
            'winners': 0,
            'losers': 0,
            'win_rate': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'profit_factor': 0,
            'largest_win': None,
            'largest_loss': None,
            'top_performers': [],
            'worst_performers': []
        }


async def run_daily_reports_for_all_users(db: AsyncSession) -> int:
    """
    Generate daily reports for all active users.
    Called by scheduler job after market close.
    """
    result = await db.execute(
        select(User).where(User.is_active == True)
    )
    users = result.scalars().all()
    
    reports_created = 0
    for user in users:
        try:
            generator = ReportGenerator(db)
            report = await generator.generate_daily_summary(user.id)
            if report:
                reports_created += 1
        except Exception as e:
            logger.error(f"Daily report generation failed for user {user.id}: {e}")
    
    logger.info(f"Daily reports complete: {reports_created} reports created")
    return reports_created


async def run_weekly_reports_for_all_users(db: AsyncSession) -> int:
    """
    Generate weekly reports for all active users.
    Called by scheduler job on Friday evening.
    """
    result = await db.execute(
        select(User).where(User.is_active == True)
    )
    users = result.scalars().all()
    
    reports_created = 0
    for user in users:
        try:
            generator = ReportGenerator(db)
            report = await generator.generate_weekly_report(user.id)
            if report:
                reports_created += 1
        except Exception as e:
            logger.error(f"Weekly report generation failed for user {user.id}: {e}")
    
    logger.info(f"Weekly reports complete: {reports_created} reports created")
    return reports_created
