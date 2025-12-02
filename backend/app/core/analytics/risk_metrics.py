"""
Risk Metrics

Advanced risk analytics:
- Value at Risk (VaR) - Historical, Parametric, Monte Carlo
- Expected Shortfall (CVaR)
- Beta and correlation analysis
- Factor risk decomposition
- Stress testing
"""
import numpy as np
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from loguru import logger


class VaRMethod(str, Enum):
    """VaR calculation method."""
    HISTORICAL = "historical"
    PARAMETRIC = "parametric"
    MONTE_CARLO = "monte_carlo"
    CORNISH_FISHER = "cornish_fisher"


@dataclass
class VaRResult:
    """Value at Risk result."""
    var_value: float  # VaR value (loss)
    confidence_level: float  # e.g., 0.95
    method: VaRMethod
    time_horizon: int  # Days
    cvar_value: float = 0.0  # Conditional VaR
    marginal_var: Dict[str, float] = field(default_factory=dict)  # By asset
    component_var: Dict[str, float] = field(default_factory=dict)  # By asset
    incremental_var: Dict[str, float] = field(default_factory=dict)  # By asset
    
    def to_dict(self) -> dict:
        return {
            'var_value': self.var_value,
            'confidence_level': self.confidence_level,
            'method': self.method.value,
            'time_horizon': self.time_horizon,
            'cvar_value': self.cvar_value,
            'marginal_var': self.marginal_var,
            'component_var': self.component_var,
            'incremental_var': self.incremental_var
        }


@dataclass
class BetaAnalysis:
    """Beta and market risk analysis."""
    beta: float  # Market beta
    alpha: float  # Jensen's alpha
    r_squared: float  # R-squared
    systematic_risk: float  # Beta * market vol
    idiosyncratic_risk: float  # Residual vol
    treynor_ratio: float
    information_ratio: float
    tracking_error: float
    up_capture: float = 0.0  # Upside capture ratio
    down_capture: float = 0.0  # Downside capture ratio
    
    def to_dict(self) -> dict:
        return {
            'beta': self.beta,
            'alpha': self.alpha,
            'r_squared': self.r_squared,
            'systematic_risk': self.systematic_risk,
            'idiosyncratic_risk': self.idiosyncratic_risk,
            'treynor_ratio': self.treynor_ratio,
            'information_ratio': self.information_ratio,
            'tracking_error': self.tracking_error,
            'up_capture': self.up_capture,
            'down_capture': self.down_capture
        }


@dataclass
class CorrelationAnalysis:
    """Correlation and diversification analysis."""
    correlation_matrix: Dict[str, Dict[str, float]]
    average_correlation: float
    diversification_ratio: float
    concentration_ratio: float  # Herfindahl index
    effective_n_assets: float  # 1/concentration
    max_correlation: float
    min_correlation: float
    correlation_clusters: List[List[str]] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            'correlation_matrix': self.correlation_matrix,
            'average_correlation': self.average_correlation,
            'diversification_ratio': self.diversification_ratio,
            'concentration_ratio': self.concentration_ratio,
            'effective_n_assets': self.effective_n_assets,
            'max_correlation': self.max_correlation,
            'min_correlation': self.min_correlation,
            'correlation_clusters': self.correlation_clusters
        }


@dataclass
class StressTestResult:
    """Stress test result."""
    scenario_name: str
    portfolio_impact: float  # Return impact
    var_impact: float  # VaR under stress
    worst_asset: str
    worst_asset_impact: float
    best_asset: str
    best_asset_impact: float
    asset_impacts: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            'scenario_name': self.scenario_name,
            'portfolio_impact': self.portfolio_impact,
            'var_impact': self.var_impact,
            'worst_asset': self.worst_asset,
            'worst_asset_impact': self.worst_asset_impact,
            'best_asset': self.best_asset,
            'best_asset_impact': self.best_asset_impact,
            'asset_impacts': self.asset_impacts
        }


