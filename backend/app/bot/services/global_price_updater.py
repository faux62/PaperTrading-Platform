"""
Global Price Updater Service

Manages price updates for all markets globally:
- Real-time updates for open markets
- EOD (End of Day) data for closed markets
- Smart caching to avoid redundant API calls
"""
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Set, List, Tuple
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from loguru import logger

from app.db.models import Portfolio, Position
from app.scheduler.market_hours import (
    MarketHoursManager,
    MarketSession,
    EXCHANGE_HOURS,
)
from app.data_providers import orchestrator
from app.db.redis_client import redis_client
from app.utils.currency import get_exchange_rate


class GlobalPriceUpdater:
    """
    Service for updating prices across all global markets.
    
    Strategy:
    1. For OPEN markets: Fetch real-time quotes
    2. For CLOSED markets: Fetch EOD data (once per day)
    3. Track what's been updated to avoid redundant calls
    """
    
    # Cache keys for tracking EOD updates
    EOD_CACHE_PREFIX = "price_updater:eod_fetched:"
    EOD_CACHE_TTL = 86400  # 24 hours
    
    # Map symbols to exchanges (simplified - can be expanded)
    EXCHANGE_SUFFIXES = {
        ".L": "LSE",       # London
        ".DE": "XETRA",    # Germany
        ".PA": "EURONEXT", # Paris
        ".MI": "BIT",      # Milan
        ".MC": "BME",      # Madrid
        ".SW": "SIX",      # Swiss
        ".T": "TSE",       # Tokyo
        ".HK": "HKEX",     # Hong Kong
        ".SS": "SSE",      # Shanghai
        ".SZ": "SZSE",     # Shenzhen
        ".NS": "NSE",      # India NSE
        ".BO": "NSE",      # India BSE
        ".KS": "KRX",      # Korea
        ".AX": "ASX",      # Australia
        ".SI": "SGX",      # Singapore
    }
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.market_manager = MarketHoursManager()
        self._eod_fetched_today: Set[str] = set()  # In-memory cache for current session
    
    def _get_exchange_for_symbol(self, symbol: str) -> str:
        """
        Determine the exchange for a symbol based on suffix or default to US.
        """
        symbol_upper = symbol.upper()
        
        for suffix, exchange in self.EXCHANGE_SUFFIXES.items():
            if symbol_upper.endswith(suffix.upper()):
                return exchange
        
        # Default to NYSE for US stocks (no suffix)
        return "NYSE"
    
    def _get_market_status(self, exchange: str) -> Tuple[bool, MarketSession]:
        """
        Get current market status for an exchange.
        Returns (is_open, session_type)
        """
        try:
            status = self.market_manager.get_market_status(exchange)
            return status.is_open, status.session
        except Exception as e:
            logger.warning(f"Could not get status for {exchange}: {e}")
            # Default to closed if we can't determine
            return False, MarketSession.CLOSED
    
    async def _is_eod_fetched_today(self, symbol: str) -> bool:
        """Check if EOD data was already fetched today for this symbol."""
        # Check in-memory first
        today_key = f"{symbol}:{date.today().isoformat()}"
        if today_key in self._eod_fetched_today:
            return True
        
        # Check Redis
        try:
            cache_key = f"{self.EOD_CACHE_PREFIX}{today_key}"
            cached = await redis_client.get(cache_key)
            if cached:
                self._eod_fetched_today.add(today_key)
                return True
        except Exception as e:
            logger.debug(f"Redis check failed: {e}")
        
        return False
    
    async def _mark_eod_fetched(self, symbol: str) -> None:
        """Mark that EOD data was fetched today for this symbol."""
        today_key = f"{symbol}:{date.today().isoformat()}"
        self._eod_fetched_today.add(today_key)
        
        try:
            cache_key = f"{self.EOD_CACHE_PREFIX}{today_key}"
            await redis_client.set(cache_key, "1", ex=self.EOD_CACHE_TTL)
        except Exception as e:
            logger.debug(f"Redis set failed: {e}")
    
    async def _get_realtime_price(self, symbol: str) -> Optional[float]:
        """Fetch real-time price for a symbol."""
        try:
            quote = await orchestrator.get_quote(symbol)
            if quote and quote.price:
                return float(quote.price)
        except Exception as e:
            logger.debug(f"Real-time price fetch failed for {symbol}: {e}")
        return None
    
    async def _get_eod_price(self, symbol: str) -> Optional[float]:
        """
        Fetch End of Day price for a symbol.
        Returns the last closing price.
        """
        try:
            # Get last few days of data to ensure we have at least one valid close
            end_date = date.today()
            start_date = end_date - timedelta(days=7)
            
            bars = await orchestrator.get_historical(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date
            )
            
            if bars and len(bars) > 0:
                # Get the most recent bar's close price
                last_bar = bars[-1]
                return float(last_bar.close)
        except Exception as e:
            logger.debug(f"EOD price fetch failed for {symbol}: {e}")
        return None
    
    async def update_position_price(
        self,
        position: Position,
        portfolio_currency: str = "USD",
        force_realtime: bool = False
    ) -> bool:
        """
        Update price for a single position.
        
        Args:
            position: The position to update
            portfolio_currency: The portfolio's base currency for value conversion
            force_realtime: If True, always try real-time first
            
        Returns:
            True if price was updated, False otherwise
        """
        symbol = position.symbol
        exchange = self._get_exchange_for_symbol(symbol)
        is_open, session = self._get_market_status(exchange)
        native_currency = position.native_currency or "USD"
        
        price = None
        price_source = None
        
        if is_open or force_realtime:
            # Market is open - get real-time price
            price = await self._get_realtime_price(symbol)
            if price:
                price_source = "realtime"
        
        if price is None:
            # Market closed or real-time failed - try EOD
            if not await self._is_eod_fetched_today(symbol):
                price = await self._get_eod_price(symbol)
                if price:
                    await self._mark_eod_fetched(symbol)
                    price_source = "eod"
            else:
                # EOD already fetched today - skip
                logger.debug(f"EOD already fetched today for {symbol}")
                return False
        
        if price:
            # Update position price in native currency
            position.current_price = Decimal(str(price))
            
            # Get exchange rate for currency conversion (native -> portfolio)
            if native_currency != portfolio_currency:
                exchange_rate = await get_exchange_rate(native_currency, portfolio_currency)
            else:
                exchange_rate = Decimal("1.0")
            
            # Calculate market_value in PORTFOLIO currency
            native_market_value = position.quantity * position.current_price
            position.market_value = (native_market_value * exchange_rate).quantize(Decimal("0.01"))
            
            # Calculate unrealized P&L in PORTFOLIO currency
            # cost_basis uses avg_cost_portfolio (already in portfolio currency)
            cost_basis = position.quantity * (position.avg_cost_portfolio or position.avg_cost)
            position.unrealized_pnl = (position.market_value - cost_basis).quantize(Decimal("0.01"))
            
            # P&L percentage based on native currency prices (for accurate %)  
            if position.avg_cost > 0:
                position.unrealized_pnl_percent = float(
                    (position.current_price - position.avg_cost) / position.avg_cost * 100
                )
            position.updated_at = datetime.utcnow()
            
            logger.debug(f"Updated {symbol} price to {price} ({price_source}), market_value={position.market_value} {portfolio_currency}")
            return True
        
        return False
    
    async def update_portfolio_prices(self, portfolio: Portfolio) -> Dict[str, any]:
        """
        Update prices for all positions in a portfolio.
        
        Returns:
            Dict with update statistics
        """
        result = await self.db.execute(
            select(Position).where(
                and_(
                    Position.portfolio_id == portfolio.id,
                    Position.quantity != 0
                )
            )
        )
        positions = result.scalars().all()
        
        if not positions:
            return {"updated": 0, "skipped": 0, "failed": 0}
        
        # Get portfolio's base currency for value conversion
        portfolio_currency = portfolio.currency or "USD"
        
        stats = {"updated": 0, "skipped": 0, "failed": 0, "by_exchange": {}}
        
        for position in positions:
            exchange = self._get_exchange_for_symbol(position.symbol)
            
            if exchange not in stats["by_exchange"]:
                stats["by_exchange"][exchange] = {"updated": 0, "skipped": 0}
            
            try:
                updated = await self.update_position_price(position, portfolio_currency)
                if updated:
                    stats["updated"] += 1
                    stats["by_exchange"][exchange]["updated"] += 1
                else:
                    stats["skipped"] += 1
                    stats["by_exchange"][exchange]["skipped"] += 1
            except Exception as e:
                logger.error(f"Failed to update {position.symbol}: {e}")
                stats["failed"] += 1
        
        if stats["updated"] > 0:
            await self.db.commit()
        
        return stats
    
    async def get_market_overview(self) -> Dict[str, any]:
        """
        Get overview of all market statuses.
        
        Returns:
            Dict with market status information
        """
        overview = {}
        
        for exchange in EXCHANGE_HOURS.keys():
            try:
                status = self.market_manager.get_market_status(exchange)
                overview[exchange] = {
                    "is_open": status.is_open,
                    "session": status.session.value,
                    "local_time": status.local_time.isoformat() if status.local_time else None,
                    "next_open": status.next_open.isoformat() if status.next_open else None,
                    "next_close": status.next_close.isoformat() if status.next_close else None,
                }
            except Exception as e:
                overview[exchange] = {"error": str(e)}
        
        return overview


