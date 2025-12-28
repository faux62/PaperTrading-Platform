"""
PaperTrading Platform - Historical Data Collector Service

Background service that collects EOD (End of Day) OHLCV data for all symbols
in the market_universe table. Designed to run once daily after market close.

Architecture:
- Fetches symbols grouped by market_type from market_universe
- Uses batch API calls per market for efficiency  
- Stores data in price_bars table (TimescaleDB hypertable)
- Optimizer reads from DB instead of making live API calls

Benefits:
- Reduces API calls from 155/request to 1/day per market
- Eliminates rate limiting issues during optimization
- Sub-second optimizer response times
- Data always available, no provider downtime impact
"""
import asyncio
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Set
from collections import defaultdict
from loguru import logger

from sqlalchemy import select, func, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import async_session_maker
from app.db.models.market_universe import MarketUniverse
from app.db.models.price_bar import PriceBar, TimeFrame
from app.data_providers.orchestrator import ProviderOrchestrator
from app.data_providers.adapters.base import (
    TimeFrame as ProviderTimeFrame,
    MarketType,
    OHLCV
)


# Map symbol suffixes to market types
EU_SUFFIXES = {'.MI', '.PA', '.DE', '.MC', '.AS', '.L', '.BR', '.CO', '.HE', '.LI', '.LS', '.VX', '.SW'}
UK_SUFFIXES = {'.L'}
JP_SUFFIXES = {'.T', '.TYO'}
HK_SUFFIXES = {'.HK'}


def get_market_type_from_symbol(symbol: str) -> MarketType:
    """Determine market type from symbol suffix."""
    symbol_upper = symbol.upper()
    
    # Check specific markets first
    for suffix in UK_SUFFIXES:
        if symbol_upper.endswith(suffix):
            return MarketType.UK_STOCK
    
    for suffix in JP_SUFFIXES:
        if symbol_upper.endswith(suffix):
            return MarketType.JP_STOCK
            
    for suffix in HK_SUFFIXES:
        if symbol_upper.endswith(suffix):
            return MarketType.HK_STOCK
    
    # EU stocks (excluding UK which was already checked)
    for suffix in EU_SUFFIXES - UK_SUFFIXES:
        if symbol_upper.endswith(suffix):
            return MarketType.EU_STOCK
    
    # Default to US stock
    return MarketType.US_STOCK


