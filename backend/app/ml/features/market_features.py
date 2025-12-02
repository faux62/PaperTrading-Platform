"""
Market Features Calculator

Calculates market-level and cross-asset features:
- Correlations: With index, sector, similar stocks
- Sector analysis: Relative strength, momentum
- Market regime: VIX levels, market breadth
- Macro: Interest rates, currency correlations
"""
from decimal import Decimal
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import numpy as np
from loguru import logger


@dataclass
class MarketFeatures:
    """Container for market-level features."""
    symbol: str
    timestamp: str
    
    # Correlations
    correlation_spy: Optional[float] = None  # S&P 500
    correlation_qqq: Optional[float] = None  # Nasdaq 100
    correlation_iwm: Optional[float] = None  # Russell 2000
    correlation_sector: Optional[float] = None  # Sector ETF
    beta_spy: Optional[float] = None
    beta_sector: Optional[float] = None
    
    # Relative Strength
    rs_vs_spy: Optional[float] = None  # Relative strength vs S&P
    rs_vs_sector: Optional[float] = None  # Relative strength vs sector
    rs_ranking_sector: Optional[float] = None  # Percentile ranking in sector
    rs_ranking_market: Optional[float] = None  # Percentile ranking in market
    
    # Sector Performance
    sector_return_1d: Optional[float] = None
    sector_return_5d: Optional[float] = None
    sector_return_20d: Optional[float] = None
    sector_momentum: Optional[float] = None
    sector_volatility: Optional[float] = None
    
    # Market Regime
    vix_level: Optional[float] = None
    vix_percentile: Optional[float] = None
    market_breadth: Optional[float] = None  # Advance-decline ratio
    new_highs_lows: Optional[float] = None
    put_call_ratio: Optional[float] = None
    
    # Market Trend
    spy_above_sma_50: Optional[bool] = None
    spy_above_sma_200: Optional[bool] = None
    market_regime: Optional[str] = None  # bull, bear, sideways
    
    # Macro Indicators
    treasury_10y_yield: Optional[float] = None
    yield_curve_spread: Optional[float] = None  # 10Y - 2Y
    dxy_change: Optional[float] = None  # Dollar index
    
    # Sector Rotation
    sector_name: Optional[str] = None
    sector_rank: Optional[int] = None  # 1 = best performing
    sector_momentum_score: Optional[float] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {k: v for k, v in self.__dict__.items() if v is not None}
    
    def to_feature_vector(self) -> list[float]:
        """Convert to numerical feature vector for ML."""
        features = []
        for key, value in self.__dict__.items():
            if key in ('symbol', 'timestamp', 'sector_name', 'market_regime'):
                continue
            if isinstance(value, bool):
                features.append(1.0 if value else 0.0)
            elif isinstance(value, (int, float)):
                if value is None or value != value or abs(value) == float('inf'):
                    features.append(0.0)
                else:
                    features.append(float(value))
            elif value is None:
                features.append(0.0)
        return features


