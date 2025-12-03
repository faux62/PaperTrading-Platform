"""
Performance Analytics Service

Calculates portfolio and trading performance metrics:
- Returns analysis (total, annualized, CAGR)
- Risk-adjusted metrics (Sharpe, Sortino, Calmar)
- Attribution analysis
- Time-weighted vs Money-weighted returns
"""
import numpy as np
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


class ReturnType(str, Enum):
    """Type of return calculation."""
    SIMPLE = "simple"
    LOG = "log"
    TIME_WEIGHTED = "time_weighted"
    MONEY_WEIGHTED = "money_weighted"


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics."""
    # Returns
    total_return: float = 0.0
    annualized_return: float = 0.0
    cagr: float = 0.0
    ytd_return: float = 0.0
    mtd_return: float = 0.0
    wtd_return: float = 0.0
    
    # Risk metrics
    volatility: float = 0.0
    annualized_volatility: float = 0.0
    downside_volatility: float = 0.0
    
    # Risk-adjusted returns
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    information_ratio: float = 0.0
    treynor_ratio: float = 0.0
    
    # Drawdown
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0  # Days
    current_drawdown: float = 0.0
    average_drawdown: float = 0.0
    
    # Distribution
    skewness: float = 0.0
    kurtosis: float = 0.0
    var_95: float = 0.0
    cvar_95: float = 0.0
    
    # Win/Loss
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    best_day: float = 0.0
    worst_day: float = 0.0
    
    # Consistency
    positive_periods: int = 0
    negative_periods: int = 0
    
    # Period info
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    trading_days: int = 0
    
    def to_dict(self) -> dict:
        return {
            'total_return': self.total_return,
            'annualized_return': self.annualized_return,
            'cagr': self.cagr,
            'ytd_return': self.ytd_return,
            'mtd_return': self.mtd_return,
            'wtd_return': self.wtd_return,
            'volatility': self.volatility,
            'annualized_volatility': self.annualized_volatility,
            'downside_volatility': self.downside_volatility,
            'sharpe_ratio': self.sharpe_ratio,
            'sortino_ratio': self.sortino_ratio,
            'calmar_ratio': self.calmar_ratio,
            'information_ratio': self.information_ratio,
            'treynor_ratio': self.treynor_ratio,
            'max_drawdown': self.max_drawdown,
            'max_drawdown_duration': self.max_drawdown_duration,
            'current_drawdown': self.current_drawdown,
            'average_drawdown': self.average_drawdown,
            'skewness': self.skewness,
            'kurtosis': self.kurtosis,
            'var_95': self.var_95,
            'cvar_95': self.cvar_95,
            'win_rate': self.win_rate,
            'profit_factor': self.profit_factor,
            'avg_win': self.avg_win,
            'avg_loss': self.avg_loss,
            'best_day': self.best_day,
            'worst_day': self.worst_day,
            'positive_periods': self.positive_periods,
            'negative_periods': self.negative_periods,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'trading_days': self.trading_days
        }


@dataclass
class PeriodReturn:
    """Return for a specific period."""
    period: str  # "daily", "weekly", "monthly", "yearly"
    start_date: datetime
    end_date: datetime
    return_value: float
    cumulative_return: float
    volatility: float
    
    def to_dict(self) -> dict:
        return {
            'period': self.period,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'return': self.return_value,
            'cumulative_return': self.cumulative_return,
            'volatility': self.volatility
        }


@dataclass
class AttributionResult:
    """Performance attribution result."""
    total_return: float
    selection_effect: float  # Stock selection
    allocation_effect: float  # Sector allocation
    interaction_effect: float
    residual: float
    by_sector: Dict[str, Dict[str, float]] = field(default_factory=dict)
    by_asset: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            'total_return': self.total_return,
            'selection_effect': self.selection_effect,
            'allocation_effect': self.allocation_effect,
            'interaction_effect': self.interaction_effect,
            'residual': self.residual,
            'by_sector': self.by_sector,
            'by_asset': self.by_asset
        }


class PerformanceAnalytics:
    """
    Performance analytics calculator.
    
    Features:
    - Multiple return calculation methods
    - Risk-adjusted metrics
    - Drawdown analysis
    - Performance attribution
    - Rolling statistics
    """
    
    def __init__(
        self,
        risk_free_rate: float = 0.02,
        trading_days_per_year: int = 252
    ):
        self.risk_free_rate = risk_free_rate
        self.trading_days = trading_days_per_year
    
    def calculate_metrics(
        self,
        returns: np.ndarray,
        dates: Optional[List[datetime]] = None,
        benchmark_returns: Optional[np.ndarray] = None
    ) -> PerformanceMetrics:
        """
        Calculate comprehensive performance metrics.
        
        Args:
            returns: Array of period returns
            dates: Optional list of dates
            benchmark_returns: Optional benchmark returns for relative metrics
            
        Returns:
            PerformanceMetrics object
        """
        metrics = PerformanceMetrics()
        
        if len(returns) == 0:
            return metrics
        
        returns = np.asarray(returns)
        
        # Period info
        metrics.trading_days = len(returns)
        if dates and len(dates) > 0:
            metrics.start_date = dates[0] if isinstance(dates[0], datetime) else datetime.now()
            metrics.end_date = dates[-1] if isinstance(dates[-1], datetime) else datetime.now()
        
        # Total and annualized returns
        cumulative = np.prod(1 + returns) - 1
        metrics.total_return = float(cumulative)
        
        if metrics.trading_days > 1:
            metrics.annualized_return = float(
                (1 + cumulative) ** (self.trading_days / metrics.trading_days) - 1
            )
            metrics.cagr = metrics.annualized_return
        
        # Period returns (YTD, MTD, WTD)
        if dates and len(dates) > 0:
            metrics.ytd_return = self._calculate_ytd_return(returns, dates)
            metrics.mtd_return = self._calculate_mtd_return(returns, dates)
            metrics.wtd_return = self._calculate_wtd_return(returns, dates)
        
        # Volatility
        metrics.volatility = float(np.std(returns)) if len(returns) > 1 else 0.0
        metrics.annualized_volatility = metrics.volatility * np.sqrt(self.trading_days)
        
        # Downside volatility
        negative_returns = returns[returns < 0]
        if len(negative_returns) > 0:
            metrics.downside_volatility = float(np.std(negative_returns)) * np.sqrt(self.trading_days)
        
        # Risk-adjusted ratios
        excess_return = metrics.annualized_return - self.risk_free_rate
        
        if metrics.annualized_volatility > 0:
            metrics.sharpe_ratio = float(excess_return / metrics.annualized_volatility)
        
        if metrics.downside_volatility > 0:
            metrics.sortino_ratio = float(excess_return / metrics.downside_volatility)
        
        # Drawdown analysis
        dd_metrics = self._calculate_drawdown_metrics(returns)
        metrics.max_drawdown = dd_metrics['max_drawdown']
        metrics.max_drawdown_duration = dd_metrics['max_duration']
        metrics.current_drawdown = dd_metrics['current_drawdown']
        metrics.average_drawdown = dd_metrics['average_drawdown']
        
        if metrics.max_drawdown < 0:
            metrics.calmar_ratio = float(metrics.annualized_return / abs(metrics.max_drawdown))
        
        # Distribution metrics
        if len(returns) > 2:
            metrics.skewness = float(self._calculate_skewness(returns))
            metrics.kurtosis = float(self._calculate_kurtosis(returns))
        
        # VaR and CVaR
        metrics.var_95 = float(np.percentile(returns, 5))
        var_mask = returns <= metrics.var_95
        if np.any(var_mask):
            metrics.cvar_95 = float(np.mean(returns[var_mask]))
        
        # Win/Loss statistics
        positive_returns = returns[returns > 0]
        negative_returns = returns[returns < 0]
        
        metrics.positive_periods = len(positive_returns)
        metrics.negative_periods = len(negative_returns)
        
        if len(returns) > 0:
            metrics.win_rate = float(len(positive_returns) / len(returns))
        
        if len(positive_returns) > 0:
            metrics.avg_win = float(np.mean(positive_returns))
        if len(negative_returns) > 0:
            metrics.avg_loss = float(np.mean(negative_returns))
        
        # Profit factor
        total_gains = np.sum(positive_returns) if len(positive_returns) > 0 else 0
        total_losses = abs(np.sum(negative_returns)) if len(negative_returns) > 0 else 1
        metrics.profit_factor = float(total_gains / total_losses) if total_losses > 0 else float('inf')
        
        # Best/Worst
        metrics.best_day = float(np.max(returns)) if len(returns) > 0 else 0.0
        metrics.worst_day = float(np.min(returns)) if len(returns) > 0 else 0.0
        
        # Benchmark-relative metrics
        if benchmark_returns is not None and len(benchmark_returns) == len(returns):
            relative_metrics = self._calculate_relative_metrics(returns, benchmark_returns)
            metrics.information_ratio = relative_metrics['information_ratio']
            metrics.treynor_ratio = relative_metrics['treynor_ratio']
        
        return metrics
    
    def _calculate_ytd_return(
        self,
        returns: np.ndarray,
        dates: List[datetime]
    ) -> float:
        """Calculate year-to-date return."""
        if not dates:
            return 0.0
        
        current_year = dates[-1].year if isinstance(dates[-1], datetime) else datetime.now().year
        ytd_mask = [d.year == current_year if isinstance(d, datetime) else False for d in dates]
        ytd_returns = returns[ytd_mask]
        
        if len(ytd_returns) > 0:
            return float(np.prod(1 + ytd_returns) - 1)
        return 0.0
    
    def _calculate_mtd_return(
        self,
        returns: np.ndarray,
        dates: List[datetime]
    ) -> float:
        """Calculate month-to-date return."""
        if not dates:
            return 0.0
        
        last_date = dates[-1] if isinstance(dates[-1], datetime) else datetime.now()
        mtd_mask = [
            d.year == last_date.year and d.month == last_date.month 
            if isinstance(d, datetime) else False 
            for d in dates
        ]
        mtd_returns = returns[mtd_mask]
        
        if len(mtd_returns) > 0:
            return float(np.prod(1 + mtd_returns) - 1)
        return 0.0
    
    def _calculate_wtd_return(
        self,
        returns: np.ndarray,
        dates: List[datetime]
    ) -> float:
        """Calculate week-to-date return."""
        if not dates:
            return 0.0
        
        last_date = dates[-1] if isinstance(dates[-1], datetime) else datetime.now()
        week_start = last_date - timedelta(days=last_date.weekday())
        
        wtd_mask = [d >= week_start if isinstance(d, datetime) else False for d in dates]
        wtd_returns = returns[wtd_mask]
        
        if len(wtd_returns) > 0:
            return float(np.prod(1 + wtd_returns) - 1)
        return 0.0
    
    def _calculate_drawdown_metrics(
        self,
        returns: np.ndarray
    ) -> Dict[str, Any]:
        """Calculate drawdown metrics."""
        # Cumulative returns
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = (cumulative - running_max) / running_max
        
        max_dd = float(np.min(drawdowns)) if len(drawdowns) > 0 else 0.0
        current_dd = float(drawdowns[-1]) if len(drawdowns) > 0 else 0.0
        
        # Average drawdown (of negative drawdowns)
        negative_dd = drawdowns[drawdowns < 0]
        avg_dd = float(np.mean(negative_dd)) if len(negative_dd) > 0 else 0.0
        
        # Max drawdown duration
        max_duration = 0
        current_duration = 0
        for dd in drawdowns:
            if dd < 0:
                current_duration += 1
                max_duration = max(max_duration, current_duration)
            else:
                current_duration = 0
        
        return {
            'max_drawdown': max_dd,
            'max_duration': max_duration,
            'current_drawdown': current_dd,
            'average_drawdown': avg_dd
        }
    
    def _calculate_skewness(self, returns: np.ndarray) -> float:
        """Calculate skewness of returns."""
        n = len(returns)
        mean = np.mean(returns)
        std = np.std(returns)
        
        if std == 0:
            return 0.0
        
        return float((n / ((n - 1) * (n - 2))) * np.sum(((returns - mean) / std) ** 3))
    
    def _calculate_kurtosis(self, returns: np.ndarray) -> float:
        """Calculate excess kurtosis of returns."""
        n = len(returns)
        mean = np.mean(returns)
        std = np.std(returns)
        
        if std == 0:
            return 0.0
        
        kurt = (n * (n + 1) / ((n - 1) * (n - 2) * (n - 3))) * np.sum(((returns - mean) / std) ** 4)
        kurt -= 3 * (n - 1) ** 2 / ((n - 2) * (n - 3))
        
        return float(kurt)
    
    def _calculate_relative_metrics(
        self,
        returns: np.ndarray,
        benchmark_returns: np.ndarray
    ) -> Dict[str, float]:
        """Calculate benchmark-relative metrics."""
        # Beta
        covariance = np.cov(returns, benchmark_returns)[0, 1]
        benchmark_var = np.var(benchmark_returns)
        beta = covariance / benchmark_var if benchmark_var > 0 else 1.0
        
        # Alpha
        portfolio_return = np.mean(returns) * self.trading_days
        benchmark_return = np.mean(benchmark_returns) * self.trading_days
        alpha = portfolio_return - self.risk_free_rate - beta * (benchmark_return - self.risk_free_rate)
        
        # Tracking error and Information Ratio
        tracking_diff = returns - benchmark_returns
        tracking_error = np.std(tracking_diff) * np.sqrt(self.trading_days)
        
        info_ratio = 0.0
        if tracking_error > 0:
            excess = np.mean(tracking_diff) * self.trading_days
            info_ratio = excess / tracking_error
        
        # Treynor Ratio
        treynor = 0.0
        if beta != 0:
            treynor = (portfolio_return - self.risk_free_rate) / beta
        
        return {
            'alpha': float(alpha),
            'beta': float(beta),
            'tracking_error': float(tracking_error),
            'information_ratio': float(info_ratio),
            'treynor_ratio': float(treynor)
        }
    
    def calculate_rolling_metrics(
        self,
        returns: np.ndarray,
        window: int = 20,
        metrics: List[str] = None
    ) -> Dict[str, np.ndarray]:
        """
        Calculate rolling performance metrics.
        
        Args:
            returns: Array of returns
            window: Rolling window size
            metrics: List of metrics to calculate
            
        Returns:
            Dictionary of rolling metrics
        """
        metrics = metrics or ['return', 'volatility', 'sharpe']
        results = {}
        
        n = len(returns)
        if n < window:
            return results
        
        for metric in metrics:
            rolling_values = []
            
            for i in range(window - 1, n):
                window_returns = returns[i - window + 1:i + 1]
                
                if metric == 'return':
                    value = np.prod(1 + window_returns) - 1
                elif metric == 'volatility':
                    value = np.std(window_returns) * np.sqrt(self.trading_days)
                elif metric == 'sharpe':
                    ann_ret = (np.prod(1 + window_returns) - 1) * (self.trading_days / window)
                    ann_vol = np.std(window_returns) * np.sqrt(self.trading_days)
                    value = (ann_ret - self.risk_free_rate) / ann_vol if ann_vol > 0 else 0
                else:
                    value = 0
                
                rolling_values.append(value)
            
            results[metric] = np.array(rolling_values)
        
        return results
    
    def calculate_period_returns(
        self,
        returns: np.ndarray,
        dates: List[datetime],
        period: str = "monthly"
    ) -> List[PeriodReturn]:
        """
        Calculate returns by period (weekly, monthly, yearly).
        
        Args:
            returns: Array of returns
            dates: List of dates
            period: Period type
            
        Returns:
            List of PeriodReturn objects
        """
        if len(returns) != len(dates):
            return []
        
        results = []
        cumulative = 1.0
        
        # Group by period
        period_groups = {}
        for i, (ret, date) in enumerate(zip(returns, dates)):
            if not isinstance(date, datetime):
                continue
                
            if period == "weekly":
                key = f"{date.year}-W{date.isocalendar()[1]:02d}"
            elif period == "monthly":
                key = f"{date.year}-{date.month:02d}"
            elif period == "yearly":
                key = str(date.year)
            else:
                key = str(i)
            
            if key not in period_groups:
                period_groups[key] = {'returns': [], 'dates': []}
            period_groups[key]['returns'].append(ret)
            period_groups[key]['dates'].append(date)
        
        # Calculate period metrics
        for key, group in sorted(period_groups.items()):
            period_returns = np.array(group['returns'])
            period_dates = group['dates']
            
            period_return = float(np.prod(1 + period_returns) - 1)
            cumulative *= (1 + period_return)
            
            results.append(PeriodReturn(
                period=key,
                start_date=period_dates[0],
                end_date=period_dates[-1],
                return_value=period_return,
                cumulative_return=cumulative - 1,
                volatility=float(np.std(period_returns)) if len(period_returns) > 1 else 0.0
            ))
        
        return results
    
    def calculate_attribution(
        self,
        portfolio_weights: Dict[str, float],
        asset_returns: Dict[str, float],
        benchmark_weights: Dict[str, float],
        benchmark_returns: Dict[str, float],
        sector_mapping: Optional[Dict[str, str]] = None
    ) -> AttributionResult:
        """
        Calculate Brinson-Fachler performance attribution.
        
        Args:
            portfolio_weights: Portfolio weights by asset
            asset_returns: Asset returns
            benchmark_weights: Benchmark weights
            benchmark_returns: Benchmark returns
            sector_mapping: Asset to sector mapping
            
        Returns:
            AttributionResult with decomposition
        """
        # Calculate portfolio return
        portfolio_return = sum(
            portfolio_weights.get(a, 0) * asset_returns.get(a, 0)
            for a in set(portfolio_weights.keys()) | set(asset_returns.keys())
        )
        
        # Calculate benchmark return
        benchmark_return = sum(
            benchmark_weights.get(a, 0) * benchmark_returns.get(a, 0)
            for a in set(benchmark_weights.keys()) | set(benchmark_returns.keys())
        )
        
        # Calculate effects by asset
        selection_effect = 0.0
        allocation_effect = 0.0
        interaction_effect = 0.0
        by_asset = {}
        
        all_assets = set(portfolio_weights.keys()) | set(benchmark_weights.keys())
        
        for asset in all_assets:
            pw = portfolio_weights.get(asset, 0)
            bw = benchmark_weights.get(asset, 0)
            ar = asset_returns.get(asset, 0)
            br = benchmark_returns.get(asset, ar)  # Use actual if no benchmark
            
            # Selection: Stock picking ability
            selection = bw * (ar - br)
            # Allocation: Sector/asset allocation
            allocation = (pw - bw) * (br - benchmark_return)
            # Interaction: Combined effect
            interaction = (pw - bw) * (ar - br)
            
            selection_effect += selection
            allocation_effect += allocation
            interaction_effect += interaction
            
            by_asset[asset] = {
                'selection': selection,
                'allocation': allocation,
                'interaction': interaction,
                'total': selection + allocation + interaction
            }
        
        # Calculate residual
        total_effect = selection_effect + allocation_effect + interaction_effect
        residual = (portfolio_return - benchmark_return) - total_effect
        
        # Group by sector if mapping provided
        by_sector = {}
        if sector_mapping:
            for asset, effects in by_asset.items():
                sector = sector_mapping.get(asset, 'Other')
                if sector not in by_sector:
                    by_sector[sector] = {'selection': 0, 'allocation': 0, 'interaction': 0, 'total': 0}
                for key in ['selection', 'allocation', 'interaction', 'total']:
                    by_sector[sector][key] += effects[key]
        
        return AttributionResult(
            total_return=portfolio_return - benchmark_return,
            selection_effect=selection_effect,
            allocation_effect=allocation_effect,
            interaction_effect=interaction_effect,
            residual=residual,
            by_sector=by_sector,
            by_asset=by_asset
        )


# Global instance
_performance_analytics: Optional[PerformanceAnalytics] = None


def get_performance_analytics() -> PerformanceAnalytics:
    """Get or create global performance analytics instance."""
    global _performance_analytics
    if _performance_analytics is None:
        _performance_analytics = PerformanceAnalytics()
    return _performance_analytics