class HistoricalDataCollector:
    """
    Service for collecting and storing historical OHLCV data.
    
    Designed to run as a scheduled background job.
    
    Usage:
        collector = HistoricalDataCollector(orchestrator)
        
        # Daily EOD collection
        await collector.collect_eod_data()
        
        # Backfill historical data
        await collector.backfill(days=365)
    """
    
    def __init__(
        self,
        orchestrator: ProviderOrchestrator,
        batch_size: int = 50,
        concurrency: int = 5
    ):
        """
        Initialize the historical data collector.
        
        Args:
            orchestrator: Provider orchestrator for fetching data
            batch_size: Number of symbols to fetch per batch
            concurrency: Max concurrent batch requests
        """
        self.orchestrator = orchestrator
        self.batch_size = batch_size
        self.concurrency = concurrency
        self._semaphore = asyncio.Semaphore(concurrency)
    
    async def get_universe_symbols(
        self,
        currency: Optional[str] = None,
        market_type: Optional[MarketType] = None
    ) -> Dict[MarketType, List[str]]:
        """
        Get symbols from market_universe grouped by market type.
        
        Args:
            currency: Filter by currency (e.g., 'EUR', 'USD')
            market_type: Filter by specific market type
            
        Returns:
            Dict mapping MarketType to list of symbols
        """
        async with async_session_maker() as db:
            query = select(MarketUniverse.symbol).where(MarketUniverse.is_active == True)
            
            if currency:
                query = query.where(MarketUniverse.currency == currency)
            
            result = await db.execute(query)
            symbols = [row[0] for row in result.fetchall()]
        
        # Group by market type
        grouped: Dict[MarketType, List[str]] = defaultdict(list)
        for symbol in symbols:
            mt = get_market_type_from_symbol(symbol)
            if market_type is None or mt == market_type:
                grouped[mt].append(symbol)
        
        return dict(grouped)
    
    async def collect_eod_data(
        self,
        target_date: Optional[date] = None,
        currency: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Collect End-of-Day data for all symbols in universe.
        
        Args:
            target_date: Date to collect data for (default: yesterday)
            currency: Optional currency filter
            
        Returns:
            Dict with collection statistics
        """
        if target_date is None:
            # Default to yesterday (today's data may not be complete)
            target_date = date.today() - timedelta(days=1)
        
        logger.info(f"Starting EOD data collection for {target_date}, currency={currency}")
        
        # Get symbols grouped by market
        symbols_by_market = await self.get_universe_symbols(currency=currency)
        
        stats = {
            "total_symbols": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "markets_processed": 0
        }
        
        for market_type, symbols in symbols_by_market.items():
            logger.info(f"Processing {market_type.value}: {len(symbols)} symbols")
            stats["total_symbols"] += len(symbols)
            
            # Check which symbols already have data for this date
            existing = await self._get_existing_symbols(symbols, target_date)
            to_fetch = [s for s in symbols if s not in existing]
            stats["skipped"] += len(existing)
            
            if not to_fetch:
                logger.info(f"All {len(symbols)} symbols already have data for {target_date}")
                continue
            
            logger.info(f"Fetching {len(to_fetch)} symbols (skipping {len(existing)} existing)")
            
            # Fetch in batches
            results = await self._fetch_market_batch(
                to_fetch, 
                market_type, 
                target_date, 
                target_date
            )
            
            stats["successful"] += results["successful"]
            stats["failed"] += results["failed"]
            stats["markets_processed"] += 1
        
        logger.info(f"EOD collection complete: {stats}")
        return stats
    
    async def backfill(
        self,
        days: int = 365,
        currency: Optional[str] = None,
        force: bool = False
    ) -> Dict[str, int]:
        """
        Backfill historical data for the specified number of days.
        
        Args:
            days: Number of days to backfill
            currency: Optional currency filter
            force: If True, refetch even if data exists
            
        Returns:
            Dict with collection statistics
        """
        end_date = date.today() - timedelta(days=1)
        start_date = end_date - timedelta(days=days)
        
        logger.info(f"Starting backfill from {start_date} to {end_date}, currency={currency}")
        
        symbols_by_market = await self.get_universe_symbols(currency=currency)
        
        total_stats = {
            "total_symbols": 0,
            "successful": 0,
            "failed": 0,
            "bars_inserted": 0
        }
        
        for market_type, symbols in symbols_by_market.items():
            logger.info(f"Backfilling {market_type.value}: {len(symbols)} symbols")
            total_stats["total_symbols"] += len(symbols)
            
            results = await self._fetch_market_batch(
                symbols,
                market_type,
                start_date,
                end_date
            )
            
            total_stats["successful"] += results["successful"]
            total_stats["failed"] += results["failed"]
            total_stats["bars_inserted"] += results.get("bars_inserted", 0)
        
        logger.info(f"Backfill complete: {total_stats}")
        return total_stats
    
    async def _get_existing_symbols(
        self,
        symbols: List[str],
        target_date: date
    ) -> Set[str]:
        """Get symbols that already have data for the target date."""
        async with async_session_maker() as db:
            # Query for symbols that have data for this date
            result = await db.execute(
                select(PriceBar.symbol)
                .where(
                    PriceBar.symbol.in_(symbols),
                    PriceBar.timeframe == TimeFrame.D1,
                    func.date(PriceBar.timestamp) == target_date
                )
                .distinct()
            )
            return {row[0] for row in result.fetchall()}
    
    async def _fetch_market_batch(
        self,
        symbols: List[str],
        market_type: MarketType,
        start_date: date,
        end_date: date
    ) -> Dict[str, int]:
        """
        Fetch historical data for a batch of symbols from the same market.
        
        Uses semaphore to limit concurrency.
        """
        results = {"successful": 0, "failed": 0, "bars_inserted": 0}
        
        async def fetch_symbol(symbol: str):
            async with self._semaphore:
                try:
                    bars = await self.orchestrator.get_historical(
                        symbol=symbol,
                        timeframe=ProviderTimeFrame.DAY,
                        start_date=start_date,
                        end_date=end_date,
                        market_type=market_type
                    )
                    
                    if bars:
                        inserted = await self._store_bars(symbol, bars)
                        return ("success", inserted)
                    else:
                        logger.warning(f"No data returned for {symbol}")
                        return ("failed", 0)
                        
                except Exception as e:
                    logger.error(f"Failed to fetch {symbol}: {e}")
                    return ("failed", 0)
        
        # Process all symbols concurrently (limited by semaphore)
        tasks = [fetch_symbol(s) for s in symbols]
        outcomes = await asyncio.gather(*tasks, return_exceptions=True)
        
        for outcome in outcomes:
            if isinstance(outcome, Exception):
                results["failed"] += 1
            elif outcome[0] == "success":
                results["successful"] += 1
                results["bars_inserted"] += outcome[1]
            else:
                results["failed"] += 1
        
        return results
    
    async def _store_bars(self, symbol: str, bars: List[OHLCV]) -> int:
        """
        Store OHLCV bars in the database using upsert.
        
        Returns number of rows inserted/updated.
        """
        if not bars:
            return 0
        
        async with async_session_maker() as db:
            inserted_count = 0
            
            for bar in bars:
                # Convert timezone-aware timestamp to naive UTC
                ts = bar.timestamp
                if ts.tzinfo is not None:
                    ts = ts.replace(tzinfo=None)
                
                # Use PostgreSQL upsert (INSERT ... ON CONFLICT UPDATE)
                stmt = insert(PriceBar).values(
                    symbol=symbol.upper(),
                    timeframe=TimeFrame.D1,
                    timestamp=ts,
                    open=float(bar.open),
                    high=float(bar.high),
                    low=float(bar.low),
                    close=float(bar.close),
                    volume=bar.volume,
                    source=bar.provider
                ).on_conflict_do_update(
                    index_elements=['symbol', 'timeframe', 'timestamp'],
                    set_={
                        'open': float(bar.open),
                        'high': float(bar.high),
                        'low': float(bar.low),
                        'close': float(bar.close),
                        'volume': bar.volume,
                        'source': bar.provider
                    }
                )
                
                await db.execute(stmt)
                inserted_count += 1
            
            await db.commit()
            
        return inserted_count
    
    async def get_collection_status(self) -> Dict:
        """
        Get status of data collection.
        
        Returns stats about data coverage.
        """
        async with async_session_maker() as db:
            # Count total bars
            total_result = await db.execute(
                select(func.count(PriceBar.id))
                .where(PriceBar.timeframe == TimeFrame.D1)
            )
            total_bars = total_result.scalar()
            
            # Count unique symbols
            symbols_result = await db.execute(
                select(func.count(func.distinct(PriceBar.symbol)))
                .where(PriceBar.timeframe == TimeFrame.D1)
            )
            unique_symbols = symbols_result.scalar()
            
            # Get date range
            range_result = await db.execute(
                select(
                    func.min(PriceBar.timestamp),
                    func.max(PriceBar.timestamp)
                ).where(PriceBar.timeframe == TimeFrame.D1)
            )
            date_range = range_result.first()
            
            # Get latest collection date
            latest_result = await db.execute(
                select(func.max(func.date(PriceBar.timestamp)))
                .where(PriceBar.timeframe == TimeFrame.D1)
            )
            latest_date = latest_result.scalar()
            
            return {
                "total_bars": total_bars or 0,
                "unique_symbols": unique_symbols or 0,
                "earliest_date": date_range[0].isoformat() if date_range[0] else None,
                "latest_date": date_range[1].isoformat() if date_range[1] else None,
                "last_collection": str(latest_date) if latest_date else None
            }
    
    async def collect_via_yfinance(
        self,
        currency: str = "EUR",
        period: str = "5d"
    ) -> Dict[str, int]:
        """
        Collect historical data directly via yfinance using batch download.
        
        Uses yf.download() for efficient batch fetching - single HTTP request
        for multiple symbols instead of individual requests.
        
        Args:
            currency: Currency filter (e.g., 'EUR', 'USD')
            period: yfinance period string ('1d', '5d', '1mo', '3mo', '1y')
            
        Returns:
            Dict with collection statistics
        """
        import yfinance as yf
        
        # Get symbols
        async with async_session_maker() as db:
            result = await db.execute(
                select(MarketUniverse.symbol)
                .where(
                    MarketUniverse.is_active == True,
                    MarketUniverse.currency == currency
                )
            )
            symbols = [r[0] for r in result.fetchall()]
        
        logger.info(f"Collecting {len(symbols)} {currency} symbols via yfinance batch (period={period})")
        
        stats = {
            "total_symbols": len(symbols),
            "successful": 0,
            "failed": 0,
            "bars_inserted": 0
        }
        
        if not symbols:
            return stats
        
        # Process in batches using yf.download() - TRUE batch (1 HTTP request per batch)
        batch_size = 50  # yfinance handles up to ~50 symbols well per request
        
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i+batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(symbols) + batch_size - 1) // batch_size
            
            try:
                # yf.download() makes a SINGLE HTTP request for all symbols in batch
                logger.debug(f"Downloading batch {batch_num}/{total_batches}: {len(batch)} symbols")
                
                # Run synchronous yfinance in thread pool
                def download_batch():
                    return yf.download(
                        tickers=batch,
                        period=period,
                        group_by='ticker',
                        auto_adjust=True,
                        progress=False,
                        threads=False  # Single request, no threading
                    )
                
                loop = asyncio.get_event_loop()
                data = await loop.run_in_executor(None, download_batch)
                
                if data.empty:
                    logger.warning(f"Batch {batch_num} returned empty data")
                    stats["failed"] += len(batch)
                    continue
                
                # Process results - handle both single and multi-symbol DataFrames
                async with async_session_maker() as db:
                    symbols_processed = set()
                    
                    # For single symbol, columns are OHLCV directly
                    # For multiple symbols, columns are MultiIndex (symbol, OHLCV)
                    if len(batch) == 1:
                        sym = batch[0].upper()
                        symbols_processed.add(sym)
                        count = await self._insert_symbol_bars(db, sym, data, stats)
                    else:
                        # MultiIndex columns: (Symbol, OHLCV)
                        for sym in batch:
                            sym_upper = sym.upper()
                            try:
                                if sym_upper in data.columns.get_level_values(0):
                                    sym_data = data[sym_upper]
                                    if not sym_data.dropna(how='all').empty:
                                        symbols_processed.add(sym_upper)
                                        await self._insert_symbol_bars(db, sym_upper, sym_data, stats)
                            except Exception as e:
                                logger.debug(f"Error processing {sym}: {e}")
                    
                    await db.commit()
                    
                    # Count successes and failures
                    stats["successful"] += len(symbols_processed)
                    stats["failed"] += len(batch) - len(symbols_processed)
                
            except Exception as e:
                logger.warning(f"Batch {batch_num} download failed: {e}")
                stats["failed"] += len(batch)
            
            # Small delay between batches to be nice to yfinance
            if i + batch_size < len(symbols):
                await asyncio.sleep(0.3)
        
        logger.info(f"yfinance batch collection complete: {stats}")
        return stats
    
    async def _insert_symbol_bars(
        self,
        db,
        symbol: str,
        data,
        stats: Dict
    ) -> int:
        """Insert OHLCV bars for a single symbol from DataFrame."""
        count = 0
        
        for idx, row in data.iterrows():
            try:
                # Skip rows with NaN values
                if row.isna().all():
                    continue
                    
                ts = idx.to_pydatetime().replace(tzinfo=None)
                
                # Handle column names (may be lowercase or capitalized)
                open_val = row.get('Open') or row.get('open')
                high_val = row.get('High') or row.get('high')
                low_val = row.get('Low') or row.get('low')
                close_val = row.get('Close') or row.get('close')
                volume_val = row.get('Volume') or row.get('volume') or 0
                
                if open_val is None or close_val is None:
                    continue
                
                stmt = insert(PriceBar).values(
                    symbol=symbol,
                    timeframe=TimeFrame.D1,
                    timestamp=ts,
                    open=float(open_val),
                    high=float(high_val),
                    low=float(low_val),
                    close=float(close_val),
                    volume=int(volume_val) if volume_val else 0,
                    source='yfinance'
                ).on_conflict_do_update(
                    index_elements=['symbol', 'timeframe', 'timestamp'],
                    set_={
                        'open': float(open_val),
                        'high': float(high_val),
                        'low': float(low_val),
                        'close': float(close_val),
                        'volume': int(volume_val) if volume_val else 0,
                        'source': 'yfinance'
                    }
                )
                await db.execute(stmt)
                count += 1
                
            except Exception as e:
                logger.debug(f"Error inserting bar for {symbol} at {idx}: {e}")
        
        stats["bars_inserted"] += count
        return count


# Singleton instance (initialized on first import with orchestrator)
_collector_instance: Optional[HistoricalDataCollector] = None


def get_collector(orchestrator: Optional[ProviderOrchestrator] = None) -> HistoricalDataCollector:
    """
    Get or create the singleton collector instance.
    
    Args:
        orchestrator: Provider orchestrator (required on first call)
        
    Returns:
        HistoricalDataCollector instance
    """
    global _collector_instance
    
    if _collector_instance is None:
        if orchestrator is None:
            raise ValueError("Orchestrator required for first initialization")
        _collector_instance = HistoricalDataCollector(orchestrator)
    
    return _collector_instance
