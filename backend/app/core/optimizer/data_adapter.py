"""
Data Adapter for Portfolio Optimizer

Reads historical data primarily from the local price_bars table (populated
by the scheduled EOD collection job). Falls back to live provider calls
only if DB data is insufficient.

Architecture:
- Primary: Read from price_bars table (fast, no rate limits)
- Fallback: Call providers via orchestrator (slow, rate limited)
"""

import pandas as pd
import asyncio
from typing import Dict, Optional, Any, List, Tuple
from datetime import datetime, date, timedelta
import logging

from sqlalchemy import select, func, and_

from app.data_providers.orchestrator import ProviderOrchestrator
from app.data_providers.adapters.base import TimeFrame, MarketType
from app.db.database import async_session_maker
from app.db.models.price_bar import PriceBar, TimeFrame as DBTimeFrame

logger = logging.getLogger(__name__)


# European exchange suffixes
EU_SUFFIXES = {'.MI', '.PA', '.DE', '.MC', '.AS', '.L', '.BR', '.CO', '.HE', '.LI', '.LS', '.VX', '.SW'}


def get_market_type_from_symbol(symbol: str) -> MarketType:
    """Determine market type from symbol suffix."""
    for suffix in EU_SUFFIXES:
        if symbol.upper().endswith(suffix):
            return MarketType.EU_STOCK
    return MarketType.US_STOCK