async def run_global_price_update(db: AsyncSession) -> Dict[str, any]:
    """
    Run global price update for all users' portfolios.
    
    This is the main entry point called by the scheduler.
    """
    from app.db.models import User
    
    result = await db.execute(
        select(User).where(User.is_active == True)
    )
    users = result.scalars().all()
    
    total_stats = {
        "users_processed": 0,
        "positions_updated": 0,
        "positions_skipped": 0,
        "positions_failed": 0,
    }
    
    for user in users:
        try:
            # Get user's portfolios
            portfolios_result = await db.execute(
                select(Portfolio).where(
                    and_(
                        Portfolio.user_id == user.id,
                        Portfolio.is_active == True
                    )
                )
            )
            portfolios = portfolios_result.scalars().all()
            
            updater = GlobalPriceUpdater(db)
            
            for portfolio in portfolios:
                stats = await updater.update_portfolio_prices(portfolio)
                total_stats["positions_updated"] += stats["updated"]
                total_stats["positions_skipped"] += stats["skipped"]
                total_stats["positions_failed"] += stats["failed"]
            
            total_stats["users_processed"] += 1
            
        except Exception as e:
            logger.error(f"Price update failed for user {user.id}: {e}")
    
    if total_stats["positions_updated"] > 0:
        logger.info(
            f"Global price update: {total_stats['positions_updated']} updated, "
            f"{total_stats['positions_skipped']} skipped, "
            f"{total_stats['positions_failed']} failed"
        )
    
    return total_stats
