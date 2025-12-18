"""
Asset Screener for Portfolio Optimization

Filters and ranks the investment universe based on:
- Technical indicators (momentum, volatility, trend)
- Fundamental metrics (P/E, market cap, dividend yield)
- Quality scores and rankings
- Sector/industry constraints
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import asyncio


class ScreenerCriteriaType(str, Enum):
    """Types of screening criteria"""
    MOMENTUM = "momentum"
    VALUE = "value"
    QUALITY = "quality"
    VOLATILITY = "volatility"
    DIVIDEND = "dividend"
    SIZE = "size"
    LIQUIDITY = "liquidity"
    TECHNICAL = "technical"


@dataclass
class ScreenerCriteria:
    """Individual screening criterion"""
    criteria_type: ScreenerCriteriaType
    metric: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    rank_percentile: Optional[float] = None  # Top/bottom percentile
    weight: float = 1.0  # Weight for composite scoring


@dataclass
class ScreenedAsset:
    """Asset that passed screening with scores"""
    symbol: str
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None
    scores: Dict[str, float] = field(default_factory=dict)
    total_score: float = 0.0
    rank: int = 0
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScreenerConfig:
    """Configuration for asset screening"""
    universe: List[str] = field(default_factory=list)  # Symbols to screen
    criteria: List[ScreenerCriteria] = field(default_factory=list)
    min_market_cap: Optional[float] = None  # Minimum market cap
    max_market_cap: Optional[float] = None
    sectors: Optional[List[str]] = None  # Allowed sectors
    excluded_sectors: Optional[List[str]] = None
    min_avg_volume: Optional[float] = None  # Minimum daily volume
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    lookback_days: int = 252  # Historical data period
    top_n: Optional[int] = None  # Return top N assets


class AssetScreener:
    """
    Screens and ranks assets based on multiple criteria.
    
    Integrates with data providers to fetch market data and
    applies filters and scoring to identify investment candidates.
    """
    
    def __init__(self, data_provider: Any = None):
        """
        Initialize the asset screener.
        
        Args:
            data_provider: Data provider for fetching market data
        """
        self.data_provider = data_provider
        self._cache: Dict[str, Any] = {}
        self._cache_expiry: Dict[str, datetime] = {}
    
    async def screen(
        self,
        config: ScreenerConfig
    ) -> List[ScreenedAsset]:
        """
        Screen assets based on configuration.
        
        Args:
            config: Screening configuration
            
        Returns:
            List of screened assets with scores and rankings
        """
        # Get universe
        universe = config.universe
        if not universe:
            # Default universe - could be expanded
            universe = await self._get_default_universe()
        
        # Fetch data for all symbols
        data = await self._fetch_screening_data(universe, config.lookback_days)
        
        # Apply filters
        filtered = self._apply_filters(data, config)
        
        # Calculate scores
        scored = self._calculate_scores(filtered, config.criteria)
        
        # Rank
        ranked = self._rank_assets(scored)
        
        # Apply top_n if specified
        if config.top_n:
            ranked = ranked[:config.top_n]
        
        return ranked
    
    async def _get_default_universe(self) -> List[str]:
        """Get default universe of stocks (S&P 500 or similar)"""
        # This would typically fetch from a database or external source
        # For now, return a sample of major stocks
        return [
            "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA",
            "JPM", "V", "UNH", "JNJ", "WMT", "PG", "MA", "HD",
            "CVX", "MRK", "ABBV", "KO", "PEP", "COST", "AVGO",
            "LLY", "MCD", "TMO", "CSCO", "DHR", "ACN", "ABT", "WFC",
            "NEE", "VZ", "CMCSA", "ADBE", "TXN", "PM", "CRM", "NKE",
            "BMY", "RTX", "UPS", "HON", "QCOM", "LOW", "ORCL", "INTC",
            "AMD", "IBM", "GE", "CAT"
        ]
    
    async def _fetch_screening_data(
        self,
        symbols: List[str],
        lookback_days: int
    ) -> Dict[str, Dict]:
        """
        Fetch all required data for screening.
        
        Returns dict with symbol -> data mapping.
        """
        data = {}
        
        for symbol in symbols:
            try:
                asset_data = await self._fetch_single_asset_data(symbol, lookback_days)
                if asset_data:
                    data[symbol] = asset_data
            except Exception as e:
                # Skip assets with data issues
                continue
        
        return data
    
    async def _fetch_single_asset_data(
        self,
        symbol: str,
        lookback_days: int
    ) -> Optional[Dict]:
        """Fetch data for a single asset - REAL DATA ONLY"""
        # Check cache
        cache_key = f"{symbol}_{lookback_days}"
        if cache_key in self._cache:
            if self._cache_expiry.get(cache_key, datetime.min) > datetime.now():
                return self._cache[cache_key]
        
        # Require data provider
        if self.data_provider is None:
            raise ValueError("No data provider configured - cannot fetch asset data")
        
        try:
            # Fetch price history
            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days)
            
            history = await self.data_provider.get_historical_prices(
                symbol, start_date, end_date
            )
            
            if history.empty:
                return None
            
            # Fetch fundamental data
            fundamentals = await self.data_provider.get_fundamentals(symbol)
            
            # Calculate derived metrics
            data = self._process_raw_data(symbol, history, fundamentals)
            
            # Cache
            self._cache[cache_key] = data
            self._cache_expiry[cache_key] = datetime.now() + timedelta(hours=1)
            
            return data
            
        except Exception as e:
            # Log and return None (skip this symbol)
            return None
    
    def _process_raw_data(
        self,
        symbol: str,
        history: pd.DataFrame,
        fundamentals: Dict
    ) -> Dict:
        """Process raw data into screening format"""
        returns = history['close'].pct_change().dropna()
        
        return {
            "symbol": symbol,
            "name": fundamentals.get('name', symbol),
            "sector": fundamentals.get('sector'),
            "industry": fundamentals.get('industry'),
            "price": history['close'].iloc[-1],
            "prices": history['close'].values,
            "returns": returns.values,
            "volume": history['volume'].iloc[-20:].mean(),
            "market_cap": fundamentals.get('market_cap'),
            "pe_ratio": fundamentals.get('pe_ratio'),
            "pb_ratio": fundamentals.get('pb_ratio'),
            "dividend_yield": fundamentals.get('dividend_yield'),
            "roe": fundamentals.get('roe'),
            "debt_to_equity": fundamentals.get('debt_to_equity'),
            "revenue_growth": fundamentals.get('revenue_growth'),
            "earnings_growth": fundamentals.get('earnings_growth'),
            "beta": fundamentals.get('beta')
        }
    
    def _apply_filters(
        self,
        data: Dict[str, Dict],
        config: ScreenerConfig
    ) -> Dict[str, Dict]:
        """Apply hard filters to remove non-qualifying assets"""
        filtered = {}
        
        for symbol, asset in data.items():
            # Market cap filter (handle None values explicitly)
            if config.min_market_cap:
                market_cap = asset.get('market_cap')
                if market_cap is None or market_cap < config.min_market_cap:
                    continue
            if config.max_market_cap:
                market_cap = asset.get('market_cap')
                if market_cap is not None and market_cap > config.max_market_cap:
                    continue
            
            # Sector filter
            if config.sectors:
                if asset.get('sector') not in config.sectors:
                    continue
            if config.excluded_sectors:
                if asset.get('sector') in config.excluded_sectors:
                    continue
            
            # Volume filter (handle None values explicitly)
            if config.min_avg_volume:
                volume = asset.get('volume')
                if volume is None or volume < config.min_avg_volume:
                    continue
            
            # Price filter (handle None values explicitly)
            if config.min_price:
                price = asset.get('price')
                if price is None or price < config.min_price:
                    continue
            if config.max_price:
                price = asset.get('price')
                if price is not None and price > config.max_price:
                    continue
            
            filtered[symbol] = asset
        
        return filtered
    
    def _calculate_scores(
        self,
        data: Dict[str, Dict],
        criteria: List[ScreenerCriteria]
    ) -> List[ScreenedAsset]:
        """Calculate scores for each asset based on criteria"""
        if not criteria:
            # Default criteria
            criteria = self._get_default_criteria()
        
        screened = []
        
        for symbol, asset in data.items():
            scores = {}
            
            for criterion in criteria:
                score = self._calculate_criterion_score(asset, criterion, data)
                scores[criterion.metric] = score
            
            # Calculate weighted total score
            total_weight = sum(c.weight for c in criteria)
            total_score = sum(
                scores.get(c.metric, 0) * c.weight 
                for c in criteria
            ) / total_weight if total_weight > 0 else 0
            
            screened.append(ScreenedAsset(
                symbol=symbol,
                name=asset.get('name', symbol),
                sector=asset.get('sector'),
                industry=asset.get('industry'),
                market_cap=asset.get('market_cap'),
                scores=scores,
                total_score=total_score,
                metrics={
                    'price': asset.get('price'),
                    'pe_ratio': asset.get('pe_ratio'),
                    'dividend_yield': asset.get('dividend_yield'),
                    'beta': asset.get('beta'),
                    'volume': asset.get('volume')
                }
            ))
        
        return screened
    
    def _calculate_criterion_score(
        self,
        asset: Dict,
        criterion: ScreenerCriteria,
        all_data: Dict[str, Dict]
    ) -> float:
        """Calculate score for a single criterion"""
        metric = criterion.metric
        
        # Get metric value for this asset
        value = self._get_metric_value(asset, metric)
        if value is None:
            return 0.0
        
        # Apply min/max filters
        if criterion.min_value is not None and value < criterion.min_value:
            return 0.0
        if criterion.max_value is not None and value > criterion.max_value:
            return 0.0
        
        # Calculate percentile score
        all_values = [
            self._get_metric_value(a, metric)
            for a in all_data.values()
        ]
        all_values = [v for v in all_values if v is not None]
        
        if not all_values:
            return 0.5
        
        percentile = sum(1 for v in all_values if v <= value) / len(all_values)
        
        # Some metrics are better when lower (e.g., volatility, P/E)
        if metric in ['volatility', 'pe_ratio', 'pb_ratio', 'debt_to_equity', 'beta']:
            percentile = 1 - percentile
        
        return percentile
    
    def _get_metric_value(self, asset: Dict, metric: str) -> Optional[float]:
        """Get metric value from asset data"""
        # Direct metrics
        if metric in asset:
            return asset[metric]
        
        # Calculated metrics
        returns = asset.get('returns')
        if returns is None or len(returns) == 0:
            return None
        
        if metric == 'momentum_12m':
            return np.prod(1 + returns[-252:]) - 1 if len(returns) >= 252 else None
        elif metric == 'momentum_6m':
            return np.prod(1 + returns[-126:]) - 1 if len(returns) >= 126 else None
        elif metric == 'momentum_3m':
            return np.prod(1 + returns[-63:]) - 1 if len(returns) >= 63 else None
        elif metric == 'momentum_1m':
            return np.prod(1 + returns[-21:]) - 1 if len(returns) >= 21 else None
        elif metric == 'volatility':
            return np.std(returns) * np.sqrt(252)
        elif metric == 'sharpe':
            mean_ret = np.mean(returns) * 252
            vol = np.std(returns) * np.sqrt(252)
            return mean_ret / vol if vol > 0 else 0
        elif metric == 'sortino':
            mean_ret = np.mean(returns) * 252
            downside = returns[returns < 0]
            down_vol = np.std(downside) * np.sqrt(252) if len(downside) > 0 else 0
            return mean_ret / down_vol if down_vol > 0 else 0
        elif metric == 'max_drawdown':
            cumulative = np.cumprod(1 + returns)
            running_max = np.maximum.accumulate(cumulative)
            drawdown = (cumulative - running_max) / running_max
            return np.min(drawdown)
        
        return None
    
    def _get_default_criteria(self) -> List[ScreenerCriteria]:
        """Get default screening criteria"""
        return [
            ScreenerCriteria(
                criteria_type=ScreenerCriteriaType.MOMENTUM,
                metric='momentum_6m',
                weight=1.5
            ),
            ScreenerCriteria(
                criteria_type=ScreenerCriteriaType.VOLATILITY,
                metric='volatility',
                max_value=0.5,  # Max 50% annualized vol
                weight=1.0
            ),
            ScreenerCriteria(
                criteria_type=ScreenerCriteriaType.QUALITY,
                metric='sharpe',
                weight=1.5
            ),
            ScreenerCriteria(
                criteria_type=ScreenerCriteriaType.VALUE,
                metric='pe_ratio',
                max_value=50,  # Max P/E of 50
                weight=0.8
            ),
            ScreenerCriteria(
                criteria_type=ScreenerCriteriaType.LIQUIDITY,
                metric='volume',
                weight=0.5
            )
        ]
    
    def _rank_assets(self, screened: List[ScreenedAsset]) -> List[ScreenedAsset]:
        """Rank assets by total score"""
        sorted_assets = sorted(screened, key=lambda x: x.total_score, reverse=True)
        
        for i, asset in enumerate(sorted_assets):
            asset.rank = i + 1
        
        return sorted_assets


def get_screener_for_risk_profile(
    risk_profile: str,
    time_horizon_weeks: int
) -> ScreenerConfig:
    """
    Get appropriate screening configuration for risk profile.
    
    Args:
        risk_profile: 'prudent', 'balanced', or 'aggressive'
        time_horizon_weeks: Investment time horizon
        
    Returns:
        ScreenerConfig appropriate for the profile
    """
    if risk_profile == "prudent":
        return ScreenerConfig(
            criteria=[
                ScreenerCriteria(
                    criteria_type=ScreenerCriteriaType.VOLATILITY,
                    metric='volatility',
                    max_value=0.25,  # Low volatility only
                    weight=2.0
                ),
                ScreenerCriteria(
                    criteria_type=ScreenerCriteriaType.DIVIDEND,
                    metric='dividend_yield',
                    min_value=0.01,  # Require some dividend
                    weight=1.5
                ),
                ScreenerCriteria(
                    criteria_type=ScreenerCriteriaType.QUALITY,
                    metric='sharpe',
                    weight=1.0
                ),
                ScreenerCriteria(
                    criteria_type=ScreenerCriteriaType.VALUE,
                    metric='pe_ratio',
                    max_value=25,  # Lower P/E
                    weight=1.0
                )
            ],
            min_market_cap=10e9,  # Large cap only
            min_avg_volume=1e6,
            top_n=30
        )
    
    elif risk_profile == "aggressive":
        return ScreenerConfig(
            criteria=[
                ScreenerCriteria(
                    criteria_type=ScreenerCriteriaType.MOMENTUM,
                    metric='momentum_3m',
                    weight=2.0
                ),
                ScreenerCriteria(
                    criteria_type=ScreenerCriteriaType.MOMENTUM,
                    metric='momentum_6m',
                    weight=1.5
                ),
                ScreenerCriteria(
                    criteria_type=ScreenerCriteriaType.QUALITY,
                    metric='earnings_growth',
                    weight=1.5
                ),
                ScreenerCriteria(
                    criteria_type=ScreenerCriteriaType.QUALITY,
                    metric='revenue_growth',
                    weight=1.0
                )
            ],
            min_market_cap=1e9,  # Include mid-cap
            min_avg_volume=500e3,
            top_n=50
        )
    
    else:  # balanced
        return ScreenerConfig(
            criteria=[
                ScreenerCriteria(
                    criteria_type=ScreenerCriteriaType.MOMENTUM,
                    metric='momentum_6m',
                    weight=1.5
                ),
                ScreenerCriteria(
                    criteria_type=ScreenerCriteriaType.VOLATILITY,
                    metric='volatility',
                    max_value=0.40,
                    weight=1.0
                ),
                ScreenerCriteria(
                    criteria_type=ScreenerCriteriaType.QUALITY,
                    metric='sharpe',
                    weight=1.5
                ),
                ScreenerCriteria(
                    criteria_type=ScreenerCriteriaType.DIVIDEND,
                    metric='dividend_yield',
                    weight=0.8
                ),
                ScreenerCriteria(
                    criteria_type=ScreenerCriteriaType.VALUE,
                    metric='pe_ratio',
                    max_value=35,
                    weight=0.8
                )
            ],
            min_market_cap=5e9,
            min_avg_volume=750e3,
            top_n=40
        )