@dataclass
class RiskSummary:
    """Comprehensive risk summary."""
    # VaR metrics
    var_95_1d: float = 0.0
    var_99_1d: float = 0.0
    var_95_10d: float = 0.0
    cvar_95_1d: float = 0.0
    
    # Volatility
    realized_volatility: float = 0.0
    implied_volatility: Optional[float] = None
    volatility_regime: str = "normal"
    
    # Beta
    beta: float = 1.0
    correlation_to_market: float = 0.0
    
    # Drawdown
    current_drawdown: float = 0.0
    max_drawdown: float = 0.0
    
    # Concentration
    top_5_weight: float = 0.0
    herfindahl_index: float = 0.0
    
    # Risk scores
    overall_risk_score: float = 50.0
    market_risk_score: float = 50.0
    concentration_risk_score: float = 50.0
    liquidity_risk_score: float = 50.0
    
    def to_dict(self) -> dict:
        return {
            'var_95_1d': self.var_95_1d,
            'var_99_1d': self.var_99_1d,
            'var_95_10d': self.var_95_10d,
            'cvar_95_1d': self.cvar_95_1d,
            'realized_volatility': self.realized_volatility,
            'implied_volatility': self.implied_volatility,
            'volatility_regime': self.volatility_regime,
            'beta': self.beta,
            'correlation_to_market': self.correlation_to_market,
            'current_drawdown': self.current_drawdown,
            'max_drawdown': self.max_drawdown,
            'top_5_weight': self.top_5_weight,
            'herfindahl_index': self.herfindahl_index,
            'overall_risk_score': self.overall_risk_score,
            'market_risk_score': self.market_risk_score,
            'concentration_risk_score': self.concentration_risk_score,
            'liquidity_risk_score': self.liquidity_risk_score
        }