# Sector mapping for common stocks
SECTOR_MAPPING = {
    # Technology
    'XLK': 'Technology',
    'AAPL': 'Technology', 'MSFT': 'Technology', 'GOOGL': 'Technology', 
    'META': 'Technology', 'NVDA': 'Technology', 'AMD': 'Technology',
    'INTC': 'Technology', 'CRM': 'Technology', 'ADBE': 'Technology',
    
    # Healthcare
    'XLV': 'Healthcare',
    'JNJ': 'Healthcare', 'UNH': 'Healthcare', 'PFE': 'Healthcare',
    'ABBV': 'Healthcare', 'MRK': 'Healthcare', 'TMO': 'Healthcare',
    
    # Financials
    'XLF': 'Financials',
    'JPM': 'Financials', 'BAC': 'Financials', 'WFC': 'Financials',
    'GS': 'Financials', 'MS': 'Financials', 'C': 'Financials',
    'BRK.B': 'Financials', 'V': 'Financials', 'MA': 'Financials',
    
    # Consumer Discretionary
    'XLY': 'Consumer Discretionary',
    'AMZN': 'Consumer Discretionary', 'TSLA': 'Consumer Discretionary',
    'HD': 'Consumer Discretionary', 'NKE': 'Consumer Discretionary',
    'MCD': 'Consumer Discretionary', 'SBUX': 'Consumer Discretionary',
    
    # Consumer Staples
    'XLP': 'Consumer Staples',
    'PG': 'Consumer Staples', 'KO': 'Consumer Staples', 'PEP': 'Consumer Staples',
    'WMT': 'Consumer Staples', 'COST': 'Consumer Staples',
    
    # Energy
    'XLE': 'Energy',
    'XOM': 'Energy', 'CVX': 'Energy', 'COP': 'Energy',
    
    # Industrials
    'XLI': 'Industrials',
    'BA': 'Industrials', 'CAT': 'Industrials', 'UNP': 'Industrials',
    'GE': 'Industrials', 'RTX': 'Industrials',
    
    # Materials
    'XLB': 'Materials',
    'LIN': 'Materials', 'APD': 'Materials', 'ECL': 'Materials',
    
    # Utilities
    'XLU': 'Utilities',
    'NEE': 'Utilities', 'DUK': 'Utilities', 'SO': 'Utilities',
    
    # Real Estate
    'XLRE': 'Real Estate',
    'PLD': 'Real Estate', 'AMT': 'Real Estate', 'SPG': 'Real Estate',
    
    # Communication Services
    'XLC': 'Communication Services',
    'GOOG': 'Communication Services', 'DIS': 'Communication Services',
    'NFLX': 'Communication Services', 'T': 'Communication Services',
    'VZ': 'Communication Services',
}

SECTOR_ETF_MAPPING = {
    'Technology': 'XLK',
    'Healthcare': 'XLV',
    'Financials': 'XLF',
    'Consumer Discretionary': 'XLY',
    'Consumer Staples': 'XLP',
    'Energy': 'XLE',
    'Industrials': 'XLI',
    'Materials': 'XLB',
    'Utilities': 'XLU',
    'Real Estate': 'XLRE',
    'Communication Services': 'XLC',
}


