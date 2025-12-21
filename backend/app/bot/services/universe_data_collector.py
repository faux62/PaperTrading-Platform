"""
Universe Data Collector Service

Collects and stores market data for all symbols in the market universe.
Handles:
- Quote updates (real-time during market hours)
- EOD OHLCV data (daily)
- Intelligent batching and rate limiting
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_
from loguru import logger

from app.db.models.market_universe import MarketUniverse, MarketRegion
from app.db.models.price_bar import PriceBar, TimeFrame
from app.data_providers.orchestrator import orchestrator
from app.scheduler.market_hours import get_market_hours_manager
from app.db.redis_client import redis_client


class UniverseDataCollector:
    """
    Collects market data for the entire market universe.
    
    Strategy:
    - High priority symbols (US large cap): Update every 1 minute during market hours
    - Medium priority (EU, Asia): Update every 5 minutes during their market hours
    - EOD data: Collect once daily for all symbols
    """
    
    def __init__(self):
        self.orchestrator = orchestrator  # Global instance
        self.market_hours = get_market_hours_manager()
        self._batch_size = 50  # Symbols per batch
        self._rate_limit_delay = 0.5  # Seconds between batches
        
    async def update_quotes_batch(
        self,
        db: AsyncSession,
        region: Optional[MarketRegion] = None,
        priority: Optional[int] = None,
        limit: int = 100,
    ) -> Dict:
        """
        Update quotes for a batch of symbols.
        
        Args:
            db: Database session
            region: Filter by region (optional)
            priority: Filter by priority (optional)
            limit: Max symbols to update
            
        Returns:
            Stats dict
        """
        stats = {
            "total": 0,
            "updated": 0,
            "failed": 0,
            "skipped": 0,
        }
        
        # Build query for symbols needing update
        query = select(MarketUniverse).where(
            MarketUniverse.is_active == True
        )
        
        if region:
            query = query.where(MarketUniverse.region == region)
        if priority:
            query = query.where(MarketUniverse.priority == priority)
            
        # Order by oldest update first
        query = query.order_by(
            MarketUniverse.last_quote_update.asc().nullsfirst()
        ).limit(limit)
        
        result = await db.execute(query)
        symbols_to_update = result.scalars().all()
        stats["total"] = len(symbols_to_update)
        
        if not symbols_to_update:
            return stats
        
        # Process in batches
        for i in range(0, len(symbols_to_update), self._batch_size):
            batch = symbols_to_update[i:i + self._batch_size]
            
            try:
                # Fetch quotes for batch (pass full symbol entries with region info)
                quotes = await self._fetch_quotes_batch(batch)
                
                # Update database
                for symbol_entry in batch:
                    symbol = symbol_entry.symbol
                    
                    if symbol in quotes and quotes[symbol]:
                        quote = quotes[symbol]
                        # Update timestamp
                        symbol_entry.last_quote_update = datetime.utcnow()
                        symbol_entry.consecutive_failures = 0
                        symbol_entry.last_error = None
                        
                        # Cache in Redis for fast access
                        await redis_client.set_quote(symbol, quote)
                        stats["updated"] += 1
                    else:
                        symbol_entry.consecutive_failures += 1
                        stats["failed"] += 1
                
                await db.commit()
                
            except Exception as e:
                logger.error(f"Batch quote update error: {e}")
                stats["failed"] += len(batch)
            
            
            # Rate limiting
            if i + self._batch_size < len(symbols_to_update):
                await asyncio.sleep(self._rate_limit_delay)
        
        return stats
    
    async def _fetch_quotes_batch(self, symbol_entries: List[MarketUniverse]) -> Dict:
        """
        Fetch quotes for multiple symbols with proper market type routing.
        Uses ALL available providers through the orchestrator failover system.
        
        Args:
            symbol_entries: List of MarketUniverse entries with region info
            
        Returns:
            Dict mapping symbol -> quote data
        """
        from app.data_providers.adapters.base import MarketType
        from collections import defaultdict
        
        quotes = {}
        
        # Map region to market type
        region_to_market_type = {
            MarketRegion.US: MarketType.US_STOCK,
            MarketRegion.UK: MarketType.EU_STOCK,
            MarketRegion.EU: MarketType.EU_STOCK,
            MarketRegion.ASIA: MarketType.ASIA_STOCK,
            MarketRegion.GLOBAL: MarketType.US_STOCK,
        }
        
        # Group symbols by market type for batch fetching
        by_market_type = defaultdict(list)
        for entry in symbol_entries:
            # Handle ETFs separately
            if entry.asset_type and entry.asset_type.value == "etf":
                market_type = MarketType.ETF
            else:
                market_type = region_to_market_type.get(entry.region, MarketType.US_STOCK)
            by_market_type[market_type].append(entry.symbol)
        
        # Fetch each group in batch
        for market_type, symbols in by_market_type.items():
            try:
                batch_quotes = await self.orchestrator.get_quotes(
                    symbols=symbols,
                    market_type=market_type
                )
                
                for symbol, quote in batch_quotes.items():
                    if quote and quote.price:
                        quotes[symbol] = {
                            "price": float(quote.price),
                            "change": float(quote.change) if quote.change else None,
                            "change_percent": float(quote.change_percent) if quote.change_percent else None,
                            "volume": quote.volume,
                            "timestamp": datetime.utcnow().isoformat(),
                            "bid": float(quote.bid) if quote.bid else None,
                            "ask": float(quote.ask) if quote.ask else None,
                            "day_high": float(quote.day_high) if quote.day_high else None,
                            "day_low": float(quote.day_low) if quote.day_low else None,
                            "prev_close": float(quote.prev_close) if quote.prev_close else None,
                        }
                        logger.debug(f"Fetched quote for {symbol}: ${quote.price}")
                
                # Log missing symbols
                for symbol in symbols:
                    if symbol not in batch_quotes:
                        logger.debug(f"No quote returned for {symbol} via orchestrator")
                        
            except Exception as e:
                logger.warning(f"Batch fetch failed for {market_type}: {e}")
                # Symbols in this batch will not have quotes
        
        return quotes
    
    async def collect_eod_data(
        self,
        db: AsyncSession,
        region: Optional[MarketRegion] = None,
        days_back: int = 1,
    ) -> Dict:
        """
        Collect end-of-day OHLCV data for universe symbols.
        
        Args:
            db: Database session
            region: Filter by region
            days_back: Number of days to fetch (default 1 for daily update)
            
        Returns:
            Stats dict
        """
        stats = {
            "total": 0,
            "updated": 0,
            "bars_inserted": 0,
            "failed": 0,
            "skipped": 0,
        }
        
        # Get symbols needing EOD update
        query = select(MarketUniverse).where(
            and_(
                MarketUniverse.is_active == True,
                or_(
                    MarketUniverse.last_ohlcv_update.is_(None),
                    MarketUniverse.last_ohlcv_update < datetime.utcnow() - timedelta(hours=20)
                )
            )
        )
        
        if region:
            query = query.where(MarketUniverse.region == region)
        
        result = await db.execute(query)
        symbols_to_update = result.scalars().all()
        stats["total"] = len(symbols_to_update)
        
        logger.info(f"Collecting EOD data for {len(symbols_to_update)} symbols")
        
        # Process in batches
        for i in range(0, len(symbols_to_update), self._batch_size):
            batch = symbols_to_update[i:i + self._batch_size]
            
            for symbol_entry in batch:
                try:
                    bars = await self._fetch_ohlcv(
                        symbol_entry.symbol,
                        days_back=days_back
                    )
                    
                    if bars:
                        # Insert bars into database
                        for bar in bars:
                            price_bar = PriceBar(
                                symbol=symbol_entry.symbol,
                                timeframe=TimeFrame.D1,
                                timestamp=bar["timestamp"],
                                open=bar["open"],
                                high=bar["high"],
                                low=bar["low"],
                                close=bar["close"],
                                volume=bar.get("volume"),
                                adjusted_close=bar.get("adjusted_close"),
                                source=bar.get("source", "orchestrator"),
                            )
                            db.add(price_bar)
                            stats["bars_inserted"] += 1
                        
                        symbol_entry.last_ohlcv_update = datetime.utcnow()
                        symbol_entry.consecutive_failures = 0
                        stats["updated"] += 1
                    else:
                        symbol_entry.consecutive_failures += 1
                        stats["failed"] += 1
                        
                except Exception as e:
                    logger.debug(f"EOD fetch failed for {symbol_entry.symbol}: {e}")
                    symbol_entry.consecutive_failures += 1
                    symbol_entry.last_error = str(e)[:500]
                    stats["failed"] += 1
            
            try:
                await db.commit()
            except Exception as e:
                logger.error(f"Commit error: {e}")
                await db.rollback()
            
            # Rate limiting
            if i + self._batch_size < len(symbols_to_update):
                await asyncio.sleep(self._rate_limit_delay)
        
        logger.info(
            f"EOD collection complete: {stats['updated']} symbols, "
            f"{stats['bars_inserted']} bars inserted, {stats['failed']} failed"
        )
        
        return stats
    
    async def _fetch_ohlcv(
        self,
        symbol: str,
        days_back: int = 1
    ) -> Optional[List[Dict]]:
        """Fetch OHLCV data for a symbol."""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days_back + 1)
            
            bars = await self.orchestrator.get_historical(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                timeframe="1d"
            )
            
            if bars:
                return [
                    {
                        "timestamp": bar.timestamp if hasattr(bar, 'timestamp') else bar.get("timestamp"),
                        "open": bar.open if hasattr(bar, 'open') else bar.get("open"),
                        "high": bar.high if hasattr(bar, 'high') else bar.get("high"),
                        "low": bar.low if hasattr(bar, 'low') else bar.get("low"),
                        "close": bar.close if hasattr(bar, 'close') else bar.get("close"),
                        "volume": bar.volume if hasattr(bar, 'volume') else bar.get("volume"),
                        "adjusted_close": getattr(bar, 'adjusted_close', None) or bar.get("adjusted_close"),
                        "source": getattr(bar, 'source', None) or bar.get("source"),
                    }
                    for bar in bars
                ]
        except Exception as e:
            logger.debug(f"OHLCV fetch error for {symbol}: {e}")
        
        return None


# Singleton instance
_collector: Optional[UniverseDataCollector] = None


def get_universe_collector() -> UniverseDataCollector:
    """Get singleton collector instance."""
    global _collector
    if _collector is None:
        _collector = UniverseDataCollector()
    return _collector


# =============================================================================
# Scheduled Job Functions
# =============================================================================

async def run_universe_quote_update(db: AsyncSession) -> Dict:
    """
    Scheduled job: Update quotes for universe symbols.
    
    Runs every 5 minutes and updates ALL regions.
    Prioritizes symbols that haven't been updated recently.
    """
    collector = get_universe_collector()
    
    total_stats = {
        "total": 0,
        "updated": 0,
        "failed": 0,
    }
    
    # Update ALL regions every run
    # Symbols are ordered by last_quote_update, so oldest first
    regions_to_update = [
        MarketRegion.US,
        MarketRegion.EU,
        MarketRegion.UK,
        MarketRegion.ASIA,
    ]
    
    for region in regions_to_update:
        stats = await collector.update_quotes_batch(
            db=db,
            region=region,
            priority=None,  # Don't filter by priority
            limit=100  # 100 symbols per region per run
        )
        total_stats["total"] += stats["total"]
        total_stats["updated"] += stats["updated"]
        total_stats["failed"] += stats["failed"]
    
    return total_stats


async def run_universe_eod_collection(db: AsyncSession) -> Dict:
    """
    Scheduled job: Collect EOD data for all universe symbols.
    
    Runs once daily after all markets close.
    """
    collector = get_universe_collector()
    
    # Collect for all regions
    total_stats = {
        "total": 0,
        "updated": 0,
        "bars_inserted": 0,
        "failed": 0,
    }
    
    for region in MarketRegion:
        if region == MarketRegion.GLOBAL:
            continue
            
        stats = await collector.collect_eod_data(
            db=db,
            region=region,
            days_back=1
        )
        
        total_stats["total"] += stats["total"]
        total_stats["updated"] += stats["updated"]
        total_stats["bars_inserted"] += stats["bars_inserted"]
        total_stats["failed"] += stats["failed"]
    
    logger.info(
        f"Universe EOD collection: {total_stats['updated']} symbols, "
        f"{total_stats['bars_inserted']} bars"
    )
    
    return total_stats


async def enrich_symbol_names(db: AsyncSession, limit: int = 50) -> Dict:
    """
    Enrich universe symbols with company names using orchestrator.
    
    This runs periodically to fill in missing symbol names.
    Uses orchestrator's get_company_info for centralized access.
    
    Args:
        db: Database session
        limit: Max symbols to process per run
        
    Returns:
        Stats dict with updated count
    """
    from app.data_providers import orchestrator
    
    stats = {"total": 0, "updated": 0, "failed": 0}
    
    # Get symbols without names (or where name = symbol, meaning not enriched)
    query = select(MarketUniverse).where(
        and_(
            MarketUniverse.is_active == True,
            or_(
                MarketUniverse.name.is_(None),
                MarketUniverse.name == "",
                MarketUniverse.name == MarketUniverse.symbol  # Name same as symbol means not enriched
            )
        )
    ).limit(limit)
    
    result = await db.execute(query)
    symbols_to_enrich = result.scalars().all()
    stats["total"] = len(symbols_to_enrich)
    
    if not symbols_to_enrich:
        return stats
    
    # Process in small batches to avoid rate limiting
    batch_size = 10
    for i in range(0, len(symbols_to_enrich), batch_size):
        batch = symbols_to_enrich[i:i + batch_size]
        
        for entry in batch:
            try:
                # Use orchestrator to get company info
                info = await orchestrator.get_company_info(entry.symbol)
                
                if info:
                    # Get company name
                    name = info.get("longName") or info.get("shortName")
                    if name:
                        entry.name = name[:200]  # Truncate if too long
                        
                    # Also get sector/industry if available
                    if not entry.sector and info.get("sector"):
                        entry.sector = info.get("sector")
                    if not entry.industry and info.get("industry"):
                        entry.industry = info.get("industry")
                    
                    # Get market cap
                    if info.get("marketCap"):
                        from decimal import Decimal
                        entry.market_cap = Decimal(str(info.get("marketCap")))
                    
                    stats["updated"] += 1
                    logger.debug(f"Enriched {entry.symbol}: {name}")
                else:
                    stats["failed"] += 1
                    
            except Exception as e:
                logger.debug(f"Failed to enrich {entry.symbol}: {e}")
                stats["failed"] += 1
        
        # Commit after each batch
        await db.commit()
        
        # Small delay between batches to avoid rate limiting
        await asyncio.sleep(1.0)
    
    return stats


async def run_symbol_enrichment(db: AsyncSession) -> Dict:
    """
    Scheduled job: Enrich symbol names and metadata.
    
    Runs once daily to fill in missing company names.
    """
    stats = await enrich_symbol_names(db, limit=100)
    
    if stats["updated"] > 0:
        logger.info(
            f"Symbol enrichment: {stats['updated']} enriched, "
            f"{stats['failed']} failed"
        )
    
    return stats
