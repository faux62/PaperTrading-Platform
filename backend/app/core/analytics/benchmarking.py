"""
Benchmarking Service

Compare portfolio performance against benchmarks:
- Multiple benchmark support
- Relative metrics
- Alpha/Beta analysis
- Rolling comparisons
"""
import numpy as np
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from loguru import logger


class BenchmarkType(str, Enum):
    """Type of benchmark."""
    INDEX = "index"  # Market index (S&P 500, etc.)
    ETF = "etf"  # ETF benchmark
    CUSTOM = "custom"  # Custom benchmark
    RISK_FREE = "risk_free"  # Risk-free rate
    PEER_GROUP = "peer_group"  # Peer group average


@dataclass
class BenchmarkInfo:
    """Benchmark information."""
    symbol: str
    name: str
    benchmark_type: BenchmarkType
    description: str = ""
    
    def to_dict(self) -> dict:
        return {
            'symbol': self.symbol,
            'name': self.name,
            'type': self.benchmark_type.value,
            'description': self.description
        }


@dataclass
class BenchmarkComparison:
    """Comparison between portfolio and benchmark."""
    benchmark: BenchmarkInfo
    
    # Returns comparison
    portfolio_return: float
    benchmark_return: float
    excess_return: float
    
    # Risk comparison
    portfolio_volatility: float
    benchmark_volatility: float
    
    # Risk-adjusted
    portfolio_sharpe: float
    benchmark_sharpe: float
    
    # Relative metrics
    alpha: float
    beta: float
    r_squared: float
    tracking_error: float
    information_ratio: float
    
    # Capture ratios
    up_capture: float
    down_capture: float
    
    # Drawdown comparison
    portfolio_max_drawdown: float
    benchmark_max_drawdown: float
    
    # Period
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        return {
            'benchmark': self.benchmark.to_dict(),
            'portfolio_return': self.portfolio_return,
            'benchmark_return': self.benchmark_return,
            'excess_return': self.excess_return,
            'portfolio_volatility': self.portfolio_volatility,
            'benchmark_volatility': self.benchmark_volatility,
            'portfolio_sharpe': self.portfolio_sharpe,
            'benchmark_sharpe': self.benchmark_sharpe,
            'alpha': self.alpha,
            'beta': self.beta,
            'r_squared': self.r_squared,
            'tracking_error': self.tracking_error,
            'information_ratio': self.information_ratio,
            'up_capture': self.up_capture,
            'down_capture': self.down_capture,
            'portfolio_max_drawdown': self.portfolio_max_drawdown,
            'benchmark_max_drawdown': self.benchmark_max_drawdown,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None
        }


@dataclass 
class RollingBenchmarkMetric:
    """Rolling benchmark comparison metric."""
    dates: List[datetime]
    values: List[float]
    metric_name: str
    window: int
    
    def to_dict(self) -> dict:
        return {
            'dates': [d.isoformat() for d in self.dates],
            'values': self.values,
            'metric_name': self.metric_name,
            'window': self.window
        }


@dataclass
class PeerGroupComparison:
    """Comparison against peer group."""
    portfolio_return: float
    peer_median_return: float
    peer_mean_return: float
    percentile_rank: float  # Where portfolio stands in peer group
    peer_count: int
    outperformance_ratio: float  # % of peers outperformed
    
    peer_returns: List[float] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            'portfolio_return': self.portfolio_return,
            'peer_median_return': self.peer_median_return,
            'peer_mean_return': self.peer_mean_return,
            'percentile_rank': self.percentile_rank,
            'peer_count': self.peer_count,
            'outperformance_ratio': self.outperformance_ratio
        }