class MarketFeaturesCalculator:
    """
    Calculates market-level and cross-asset features.
    
    Usage:
        calc = MarketFeaturesCalculator()
        features = calc.calculate_all(
            symbol="AAPL",
            stock_returns=aapl_daily_returns,
            spy_returns=spy_daily_returns,
            sector_returns=xlk_daily_returns,
            market_data={...},
        )
    """
    
    def __init__(self):
        self.min_periods = 60  # Minimum trading days for correlation
    
    def calculate_all(
        self,
        symbol: str,
        stock_returns: List[float],
        spy_returns: List[float],
        qqq_returns: Optional[List[float]] = None,
        iwm_returns: Optional[List[float]] = None,
        sector_returns: Optional[List[float]] = None,
        sector_name: Optional[str] = None,
        market_data: Optional[Dict[str, Any]] = None,
    ) -> MarketFeatures:
        """
        Calculate all market features.
        
        Args:
            symbol: Stock symbol
            stock_returns: Daily returns for the stock (most recent last)
            spy_returns: Daily returns for S&P 500
            qqq_returns: Daily returns for Nasdaq 100 (optional)
            iwm_returns: Daily returns for Russell 2000 (optional)
            sector_returns: Daily returns for sector ETF (optional)
            sector_name: Name of the sector
            market_data: Additional market data (VIX, yield curve, etc.)
        
        Returns:
            MarketFeatures with all calculated metrics
        """
        timestamp = datetime.utcnow().isoformat()
        features = MarketFeatures(symbol=symbol, timestamp=timestamp)
        
        # Infer sector if not provided
        if not sector_name:
            sector_name = SECTOR_MAPPING.get(symbol, 'Unknown')
        features.sector_name = sector_name
        
        stock_arr = np.array(stock_returns)
        spy_arr = np.array(spy_returns)
        
        try:
            # Correlations
            if len(stock_arr) >= self.min_periods and len(spy_arr) >= self.min_periods:
                features.correlation_spy = self._calculate_correlation(stock_arr, spy_arr)
                features.beta_spy = self._calculate_beta(stock_arr, spy_arr)
            
            if qqq_returns and len(qqq_returns) >= self.min_periods:
                qqq_arr = np.array(qqq_returns)
                features.correlation_qqq = self._calculate_correlation(stock_arr, qqq_arr)
            
            if iwm_returns and len(iwm_returns) >= self.min_periods:
                iwm_arr = np.array(iwm_returns)
                features.correlation_iwm = self._calculate_correlation(stock_arr, iwm_arr)
            
            if sector_returns and len(sector_returns) >= self.min_periods:
                sector_arr = np.array(sector_returns)
                features.correlation_sector = self._calculate_correlation(stock_arr, sector_arr)
                features.beta_sector = self._calculate_beta(stock_arr, sector_arr)
            
            # Relative Strength
            features.rs_vs_spy = self._calculate_relative_strength(stock_arr, spy_arr, 20)
            
            if sector_returns:
                sector_arr = np.array(sector_returns)
                features.rs_vs_sector = self._calculate_relative_strength(stock_arr, sector_arr, 20)
            
            # Sector Performance
            if sector_returns:
                sector_arr = np.array(sector_returns)
                features.sector_return_1d = self._calculate_return(sector_arr, 1)
                features.sector_return_5d = self._calculate_return(sector_arr, 5)
                features.sector_return_20d = self._calculate_return(sector_arr, 20)
                features.sector_momentum = self._calculate_momentum_score(sector_arr)
                features.sector_volatility = self._calculate_volatility(sector_arr, 20)
            
            # Market Data
            if market_data:
                features.vix_level = market_data.get('vix')
                features.vix_percentile = market_data.get('vix_percentile')
                features.market_breadth = market_data.get('market_breadth')
                features.new_highs_lows = market_data.get('new_highs_lows')
                features.put_call_ratio = market_data.get('put_call_ratio')
                features.treasury_10y_yield = market_data.get('treasury_10y')
                features.yield_curve_spread = market_data.get('yield_curve_spread')
                features.dxy_change = market_data.get('dxy_change')
                features.spy_above_sma_50 = market_data.get('spy_above_sma_50')
                features.spy_above_sma_200 = market_data.get('spy_above_sma_200')
                
                # Determine market regime
                features.market_regime = self._determine_market_regime(market_data)
            
        except Exception as e:
            logger.warning(f"Error calculating market features for {symbol}: {e}")
        
        return features
    
    def _calculate_correlation(
        self, 
        returns_a: np.ndarray, 
        returns_b: np.ndarray,
        period: int = 60
    ) -> Optional[float]:
        """Calculate rolling correlation."""
        if len(returns_a) < period or len(returns_b) < period:
            return None
        
        corr = np.corrcoef(returns_a[-period:], returns_b[-period:])[0, 1]
        return float(corr) if not np.isnan(corr) else None
    
    def _calculate_beta(
        self,
        stock_returns: np.ndarray,
        market_returns: np.ndarray,
        period: int = 60
    ) -> Optional[float]:
        """Calculate beta vs market/benchmark."""
        if len(stock_returns) < period or len(market_returns) < period:
            return None
        
        stock_slice = stock_returns[-period:]
        market_slice = market_returns[-period:]
        
        covariance = np.cov(stock_slice, market_slice)[0, 1]
        market_variance = np.var(market_slice)
        
        if market_variance == 0:
            return None
        
        beta = covariance / market_variance
        return float(beta) if not np.isnan(beta) else None
    
    def _calculate_relative_strength(
        self,
        stock_returns: np.ndarray,
        benchmark_returns: np.ndarray,
        period: int = 20
    ) -> Optional[float]:
        """Calculate relative strength vs benchmark."""
        if len(stock_returns) < period or len(benchmark_returns) < period:
            return None
        
        stock_perf = np.prod(1 + stock_returns[-period:]) - 1
        bench_perf = np.prod(1 + benchmark_returns[-period:]) - 1
        
        if bench_perf == 0:
            return None
        
        rs = ((1 + stock_perf) / (1 + bench_perf) - 1) * 100
        return float(rs)
    
    def _calculate_return(self, returns: np.ndarray, period: int) -> Optional[float]:
        """Calculate cumulative return over period."""
        if len(returns) < period:
            return None
        
        cum_return = np.prod(1 + returns[-period:]) - 1
        return float(cum_return * 100)
    
    def _calculate_momentum_score(self, returns: np.ndarray) -> Optional[float]:
        """Calculate momentum score (weighted average of returns)."""
        if len(returns) < 20:
            return None
        
        # Weight recent returns more heavily
        weights = np.linspace(0.5, 1.5, 20)
        weighted_returns = returns[-20:] * weights
        score = np.sum(weighted_returns) / np.sum(weights) * 100
        
        return float(score)
    
    def _calculate_volatility(self, returns: np.ndarray, period: int = 20) -> Optional[float]:
        """Calculate annualized volatility."""
        if len(returns) < period:
            return None
        
        vol = np.std(returns[-period:]) * np.sqrt(252) * 100
        return float(vol)
    
    def _determine_market_regime(self, market_data: Dict[str, Any]) -> str:
        """Determine market regime based on indicators."""
        vix = market_data.get('vix', 20)
        spy_above_200 = market_data.get('spy_above_sma_200', True)
        spy_above_50 = market_data.get('spy_above_sma_50', True)
        breadth = market_data.get('market_breadth', 1.0)
        
        # Bull market conditions
        if spy_above_200 and spy_above_50 and vix < 25 and breadth > 1:
            return 'bull'
        
        # Bear market conditions
        if not spy_above_200 and not spy_above_50 and vix > 30:
            return 'bear'
        
        # High volatility
        if vix > 35:
            return 'high_volatility'
        
        return 'sideways'
    
    def calculate_sector_rankings(
        self,
        sector_returns: Dict[str, List[float]],
        period: int = 20
    ) -> Dict[str, int]:
        """
        Calculate sector rankings based on momentum.
        
        Args:
            sector_returns: Dict mapping sector names to return series
            period: Lookback period for ranking
        
        Returns:
            Dict mapping sector names to rank (1 = best)
        """
        performances = {}
        
        for sector, returns in sector_returns.items():
            if len(returns) >= period:
                perf = np.prod(1 + np.array(returns[-period:])) - 1
                performances[sector] = perf
        
        # Sort by performance (descending)
        sorted_sectors = sorted(performances.items(), key=lambda x: x[1], reverse=True)
        
        rankings = {}
        for rank, (sector, _) in enumerate(sorted_sectors, 1):
            rankings[sector] = rank
        
        return rankings
    
    @staticmethod
    def get_feature_names() -> list[str]:
        """Get list of all feature names."""
        return [
            # Correlations
            'correlation_spy', 'correlation_qqq', 'correlation_iwm',
            'correlation_sector', 'beta_spy', 'beta_sector',
            # Relative Strength
            'rs_vs_spy', 'rs_vs_sector', 'rs_ranking_sector', 'rs_ranking_market',
            # Sector Performance
            'sector_return_1d', 'sector_return_5d', 'sector_return_20d',
            'sector_momentum', 'sector_volatility',
            # Market Regime
            'vix_level', 'vix_percentile', 'market_breadth', 'new_highs_lows',
            'put_call_ratio',
            # Market Trend
            'spy_above_sma_50', 'spy_above_sma_200',
            # Macro
            'treasury_10y_yield', 'yield_curve_spread', 'dxy_change',
            # Sector Rotation
            'sector_rank', 'sector_momentum_score',
        ]
    
    @staticmethod
    def get_sector_etf(symbol: str) -> Optional[str]:
        """Get the sector ETF for a given symbol."""
        sector = SECTOR_MAPPING.get(symbol)
        if sector:
            return SECTOR_ETF_MAPPING.get(sector)
        return None


# Module-level instance
calculator = MarketFeaturesCalculator()


def calculate_market_features(
    symbol: str,
    stock_returns: List[float],
    spy_returns: List[float],
    sector_returns: Optional[List[float]] = None,
    market_data: Optional[Dict[str, Any]] = None,
) -> MarketFeatures:
    """
    Convenience function to calculate all market features.
    
    Example:
        market_data = {
            'vix': 18.5,
            'vix_percentile': 35,
            'spy_above_sma_50': True,
            'spy_above_sma_200': True,
            'market_breadth': 1.5,
            'treasury_10y': 4.25,
            'yield_curve_spread': -0.15,
        }
        
        features = calculate_market_features(
            symbol="AAPL",
            stock_returns=aapl_returns[-252:],
            spy_returns=spy_returns[-252:],
            sector_returns=xlk_returns[-252:],
            market_data=market_data,
        )
    """
    sector_name = SECTOR_MAPPING.get(symbol)
    
    return calculator.calculate_all(
        symbol=symbol,
        stock_returns=stock_returns,
        spy_returns=spy_returns,
        sector_returns=sector_returns,
        sector_name=sector_name,
        market_data=market_data,
    )
