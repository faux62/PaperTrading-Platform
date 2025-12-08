"""
Trading Assistant Bot - Pre-Market Analyzer

Analyzes market conditions before market open:
- Scans pre-market movers
- Reviews overnight alerts
- Generates morning briefing
- Identifies trading opportunities
"""
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from loguru import logger
from decimal import Decimal

from app.db.models import (
    User,
    Portfolio,
    Position,
    Watchlist,
    Alert,
    AlertStatus,
    AlertType,
    BotSignal,
    BotReport,
    SignalType,
    SignalPriority,
    SignalDirection,
)
from app.bot.signal_engine import SignalEngine


class PreMarketAnalyzer:
    """
    Pre-market analysis engine.
    
    Runs before market open to:
    1. Review triggered alerts from overnight
    2. Scan pre-market movers
    3. Analyze watchlist changes
    4. Generate trade opportunities
    5. Create morning briefing report
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.signal_engine = SignalEngine(db)
    
    async def run_full_analysis(self, user_id: int) -> BotReport:
        """
        Run complete pre-market analysis for a user.
        
        Returns a BotReport with the morning briefing.
        """
        logger.info(f"Starting pre-market analysis for user {user_id}")
        
        # Get user's portfolios
        portfolios = await self._get_user_portfolios(user_id)
        if not portfolios:
            logger.warning(f"No portfolios found for user {user_id}")
            return None
        
        # Gather analysis data
        triggered_alerts = await self._review_triggered_alerts(user_id)
        watchlist_analysis = await self._analyze_watchlist(user_id)
        position_overnight = await self._analyze_overnight_positions(portfolios)
        trade_opportunities = await self._identify_opportunities(user_id, watchlist_analysis)
        
        # Generate signals for high-priority items
        signals_created = await self._create_signals_from_analysis(
            user_id=user_id,
            portfolio_id=portfolios[0].id,  # Primary portfolio
            triggered_alerts=triggered_alerts,
            opportunities=trade_opportunities
        )
        
        # Create morning briefing report
        report = await self._create_morning_briefing(
            user_id=user_id,
            triggered_alerts=triggered_alerts,
            watchlist_analysis=watchlist_analysis,
            position_overnight=position_overnight,
            trade_opportunities=trade_opportunities,
            signals_created=signals_created
        )
        
        logger.info(f"Pre-market analysis complete for user {user_id}: {signals_created} signals created")
        return report
    
    async def _get_user_portfolios(self, user_id: int) -> List[Portfolio]:
        """Get all active portfolios for user."""
        result = await self.db.execute(
            select(Portfolio).where(
                and_(
                    Portfolio.user_id == user_id,
                    Portfolio.is_active == "active"
                )
            )
        )
        return result.scalars().all()
    
    async def _review_triggered_alerts(self, user_id: int) -> List[Dict]:
        """Review alerts that triggered since last check."""
        # Get alerts triggered in last 24 hours
        yesterday = datetime.utcnow() - timedelta(hours=24)
        
        result = await self.db.execute(
            select(Alert).where(
                and_(
                    Alert.user_id == user_id,
                    Alert.status == AlertStatus.TRIGGERED,
                    Alert.triggered_at >= yesterday
                )
            ).order_by(Alert.triggered_at.desc())
        )
        alerts = result.scalars().all()
        
        triggered = []
        for alert in alerts:
            triggered.append({
                'id': alert.id,
                'symbol': alert.symbol,
                'type': alert.alert_type.value,
                'target': alert.target_value,
                'triggered_price': alert.triggered_price,
                'triggered_at': alert.triggered_at.isoformat() if alert.triggered_at else None,
                'note': alert.note
            })
        
        logger.info(f"Found {len(triggered)} triggered alerts for user {user_id}")
        return triggered
    
    async def _analyze_watchlist(self, user_id: int) -> Dict[str, Any]:
        """
        Analyze user's watchlist symbols.
        
        Returns analysis including:
        - Gap up/down symbols
        - Volume anomalies
        - Key level approaches
        """
        # Get user's watchlists
        result = await self.db.execute(
            select(Watchlist).where(Watchlist.user_id == user_id)
        )
        watchlists = result.scalars().all()
        
        symbols = set()
        for wl in watchlists:
            # Assume watchlist has symbols attribute or relationship
            # This would need actual market data integration
            pass
        
        # For now, return placeholder structure
        # In production, this would fetch real pre-market data
        analysis = {
            'total_symbols': len(symbols),
            'gap_up': [],       # Symbols gapping up > 2%
            'gap_down': [],     # Symbols gapping down > 2%
            'high_volume': [],  # Symbols with unusual pre-market volume
            'near_resistance': [],  # Approaching resistance
            'near_support': [],     # Approaching support
        }
        
        return analysis
    
    async def _analyze_overnight_positions(
        self,
        portfolios: List[Portfolio]
    ) -> Dict[str, Any]:
        """
        Analyze overnight positions for gaps and risk.
        """
        analysis = {
            'total_positions': 0,
            'positions_gapped_up': [],
            'positions_gapped_down': [],
            'positions_at_risk': [],  # Stop might be hit at open
            'positions_near_target': [],
        }
        
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
            analysis['total_positions'] += len(positions)
            
            # In production, would check current pre-market prices
            # against entry prices and stop-loss levels
        
        return analysis
    
    async def _identify_opportunities(
        self,
        user_id: int,
        watchlist_analysis: Dict
    ) -> List[Dict]:
        """
        Identify potential trading opportunities.
        
        Uses:
        - Technical levels
        - Gap analysis
        - Volume patterns
        - ML predictions (if available)
        """
        opportunities = []
        
        # Gap plays
        for symbol_data in watchlist_analysis.get('gap_up', []):
            opportunities.append({
                'symbol': symbol_data.get('symbol'),
                'type': 'gap_up',
                'direction': 'long',
                'reason': f"Gapping up {symbol_data.get('gap_percent', 0):.1f}% on news/momentum",
                'confidence': 60,
                'priority': 'medium'
            })
        
        # Breakdown plays
        for symbol_data in watchlist_analysis.get('gap_down', []):
            opportunities.append({
                'symbol': symbol_data.get('symbol'),
                'type': 'gap_down',
                'direction': 'short',
                'reason': f"Gapping down {abs(symbol_data.get('gap_percent', 0)):.1f}%",
                'confidence': 55,
                'priority': 'medium'
            })
        
        # Support bounce plays
        for symbol_data in watchlist_analysis.get('near_support', []):
            opportunities.append({
                'symbol': symbol_data.get('symbol'),
                'type': 'support_bounce',
                'direction': 'long',
                'reason': f"Testing support level ${symbol_data.get('support_level', 0):.2f}",
                'confidence': 65,
                'priority': 'medium'
            })
        
        return opportunities
    
    async def _create_signals_from_analysis(
        self,
        user_id: int,
        portfolio_id: int,
        triggered_alerts: List[Dict],
        opportunities: List[Dict]
    ) -> int:
        """Create bot signals from analysis results."""
        signals_created = 0
        
        # Create signals for triggered alerts
        for alert in triggered_alerts:
            try:
                await self.signal_engine.create_market_alert(
                    user_id=user_id,
                    alert_type=alert['type'],
                    symbol=alert['symbol'],
                    current_value=alert['triggered_price'] or 0,
                    threshold=alert['target'],
                    message_detail=alert.get('note', 'Alert condition met'),
                    source_alert_id=alert['id'],
                    priority=SignalPriority.HIGH
                )
                signals_created += 1
            except Exception as e:
                logger.error(f"Failed to create signal for alert {alert['id']}: {e}")
        
        # Create signals for high-confidence opportunities
        for opp in opportunities:
            if opp.get('confidence', 0) >= 65:
                try:
                    # Would need actual price data to create full trade suggestion
                    # For now, create a generic opportunity signal
                    direction = SignalDirection.LONG if opp['direction'] == 'long' else SignalDirection.SHORT
                    
                    signal = BotSignal(
                        user_id=user_id,
                        portfolio_id=portfolio_id,
                        signal_type=SignalType.TRADE_SUGGESTION,
                        priority=SignalPriority.MEDIUM if opp['priority'] == 'medium' else SignalPriority.HIGH,
                        status='pending',
                        symbol=opp['symbol'],
                        direction=direction,
                        title=f"💡 Opportunity: {opp['symbol']} ({opp['type']})",
                        message=f"**{opp['type'].replace('_', ' ').title()}**\n\n{opp['reason']}\n\n*Review chart and set your own entry/stop/target.*",
                        rationale=opp['reason'],
                        confidence_score=opp['confidence'],
                        source="pre_market_analyzer",
                        valid_until=datetime.utcnow() + timedelta(hours=10)
                    )
                    self.db.add(signal)
                    signals_created += 1
                except Exception as e:
                    logger.error(f"Failed to create opportunity signal: {e}")
        
        await self.db.commit()
        return signals_created
    
    async def _create_morning_briefing(
        self,
        user_id: int,
        triggered_alerts: List[Dict],
        watchlist_analysis: Dict,
        position_overnight: Dict,
        trade_opportunities: List[Dict],
        signals_created: int
    ) -> BotReport:
        """Create the morning briefing report."""
        now = datetime.utcnow()
        
        content = {
            'summary': {
                'alerts_triggered': len(triggered_alerts),
                'watchlist_symbols': watchlist_analysis.get('total_symbols', 0),
                'open_positions': position_overnight.get('total_positions', 0),
                'opportunities_found': len(trade_opportunities),
                'signals_generated': signals_created,
            },
            'alerts': triggered_alerts[:10],  # Top 10 alerts
            'watchlist': {
                'gap_up': watchlist_analysis.get('gap_up', [])[:5],
                'gap_down': watchlist_analysis.get('gap_down', [])[:5],
                'high_volume': watchlist_analysis.get('high_volume', [])[:5],
            },
            'positions': {
                'at_risk': position_overnight.get('positions_at_risk', []),
                'near_target': position_overnight.get('positions_near_target', []),
            },
            'opportunities': trade_opportunities[:10],
            'market_notes': [],  # Would add market-wide notes
        }
        
        report = BotReport(
            user_id=user_id,
            report_type='morning_briefing',
            report_date=now,
            title=f"📊 Morning Briefing - {now.strftime('%B %d, %Y')}",
            content=content,
            total_signals=signals_created,
            trades_suggested=len([o for o in trade_opportunities if o.get('confidence', 0) >= 65]),
            alerts_triggered=len(triggered_alerts),
            is_read=False
        )
        
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        
        logger.info(f"Created morning briefing report {report.id} for user {user_id}")
        return report


async def run_pre_market_analysis_for_all_users(db: AsyncSession) -> int:
    """
    Run pre-market analysis for all active users.
    Called by scheduler job.
    """
    result = await db.execute(
        select(User).where(User.is_active == True)
    )
    users = result.scalars().all()
    
    reports_created = 0
    for user in users:
        try:
            analyzer = PreMarketAnalyzer(db)
            report = await analyzer.run_full_analysis(user.id)
            if report:
                reports_created += 1
        except Exception as e:
            logger.error(f"Pre-market analysis failed for user {user.id}: {e}")
    
    logger.info(f"Pre-market analysis complete: {reports_created} reports created")
    return reports_created