class OptimizerDataAdapter:
    """
    Adapter that provides historical data to PortfolioOptimizer.
    
    Primary data source: price_bars table (local DB)
    Fallback: ProviderOrchestrator (live API calls)
    
    This design eliminates rate limiting issues and provides
    sub-second response times for the optimizer.
    """
    
    def __init__(
        self,
        orchestrator: ProviderOrchestrator,
        min_data_days: int = 100,  # ~5 months for reliable risk metrics
        use_db_first: bool = True
    ):
        """
        Initialize the adapter.
        
        Args:
            orchestrator: The ProviderOrchestrator instance for fallback
            min_data_days: Minimum days of data required (default 100 for reliable risk metrics)
            use_db_first: If True, try DB first, then fallback to providers
        """
        self.orchestrator = orchestrator
        self.min_data_days = min_data_days
        self.use_db_first = use_db_first
    
    async def get_historical_prices_batch(
        self,
        symbols: list[str],
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """
        Get historical closing prices for multiple symbols as DataFrame.
        
        Primary: Read from price_bars table
        Fallback: Fetch from providers for missing symbols
        
        Args:
            symbols: List of ticker symbols
            start_date: Start datetime
            end_date: End datetime
            
        Returns:
            DataFrame with dates as index and symbols as columns (closing prices)
        """
        # Convert datetime to date
        start = start_date.date() if isinstance(start_date, datetime) else start_date
        end = end_date.date() if isinstance(end_date, datetime) else end_date
        
        logger.info(f"Fetching historical data for {len(symbols)} symbols from {start} to {end}")
        
        all_dfs = []
        symbols_from_db = []
        symbols_need_fetch = []
        
        if self.use_db_first:
            # Try to get data from DB first
            db_results = await self._fetch_from_db(symbols, start, end)
            
            for symbol, df in db_results.items():
                if df is not None and len(df) >= self.min_data_days * 0.7:  # 70% coverage ok
                    all_dfs.append(df)
                    symbols_from_db.append(symbol)
                else:
                    symbols_need_fetch.append(symbol)
            
            logger.info(
                f"DB fetch: {len(symbols_from_db)} symbols with sufficient data, "
                f"{len(symbols_need_fetch)} need provider fetch"
            )
        else:
            symbols_need_fetch = symbols
        
        # Fetch missing symbols from providers
        if symbols_need_fetch:
            provider_results = await self._fetch_from_providers(symbols_need_fetch, start, end)
            for symbol, df in provider_results.items():
                if df is not None and not df.empty:
                    all_dfs.append(df)
        
        if not all_dfs:
            logger.warning("No data retrieved from DB or providers")
            return pd.DataFrame()
        
        # Merge all DataFrames
        result = all_dfs[0]
        for df in all_dfs[1:]:
            result = result.join(df, how='outer')
        
        result.sort_index(inplace=True)
        
        # Forward fill missing values (for different trading calendars)
        result.ffill(inplace=True)
        
        # Drop rows with any NaN (symbols that don't have full history)
        result.dropna(inplace=True)
        
        logger.info(f"Final dataset: {len(result.columns)} symbols, {len(result)} trading days")
        
        return result
    
    async def _fetch_from_db(
        self,
        symbols: List[str],
        start_date: date,
        end_date: date
    ) -> Dict[str, Optional[pd.DataFrame]]:
        """
        Fetch historical data from price_bars table.
        
        Returns dict mapping symbol to DataFrame (or None if no data).
        """
        results = {}
        
        async with async_session_maker() as db:
            for symbol in symbols:
                query = (
                    select(PriceBar.timestamp, PriceBar.close)
                    .where(
                        and_(
                            PriceBar.symbol == symbol.upper(),
                            PriceBar.timeframe == DBTimeFrame.D1,
                            func.date(PriceBar.timestamp) >= start_date,
                            func.date(PriceBar.timestamp) <= end_date
                        )
                    )
                    .order_by(PriceBar.timestamp)
                )
                
                result = await db.execute(query)
                rows = result.fetchall()
                
                if rows:
                    df = pd.DataFrame(rows, columns=['timestamp', symbol])
                    df.set_index('timestamp', inplace=True)
                    results[symbol] = df
                    logger.debug(f"DB: {symbol} has {len(df)} bars")
                else:
                    results[symbol] = None
                    logger.debug(f"DB: {symbol} has no data")
        
        return results
    
    async def _fetch_from_providers(
        self,
        symbols: List[str],
        start_date: date,
        end_date: date
    ) -> Dict[str, Optional[pd.DataFrame]]:
        """
        Fetch historical data from providers via orchestrator.
        
        Returns dict mapping symbol to DataFrame (or None if failed).
        """
        results = {}
        
        async def fetch_one(symbol: str) -> Tuple[str, Optional[pd.DataFrame]]:
            market_type = get_market_type_from_symbol(symbol)
            try:
                bars = await self.orchestrator.get_historical(
                    symbol=symbol,
                    timeframe=TimeFrame.DAY,
                    start_date=start_date,
                    end_date=end_date,
                    market_type=market_type
                )
                
                if bars:
                    data = [{'timestamp': bar.timestamp, symbol: float(bar.close)} for bar in bars]
                    df = pd.DataFrame(data)
                    df.set_index('timestamp', inplace=True)
                    logger.debug(f"Provider: {symbol} fetched {len(df)} bars")
                    return (symbol, df)
                else:
                    logger.debug(f"Provider: {symbol} returned no data")
                    return (symbol, None)
                    
            except Exception as e:
                logger.warning(f"Provider fetch failed for {symbol}: {e}")
                return (symbol, None)
        
        # Fetch all symbols concurrently
        tasks = [fetch_one(s) for s in symbols]
        fetch_results = await asyncio.gather(*tasks)
        
        for symbol, df in fetch_results:
            results[symbol] = df
        
        return results
    
    async def get_historical_prices(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """
        Get historical prices as DataFrame for a single symbol.
        
        Args:
            symbol: Ticker symbol
            start_date: Start datetime
            end_date: End datetime
            
        Returns:
            DataFrame with columns: open, high, low, close, volume
        """
        # Convert datetime to date
        start = start_date.date() if isinstance(start_date, datetime) else start_date
        end = end_date.date() if isinstance(end_date, datetime) else end_date
        
        # Try DB first
        if self.use_db_first:
            df = await self._fetch_full_ohlcv_from_db(symbol, start, end)
            if df is not None and len(df) >= self.min_data_days * 0.7:
                return df
        
        # Fallback to provider
        return await self._fetch_full_ohlcv_from_provider(symbol, start, end)
    
    async def _fetch_full_ohlcv_from_db(
        self,
        symbol: str,
        start_date: date,
        end_date: date
    ) -> Optional[pd.DataFrame]:
        """Fetch full OHLCV data from DB."""
        async with async_session_maker() as db:
            query = (
                select(
                    PriceBar.timestamp,
                    PriceBar.open,
                    PriceBar.high,
                    PriceBar.low,
                    PriceBar.close,
                    PriceBar.volume
                )
                .where(
                    and_(
                        PriceBar.symbol == symbol.upper(),
                        PriceBar.timeframe == DBTimeFrame.D1,
                        func.date(PriceBar.timestamp) >= start_date,
                        func.date(PriceBar.timestamp) <= end_date
                    )
                )
                .order_by(PriceBar.timestamp)
            )
            
            result = await db.execute(query)
            rows = result.fetchall()
            
            if not rows:
                return None
            
            df = pd.DataFrame(rows, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df.set_index('timestamp', inplace=True)
            return df
    
    async def _fetch_full_ohlcv_from_provider(
        self,
        symbol: str,
        start_date: date,
        end_date: date
    ) -> pd.DataFrame:
        """Fetch full OHLCV data from provider."""
        market_type = get_market_type_from_symbol(symbol)
        
        bars = await self.orchestrator.get_historical(
            symbol=symbol,
            timeframe=TimeFrame.DAY,
            start_date=start_date,
            end_date=end_date,
            market_type=market_type
        )
        
        if not bars:
            return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
        
        data = []
        for bar in bars:
            data.append({
                'timestamp': bar.timestamp,
                'open': float(bar.open),
                'high': float(bar.high),
                'low': float(bar.low),
                'close': float(bar.close),
                'volume': int(bar.volume) if bar.volume else 0
            })
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)
        
        return df
    
    async def get_fundamentals(self, symbol: str) -> Dict[str, Any]:
        """
        Get fundamental data for a symbol from market_universe table.
        
        Args:
            symbol: Ticker symbol
            
        Returns:
            Dictionary with fundamental metrics
        """
        from app.db.models.market_universe import MarketUniverse
        
        try:
            # Fetch from market_universe table
            async with async_session_maker() as session:
                result = await session.execute(
                    select(MarketUniverse).where(MarketUniverse.symbol == symbol)
                )
                asset = result.scalar_one_or_none()
                
                if asset:
                    return {
                        'name': asset.name or symbol,
                        'sector': asset.sector,
                        'industry': asset.industry,
                        'market_cap': asset.market_cap,
                        'pe_ratio': None,  # Not stored in market_universe
                        'pb_ratio': None,
                        'dividend_yield': None,
                        'roe': None,
                        'debt_to_equity': None,
                        'revenue_growth': None,
                        'earnings_growth': None,
                        'beta': None
                    }
        except Exception as e:
            logger.warning(f"Failed to get fundamentals from DB for {symbol}: {e}")
        
        # Fallback: try to get basic info from a quote
        try:
            quote = await self.orchestrator.get_quote(symbol)
            return {
                'name': getattr(quote, 'name', symbol),
                'sector': None,
                'industry': None,
                'market_cap': None,
                'pe_ratio': None,
                'pb_ratio': None,
                'dividend_yield': None,
                'roe': None,
                'debt_to_equity': None,
                'revenue_growth': None,
                'earnings_growth': None,
                'beta': None
            }
        except Exception as e:
            logger.warning(f"Failed to get fundamentals for {symbol}: {e}")
            return {
                'name': symbol,
                'sector': None,
                'industry': None,
                'market_cap': None,
                'pe_ratio': None,
                'pb_ratio': None,
                'dividend_yield': None,
                'roe': None,
                'debt_to_equity': None,
                'revenue_growth': None,
                'earnings_growth': None,
                'beta': None
            }