class RiskMetrics:
    """
    Advanced risk metrics calculator.
    
    Features:
    - VaR calculations (multiple methods)
    - Beta and correlation analysis
    - Factor risk decomposition
    - Stress testing
    - Risk scoring
    """
    
    def __init__(
        self,
        risk_free_rate: float = 0.02,
        trading_days: int = 252
    ):
        self.risk_free_rate = risk_free_rate
        self.trading_days = trading_days
    
    def calculate_var(
        self,
        returns: np.ndarray,
        confidence_level: float = 0.95,
        method: VaRMethod = VaRMethod.HISTORICAL,
        time_horizon: int = 1,
        weights: Optional[np.ndarray] = None,
        n_simulations: int = 10000
    ) -> VaRResult:
        """
        Calculate Value at Risk.
        
        Args:
            returns: Historical returns
            confidence_level: Confidence level (e.g., 0.95)
            method: VaR calculation method
            time_horizon: Time horizon in days
            weights: Portfolio weights (for component VaR)
            n_simulations: Number of Monte Carlo simulations
            
        Returns:
            VaRResult
        """
        returns = np.asarray(returns)
        
        if method == VaRMethod.HISTORICAL:
            var_value = self._historical_var(returns, confidence_level, time_horizon)
        elif method == VaRMethod.PARAMETRIC:
            var_value = self._parametric_var(returns, confidence_level, time_horizon)
        elif method == VaRMethod.MONTE_CARLO:
            var_value = self._monte_carlo_var(returns, confidence_level, time_horizon, n_simulations)
        elif method == VaRMethod.CORNISH_FISHER:
            var_value = self._cornish_fisher_var(returns, confidence_level, time_horizon)
        else:
            var_value = self._historical_var(returns, confidence_level, time_horizon)
        
        # CVaR (Expected Shortfall)
        cvar_value = self._calculate_cvar(returns, confidence_level, time_horizon)
        
        result = VaRResult(
            var_value=var_value,
            confidence_level=confidence_level,
            method=method,
            time_horizon=time_horizon,
            cvar_value=cvar_value
        )
        
        # Component and marginal VaR if weights provided
        if weights is not None and returns.ndim == 2:
            result.marginal_var = self._marginal_var(returns, weights, confidence_level)
            result.component_var = self._component_var(returns, weights, confidence_level)
        
        return result
    
    def _historical_var(
        self,
        returns: np.ndarray,
        confidence_level: float,
        time_horizon: int
    ) -> float:
        """Historical VaR."""
        if returns.ndim > 1:
            portfolio_returns = np.mean(returns, axis=1)  # Simple average
        else:
            portfolio_returns = returns
        
        # Scale to time horizon
        scaled_returns = portfolio_returns * np.sqrt(time_horizon)
        
        percentile = (1 - confidence_level) * 100
        var = -np.percentile(scaled_returns, percentile)
        
        return float(var)
    
    def _parametric_var(
        self,
        returns: np.ndarray,
        confidence_level: float,
        time_horizon: int
    ) -> float:
        """Parametric (variance-covariance) VaR."""
        from scipy import stats
        
        if returns.ndim > 1:
            portfolio_returns = np.mean(returns, axis=1)
        else:
            portfolio_returns = returns
        
        mean = np.mean(portfolio_returns)
        std = np.std(portfolio_returns)
        
        z_score = stats.norm.ppf(1 - confidence_level)
        var = -(mean + z_score * std) * np.sqrt(time_horizon)
        
        return float(var)
    
    def _monte_carlo_var(
        self,
        returns: np.ndarray,
        confidence_level: float,
        time_horizon: int,
        n_simulations: int
    ) -> float:
        """Monte Carlo VaR."""
        if returns.ndim > 1:
            portfolio_returns = np.mean(returns, axis=1)
        else:
            portfolio_returns = returns
        
        mean = np.mean(portfolio_returns)
        std = np.std(portfolio_returns)
        
        # Simulate returns
        simulated = np.random.normal(mean, std, n_simulations) * np.sqrt(time_horizon)
        
        percentile = (1 - confidence_level) * 100
        var = -np.percentile(simulated, percentile)
        
        return float(var)
    
    def _cornish_fisher_var(
        self,
        returns: np.ndarray,
        confidence_level: float,
        time_horizon: int
    ) -> float:
        """Cornish-Fisher VaR with skewness/kurtosis adjustment."""
        from scipy import stats
        
        if returns.ndim > 1:
            portfolio_returns = np.mean(returns, axis=1)
        else:
            portfolio_returns = returns
        
        mean = np.mean(portfolio_returns)
        std = np.std(portfolio_returns)
        skew = stats.skew(portfolio_returns)
        kurt = stats.kurtosis(portfolio_returns)
        
        z = stats.norm.ppf(1 - confidence_level)
        
        # Cornish-Fisher expansion
        z_cf = (z + (z**2 - 1) * skew / 6 + 
                (z**3 - 3*z) * (kurt - 3) / 24 - 
                (2*z**3 - 5*z) * skew**2 / 36)
        
        var = -(mean + z_cf * std) * np.sqrt(time_horizon)
        
        return float(var)
    
    def _calculate_cvar(
        self,
        returns: np.ndarray,
        confidence_level: float,
        time_horizon: int
    ) -> float:
        """Calculate Conditional VaR (Expected Shortfall)."""
        if returns.ndim > 1:
            portfolio_returns = np.mean(returns, axis=1)
        else:
            portfolio_returns = returns
        
        scaled_returns = portfolio_returns * np.sqrt(time_horizon)
        
        percentile = (1 - confidence_level) * 100
        var_threshold = np.percentile(scaled_returns, percentile)
        
        tail_returns = scaled_returns[scaled_returns <= var_threshold]
        
        if len(tail_returns) > 0:
            return float(-np.mean(tail_returns))
        return 0.0
    
    def _marginal_var(
        self,
        returns: np.ndarray,
        weights: np.ndarray,
        confidence_level: float
    ) -> Dict[str, float]:
        """Calculate marginal VaR by asset."""
        cov_matrix = np.cov(returns.T)
        portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        
        from scipy import stats
        z = stats.norm.ppf(confidence_level)
        
        marginal = {}
        for i in range(len(weights)):
            asset_contrib = np.dot(cov_matrix[i], weights) / portfolio_vol
            marginal[f"asset_{i}"] = float(z * asset_contrib)
        
        return marginal
    
    def _component_var(
        self,
        returns: np.ndarray,
        weights: np.ndarray,
        confidence_level: float
    ) -> Dict[str, float]:
        """Calculate component VaR by asset."""
        marginal = self._marginal_var(returns, weights, confidence_level)
        
        component = {}
        for i, (key, mvar) in enumerate(marginal.items()):
            component[key] = float(mvar * weights[i])
        
        return component
    
    def calculate_beta_analysis(
        self,
        portfolio_returns: np.ndarray,
        benchmark_returns: np.ndarray
    ) -> BetaAnalysis:
        """
        Calculate beta and related metrics.
        
        Args:
            portfolio_returns: Portfolio returns
            benchmark_returns: Benchmark returns
            
        Returns:
            BetaAnalysis
        """
        portfolio_returns = np.asarray(portfolio_returns)
        benchmark_returns = np.asarray(benchmark_returns)
        
        # Beta
        covariance = np.cov(portfolio_returns, benchmark_returns)[0, 1]
        benchmark_var = np.var(benchmark_returns)
        beta = covariance / benchmark_var if benchmark_var > 0 else 1.0
        
        # R-squared
        correlation = np.corrcoef(portfolio_returns, benchmark_returns)[0, 1]
        r_squared = correlation ** 2
        
        # Alpha
        portfolio_mean = np.mean(portfolio_returns) * self.trading_days
        benchmark_mean = np.mean(benchmark_returns) * self.trading_days
        alpha = portfolio_mean - self.risk_free_rate - beta * (benchmark_mean - self.risk_free_rate)
        
        # Risk decomposition
        portfolio_vol = np.std(portfolio_returns) * np.sqrt(self.trading_days)
        benchmark_vol = np.std(benchmark_returns) * np.sqrt(self.trading_days)
        systematic_risk = beta * benchmark_vol
        idiosyncratic_risk = np.sqrt(max(0, portfolio_vol**2 - systematic_risk**2))
        
        # Tracking error
        tracking_diff = portfolio_returns - benchmark_returns
        tracking_error = np.std(tracking_diff) * np.sqrt(self.trading_days)
        
        # Information ratio
        info_ratio = 0.0
        if tracking_error > 0:
            info_ratio = (portfolio_mean - benchmark_mean) / tracking_error
        
        # Treynor ratio
        treynor = 0.0
        if beta != 0:
            treynor = (portfolio_mean - self.risk_free_rate) / beta
        
        # Capture ratios
        up_market = benchmark_returns > 0
        down_market = benchmark_returns < 0
        
        up_capture = 0.0
        if np.any(up_market):
            up_capture = np.mean(portfolio_returns[up_market]) / np.mean(benchmark_returns[up_market])
        
        down_capture = 0.0
        if np.any(down_market):
            down_capture = np.mean(portfolio_returns[down_market]) / np.mean(benchmark_returns[down_market])
        
        return BetaAnalysis(
            beta=float(beta),
            alpha=float(alpha),
            r_squared=float(r_squared),
            systematic_risk=float(systematic_risk),
            idiosyncratic_risk=float(idiosyncratic_risk),
            treynor_ratio=float(treynor),
            information_ratio=float(info_ratio),
            tracking_error=float(tracking_error),
            up_capture=float(up_capture),
            down_capture=float(down_capture)
        )
    
    def calculate_correlation_analysis(
        self,
        returns: np.ndarray,
        symbols: List[str],
        weights: Optional[np.ndarray] = None
    ) -> CorrelationAnalysis:
        """
        Calculate correlation and diversification metrics.
        
        Args:
            returns: Returns matrix (n_periods x n_assets)
            symbols: Asset symbols
            weights: Portfolio weights
            
        Returns:
            CorrelationAnalysis
        """
        returns = np.asarray(returns)
        n_assets = returns.shape[1] if returns.ndim > 1 else 1
        
        if n_assets == 1:
            return CorrelationAnalysis(
                correlation_matrix={symbols[0]: {symbols[0]: 1.0}},
                average_correlation=0.0,
                diversification_ratio=1.0,
                concentration_ratio=1.0,
                effective_n_assets=1.0,
                max_correlation=1.0,
                min_correlation=1.0
            )
        
        # Correlation matrix
        corr_matrix = np.corrcoef(returns.T)
        
        corr_dict = {}
        for i, sym1 in enumerate(symbols):
            corr_dict[sym1] = {}
            for j, sym2 in enumerate(symbols):
                corr_dict[sym1][sym2] = float(corr_matrix[i, j])
        
        # Average correlation (off-diagonal)
        off_diagonal = corr_matrix[np.triu_indices(n_assets, k=1)]
        avg_corr = float(np.mean(off_diagonal)) if len(off_diagonal) > 0 else 0.0
        
        # Max and min correlation
        max_corr = float(np.max(off_diagonal)) if len(off_diagonal) > 0 else 1.0
        min_corr = float(np.min(off_diagonal)) if len(off_diagonal) > 0 else 1.0
        
        # Diversification ratio
        if weights is not None:
            weights = np.asarray(weights)
            asset_vols = np.std(returns, axis=0)
            weighted_vol_sum = np.sum(weights * asset_vols)
            
            cov_matrix = np.cov(returns.T)
            portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            
            div_ratio = weighted_vol_sum / portfolio_vol if portfolio_vol > 0 else 1.0
        else:
            div_ratio = 1.0
        
        # Concentration (Herfindahl index)
        if weights is not None:
            herfindahl = float(np.sum(weights ** 2))
        else:
            herfindahl = 1.0 / n_assets  # Equal weight
        
        effective_n = 1.0 / herfindahl if herfindahl > 0 else n_assets
        
        return CorrelationAnalysis(
            correlation_matrix=corr_dict,
            average_correlation=avg_corr,
            diversification_ratio=float(div_ratio),
            concentration_ratio=herfindahl,
            effective_n_assets=effective_n,
            max_correlation=max_corr,
            min_correlation=min_corr
        )
    
    def stress_test(
        self,
        weights: Dict[str, float],
        scenarios: Dict[str, Dict[str, float]]
    ) -> List[StressTestResult]:
        """
        Run stress tests.
        
        Args:
            weights: Portfolio weights
            scenarios: Stress scenarios with asset shocks
            
        Returns:
            List of StressTestResult
        """
        results = []
        
        for scenario_name, shocks in scenarios.items():
            # Calculate portfolio impact
            portfolio_impact = 0.0
            asset_impacts = {}
            
            for asset, weight in weights.items():
                shock = shocks.get(asset, 0)
                impact = weight * shock
                portfolio_impact += impact
                asset_impacts[asset] = float(shock)
            
            # Find worst and best
            if asset_impacts:
                worst_asset = min(asset_impacts, key=asset_impacts.get)
                best_asset = max(asset_impacts, key=asset_impacts.get)
            else:
                worst_asset = ""
                best_asset = ""
            
            results.append(StressTestResult(
                scenario_name=scenario_name,
                portfolio_impact=float(portfolio_impact),
                var_impact=float(portfolio_impact * 2.33),  # Approximate 99% VaR
                worst_asset=worst_asset,
                worst_asset_impact=asset_impacts.get(worst_asset, 0),
                best_asset=best_asset,
                best_asset_impact=asset_impacts.get(best_asset, 0),
                asset_impacts=asset_impacts
            ))
        
        return results
    
    def get_standard_stress_scenarios(self) -> Dict[str, Dict[str, float]]:
        """Get standard stress test scenarios."""
        return {
            "market_crash": {
                "SPY": -0.20,
                "QQQ": -0.25,
                "IWM": -0.22,
                "default": -0.18
            },
            "tech_selloff": {
                "AAPL": -0.15,
                "MSFT": -0.15,
                "GOOGL": -0.18,
                "AMZN": -0.18,
                "NVDA": -0.25,
                "default": -0.05
            },
            "rate_hike": {
                "TLT": -0.10,
                "BND": -0.05,
                "XLF": 0.05,
                "default": -0.02
            },
            "inflation_spike": {
                "TIP": -0.03,
                "GLD": 0.08,
                "XLE": 0.10,
                "default": -0.05
            },
            "recession": {
                "XLY": -0.25,
                "XLF": -0.20,
                "XLU": -0.05,
                "default": -0.15
            }
        }
    
    def calculate_risk_summary(
        self,
        returns: np.ndarray,
        weights: Optional[Dict[str, float]] = None,
        benchmark_returns: Optional[np.ndarray] = None
    ) -> RiskSummary:
        """
        Calculate comprehensive risk summary.
        
        Args:
            returns: Historical returns
            weights: Portfolio weights
            benchmark_returns: Benchmark returns
            
        Returns:
            RiskSummary
        """
        summary = RiskSummary()
        
        returns = np.asarray(returns)
        
        # VaR metrics
        var_95 = self.calculate_var(returns, 0.95, VaRMethod.HISTORICAL, 1)
        var_99 = self.calculate_var(returns, 0.99, VaRMethod.HISTORICAL, 1)
        var_95_10d = self.calculate_var(returns, 0.95, VaRMethod.HISTORICAL, 10)
        
        summary.var_95_1d = var_95.var_value
        summary.var_99_1d = var_99.var_value
        summary.var_95_10d = var_95_10d.var_value
        summary.cvar_95_1d = var_95.cvar_value
        
        # Volatility
        summary.realized_volatility = float(np.std(returns) * np.sqrt(self.trading_days))
        
        # Volatility regime
        recent_vol = np.std(returns[-20:]) if len(returns) >= 20 else np.std(returns)
        long_vol = np.std(returns)
        
        if recent_vol > long_vol * 1.5:
            summary.volatility_regime = "high"
        elif recent_vol < long_vol * 0.7:
            summary.volatility_regime = "low"
        else:
            summary.volatility_regime = "normal"
        
        # Beta
        if benchmark_returns is not None:
            beta_analysis = self.calculate_beta_analysis(returns, benchmark_returns)
            summary.beta = beta_analysis.beta
            summary.correlation_to_market = np.corrcoef(returns, benchmark_returns)[0, 1]
        
        # Drawdown
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = (cumulative - running_max) / running_max
        
        summary.max_drawdown = float(np.min(drawdowns))
        summary.current_drawdown = float(drawdowns[-1]) if len(drawdowns) > 0 else 0.0
        
        # Concentration
        if weights:
            sorted_weights = sorted(weights.values(), reverse=True)
            summary.top_5_weight = sum(sorted_weights[:5])
            summary.herfindahl_index = sum(w**2 for w in weights.values())
        
        # Risk scores (0-100)
        summary.market_risk_score = min(100, summary.beta * 50 + 25)
        summary.concentration_risk_score = min(100, summary.herfindahl_index * 200)
        
        vol_percentile = min(100, summary.realized_volatility / 0.40 * 100)
        summary.overall_risk_score = (
            summary.market_risk_score * 0.4 +
            summary.concentration_risk_score * 0.3 +
            vol_percentile * 0.3
        )
        
        return summary


# Global instance
_risk_metrics: Optional[RiskMetrics] = None


def get_risk_metrics() -> RiskMetrics:
    """Get or create global risk metrics instance."""
    global _risk_metrics
    if _risk_metrics is None:
        _risk_metrics = RiskMetrics()
    return _risk_metrics
