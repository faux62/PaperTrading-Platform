"""
Data Adapter for Portfolio Optimizer

Wraps the ProviderOrchestrator to provide the interface expected by
the optimizer's screener and historical data fetching methods.
"""

import pandas as pd
from typing import Dict, Optional, Any
from datetime import datetime, date, timedelta
import logging

from app.data_providers.orchestrator import ProviderOrchestrator
from app.data_providers.adapters.base import TimeFrame
from app.db.database import async_session_maker
from sqlalchemy import select

logger = logging.getLogger(__name__)


class OptimizerDataAdapter:
    """
    Adapter that wraps ProviderOrchestrator to provide the interface
    expected by PortfolioOptimizer and AssetScreener.
    """
    
    def __init__(self, orchestrator: ProviderOrchestrator):
        """
        Initialize the adapter.
        
        Args:
            orchestrator: The ProviderOrchestrator instance
        """
        self.orchestrator = orchestrator
    
    async def get_historical_prices(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """
        Get historical prices as DataFrame.
        
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
        
        bars = await self.orchestrator.get_historical(
            symbol=symbol,
            timeframe=TimeFrame.DAY,
            start_date=start,
            end_date=end
        )
        
        if not bars:
            return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
        
        # Convert to DataFrame
        data = []
        for bar in bars:
            data.append({
                'timestamp': bar.timestamp,
                'open': float(bar.open),
                'high': float(bar.high),
                'low': float(bar.low),
                'close': float(bar.close),
                'volume': int(bar.volume)
            })
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)
        
        return df
    
    async def get_historical_prices_batch(
        self,
        symbols: list[str],
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """
        Get historical closing prices for multiple symbols as DataFrame.
        
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
        
        batch_data = await self.orchestrator.get_historical_batch(
            symbols=symbols,
            timeframe=TimeFrame.DAY,
            start_date=start,
            end_date=end
        )
        
        # Build DataFrame with closing prices
        all_dfs = []
        for symbol, bars in batch_data.items():
            if not bars:
                continue
            
            data = []
            for bar in bars:
                data.append({
                    'timestamp': bar.timestamp,
                    symbol: float(bar.close)
                })
            
            if data:
                df = pd.DataFrame(data)
                df.set_index('timestamp', inplace=True)
                all_dfs.append(df)
        
        if not all_dfs:
            return pd.DataFrame()
        
        # Merge all DataFrames
        result = all_dfs[0]
        for df in all_dfs[1:]:
            result = result.join(df, how='outer')
        
        result.sort_index(inplace=True)
        
        # Forward fill missing values (for different trading calendars)
        result.ffill(inplace=True)
        
        return result
    
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