class BenchmarkService:
    """
    Benchmarking service for portfolio comparison.
    
    Features:
    - Multiple benchmark comparison
    - Rolling analysis
    - Peer group comparison
    - Period-specific comparison
    """
    
    # Standard benchmarks
    STANDARD_BENCHMARKS = {
        "SPY": BenchmarkInfo("SPY", "S&P 500", BenchmarkType.ETF, "US Large Cap"),
        "QQQ": BenchmarkInfo("QQQ", "NASDAQ 100", BenchmarkType.ETF, "US Tech"),
        "IWM": BenchmarkInfo("IWM", "Russell 2000", BenchmarkType.ETF, "US Small Cap"),
        "EFA": BenchmarkInfo("EFA", "EAFE", BenchmarkType.ETF, "Developed Markets ex-US"),
        "EEM": BenchmarkInfo("EEM", "Emerging Markets", BenchmarkType.ETF, "Emerging Markets"),
        "AGG": BenchmarkInfo("AGG", "US Aggregate Bond", BenchmarkType.ETF, "US Bonds"),
        "VTI": BenchmarkInfo("VTI", "Total US Market", BenchmarkType.ETF, "US Total Market"),
        "60/40": BenchmarkInfo("60/40", "60/40 Portfolio", BenchmarkType.CUSTOM, "60% SPY, 40% AGG"),
    }
    
    def __init__(
        self,
        risk_free_rate: float = 0.02,
        trading_days: int = 252
    ):
        self.risk_free_rate = risk_free_rate
        self.trading_days = trading_days
    
    def compare_to_benchmark(
        self,
        portfolio_returns: np.ndarray,
        benchmark_returns: np.ndarray,
        benchmark_info: Optional[BenchmarkInfo] = None,
        dates: Optional[List[datetime]] = None
    ) -> BenchmarkComparison:
        """
        Compare portfolio to a benchmark.
        
        Args:
            portfolio_returns: Portfolio returns
            benchmark_returns: Benchmark returns
            benchmark_info: Benchmark information
            dates: Date range
            
        Returns:
            BenchmarkComparison
        """
        portfolio_returns = np.asarray(portfolio_returns)
        benchmark_returns = np.asarray(benchmark_returns)
        
        # Ensure same length
        min_len = min(len(portfolio_returns), len(benchmark_returns))
        portfolio_returns = portfolio_returns[-min_len:]
        benchmark_returns = benchmark_returns[-min_len:]
        
        benchmark_info = benchmark_info or BenchmarkInfo(
            "BENCHMARK", "Benchmark", BenchmarkType.INDEX
        )
        
        # Returns
        port_total = float(np.prod(1 + portfolio_returns) - 1)
        bench_total = float(np.prod(1 + benchmark_returns) - 1)
        excess = port_total - bench_total
        
        # Annualized returns
        n_periods = len(portfolio_returns)
        port_ann = float((1 + port_total) ** (self.trading_days / n_periods) - 1) if n_periods > 0 else 0
        bench_ann = float((1 + bench_total) ** (self.trading_days / n_periods) - 1) if n_periods > 0 else 0
        
        # Volatility
        port_vol = float(np.std(portfolio_returns) * np.sqrt(self.trading_days))
        bench_vol = float(np.std(benchmark_returns) * np.sqrt(self.trading_days))
        
        # Sharpe ratios
        port_sharpe = (port_ann - self.risk_free_rate) / port_vol if port_vol > 0 else 0
        bench_sharpe = (bench_ann - self.risk_free_rate) / bench_vol if bench_vol > 0 else 0
        
        # Alpha and Beta
        covariance = np.cov(portfolio_returns, benchmark_returns)[0, 1]
        benchmark_var = np.var(benchmark_returns)
        beta = covariance / benchmark_var if benchmark_var > 0 else 1.0
        
        alpha = port_ann - self.risk_free_rate - beta * (bench_ann - self.risk_free_rate)
        
        # R-squared
        correlation = np.corrcoef(portfolio_returns, benchmark_returns)[0, 1]
        r_squared = correlation ** 2
        
        # Tracking error and Information Ratio
        tracking_diff = portfolio_returns - benchmark_returns
        tracking_error = float(np.std(tracking_diff) * np.sqrt(self.trading_days))
        
        info_ratio = 0.0
        if tracking_error > 0:
            ann_excess = np.mean(tracking_diff) * self.trading_days
            info_ratio = ann_excess / tracking_error
        
        # Capture ratios
        up_market = benchmark_returns > 0
        down_market = benchmark_returns < 0
        
        up_capture = 1.0
        if np.any(up_market) and np.mean(benchmark_returns[up_market]) != 0:
            up_capture = np.mean(portfolio_returns[up_market]) / np.mean(benchmark_returns[up_market])
        
        down_capture = 1.0
        if np.any(down_market) and np.mean(benchmark_returns[down_market]) != 0:
            down_capture = np.mean(portfolio_returns[down_market]) / np.mean(benchmark_returns[down_market])
        
        # Max drawdowns
        port_dd = self._max_drawdown(portfolio_returns)
        bench_dd = self._max_drawdown(benchmark_returns)
        
        # Dates
        start_date = dates[0] if dates and len(dates) > 0 else None
        end_date = dates[-1] if dates and len(dates) > 0 else None
        
        return BenchmarkComparison(
            benchmark=benchmark_info,
            portfolio_return=port_total,
            benchmark_return=bench_total,
            excess_return=excess,
            portfolio_volatility=port_vol,
            benchmark_volatility=bench_vol,
            portfolio_sharpe=float(port_sharpe),
            benchmark_sharpe=float(bench_sharpe),
            alpha=float(alpha),
            beta=float(beta),
            r_squared=float(r_squared),
            tracking_error=tracking_error,
            information_ratio=float(info_ratio),
            up_capture=float(up_capture),
            down_capture=float(down_capture),
            portfolio_max_drawdown=port_dd,
            benchmark_max_drawdown=bench_dd,
            start_date=start_date,
            end_date=end_date
        )
    
    def compare_to_multiple_benchmarks(
        self,
        portfolio_returns: np.ndarray,
        benchmark_data: Dict[str, np.ndarray],
        dates: Optional[List[datetime]] = None
    ) -> List[BenchmarkComparison]:
        """
        Compare portfolio to multiple benchmarks.
        
        Args:
            portfolio_returns: Portfolio returns
            benchmark_data: Dictionary of benchmark returns
            dates: Date range
            
        Returns:
            List of BenchmarkComparison
        """
        results = []
        
        for symbol, returns in benchmark_data.items():
            benchmark_info = self.STANDARD_BENCHMARKS.get(
                symbol,
                BenchmarkInfo(symbol, symbol, BenchmarkType.INDEX)
            )
            
            comparison = self.compare_to_benchmark(
                portfolio_returns,
                returns,
                benchmark_info,
                dates
            )
            results.append(comparison)
        
        return results
    
    def calculate_rolling_comparison(
        self,
        portfolio_returns: np.ndarray,
        benchmark_returns: np.ndarray,
        window: int = 60,
        metrics: Optional[List[str]] = None,
        dates: Optional[List[datetime]] = None
    ) -> Dict[str, RollingBenchmarkMetric]:
        """
        Calculate rolling benchmark comparison metrics.
        
        Args:
            portfolio_returns: Portfolio returns
            benchmark_returns: Benchmark returns
            window: Rolling window size
            metrics: Metrics to calculate
            dates: Date range
            
        Returns:
            Dictionary of rolling metrics
        """
        metrics = metrics or ['excess_return', 'beta', 'tracking_error', 'information_ratio']
        
        portfolio_returns = np.asarray(portfolio_returns)
        benchmark_returns = np.asarray(benchmark_returns)
        
        n = len(portfolio_returns)
        if n < window:
            return {}
        
        results = {}
        
        for metric in metrics:
            values = []
            metric_dates = []
            
            for i in range(window - 1, n):
                port_window = portfolio_returns[i - window + 1:i + 1]
                bench_window = benchmark_returns[i - window + 1:i + 1]
                
                if metric == 'excess_return':
                    port_ret = np.prod(1 + port_window) - 1
                    bench_ret = np.prod(1 + bench_window) - 1
                    value = port_ret - bench_ret
                    
                elif metric == 'beta':
                    cov = np.cov(port_window, bench_window)[0, 1]
                    var = np.var(bench_window)
                    value = cov / var if var > 0 else 1.0
                    
                elif metric == 'tracking_error':
                    diff = port_window - bench_window
                    value = np.std(diff) * np.sqrt(self.trading_days)
                    
                elif metric == 'information_ratio':
                    diff = port_window - bench_window
                    te = np.std(diff) * np.sqrt(self.trading_days)
                    excess = np.mean(diff) * self.trading_days
                    value = excess / te if te > 0 else 0
                    
                elif metric == 'alpha':
                    cov = np.cov(port_window, bench_window)[0, 1]
                    var = np.var(bench_window)
                    beta = cov / var if var > 0 else 1.0
                    
                    port_ann = (np.prod(1 + port_window) - 1) * (self.trading_days / window)
                    bench_ann = (np.prod(1 + bench_window) - 1) * (self.trading_days / window)
                    
                    value = port_ann - self.risk_free_rate - beta * (bench_ann - self.risk_free_rate)
                    
                else:
                    value = 0
                
                values.append(float(value))
                if dates and i < len(dates):
                    metric_dates.append(dates[i])
            
            if not metric_dates and dates:
                metric_dates = dates[window - 1:]
            elif not metric_dates:
                metric_dates = [datetime.now() + timedelta(days=i) for i in range(len(values))]
            
            results[metric] = RollingBenchmarkMetric(
                dates=metric_dates[:len(values)],
                values=values,
                metric_name=metric,
                window=window
            )
        
        return results
    
    def compare_to_peer_group(
        self,
        portfolio_returns: np.ndarray,
        peer_returns: List[np.ndarray]
    ) -> PeerGroupComparison:
        """
        Compare portfolio to peer group.
        
        Args:
            portfolio_returns: Portfolio returns
            peer_returns: List of peer returns
            
        Returns:
            PeerGroupComparison
        """
        portfolio_returns = np.asarray(portfolio_returns)
        
        # Calculate total returns for all
        port_total = float(np.prod(1 + portfolio_returns) - 1)
        
        peer_totals = []
        for peer in peer_returns:
            peer = np.asarray(peer)
            # Match length
            min_len = min(len(portfolio_returns), len(peer))
            peer_total = float(np.prod(1 + peer[-min_len:]) - 1)
            peer_totals.append(peer_total)
        
        if not peer_totals:
            return PeerGroupComparison(
                portfolio_return=port_total,
                peer_median_return=0,
                peer_mean_return=0,
                percentile_rank=50,
                peer_count=0,
                outperformance_ratio=0
            )
        
        peer_median = float(np.median(peer_totals))
        peer_mean = float(np.mean(peer_totals))
        
        # Percentile rank
        all_returns = sorted(peer_totals + [port_total])
        rank = all_returns.index(port_total) + 1
        percentile = (rank / len(all_returns)) * 100
        
        # Outperformance ratio
        outperformed = sum(1 for p in peer_totals if port_total > p)
        outperformance_ratio = outperformed / len(peer_totals)
        
        return PeerGroupComparison(
            portfolio_return=port_total,
            peer_median_return=peer_median,
            peer_mean_return=peer_mean,
            percentile_rank=float(percentile),
            peer_count=len(peer_totals),
            outperformance_ratio=float(outperformance_ratio),
            peer_returns=peer_totals
        )
    
    def _max_drawdown(self, returns: np.ndarray) -> float:
        """Calculate maximum drawdown."""
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = (cumulative - running_max) / running_max
        return float(np.min(drawdowns)) if len(drawdowns) > 0 else 0.0
    
    def get_benchmark_returns(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> Optional[np.ndarray]:
        """
        Get benchmark returns (placeholder for data provider integration).
        
        In production, this would fetch from a data provider.
        """
        # This is a placeholder - in production would call data provider
        logger.warning(f"Benchmark data fetch not implemented for {symbol}")
        return None
    
    def create_custom_benchmark(
        self,
        weights: Dict[str, float],
        component_returns: Dict[str, np.ndarray]
    ) -> np.ndarray:
        """
        Create custom blended benchmark.
        
        Args:
            weights: Component weights
            component_returns: Returns for each component
            
        Returns:
            Blended benchmark returns
        """
        # Find common length
        lengths = [len(r) for r in component_returns.values()]
        if not lengths:
            return np.array([])
        
        min_len = min(lengths)
        
        # Calculate weighted returns
        blended = np.zeros(min_len)
        total_weight = 0
        
        for symbol, weight in weights.items():
            if symbol in component_returns:
                returns = component_returns[symbol][-min_len:]
                blended += weight * returns
                total_weight += weight
        
        # Normalize if weights don't sum to 1
        if total_weight > 0 and total_weight != 1.0:
            blended /= total_weight
        
        return blended


# Global instance
_benchmark_service: Optional[BenchmarkService] = None


def get_benchmark_service() -> BenchmarkService:
    """Get or create global benchmark service instance."""
    global _benchmark_service
    if _benchmark_service is None:
        _benchmark_service = BenchmarkService()
    return _benchmark_service
