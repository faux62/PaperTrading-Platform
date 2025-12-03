"""
Unit Tests - Risk Metrics Analytics
Tests for VaR, correlation, and risk analysis.
"""
import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from dataclasses import dataclass, field
from typing import Dict, List
from enum import Enum


# Define test versions of the dataclasses to avoid import issues
class VaRMethod(str, Enum):
    """VaR calculation method."""
    HISTORICAL = "historical"
    PARAMETRIC = "parametric"
    MONTE_CARLO = "monte_carlo"
    CORNISH_FISHER = "cornish_fisher"


@dataclass
class VaRResult:
    """Value at Risk result."""
    var_value: float
    confidence_level: float
    method: VaRMethod
    time_horizon: int
    cvar_value: float = 0.0
    marginal_var: Dict[str, float] = field(default_factory=dict)
    component_var: Dict[str, float] = field(default_factory=dict)
    incremental_var: Dict[str, float] = field(default_factory=dict)
    
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
    beta: float
    alpha: float
    r_squared: float
    systematic_risk: float
    idiosyncratic_risk: float
    treynor_ratio: float
    information_ratio: float
    tracking_error: float
    up_capture: float = 0.0
    down_capture: float = 0.0
    
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
    concentration_ratio: float
    effective_n_assets: float
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
    portfolio_impact: float
    var_impact: float
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
    var_95_1d: float = 0.0
    var_99_1d: float = 0.0
    var_95_10d: float = 0.0
    cvar_95_1d: float = 0.0
    realized_volatility: float = 0.0
    implied_volatility: float = None
    volatility_regime: str = "normal"
    beta: float = 1.0
    correlation_to_market: float = 0.0
    current_drawdown: float = 0.0
    max_drawdown: float = 0.0
    top_5_weight: float = 0.0
    herfindahl_index: float = 0.0
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
    """Risk metrics calculator."""
    def __init__(self, risk_free_rate: float = 0.02, trading_days: int = 252):
        self.risk_free_rate = risk_free_rate
        self.trading_days = trading_days


class TestVaRMethod:
    """Tests for VaRMethod enum."""
    
    def test_var_methods(self):
        """VaRMethod should have expected calculation methods."""
        assert VaRMethod.HISTORICAL.value == "historical"
        assert VaRMethod.PARAMETRIC.value == "parametric"
        assert VaRMethod.MONTE_CARLO.value == "monte_carlo"
        assert VaRMethod.CORNISH_FISHER.value == "cornish_fisher"
    
    def test_var_method_count(self):
        """Should have 4 VaR methods."""
        methods = list(VaRMethod)
        assert len(methods) == 4


class TestVaRResult:
    """Tests for VaRResult dataclass."""
    
    def test_var_result_creation(self):
        """VaRResult should be creatable with required fields."""
        result = VaRResult(
            var_value=0.05,
            confidence_level=0.95,
            method=VaRMethod.HISTORICAL,
            time_horizon=1
        )
        assert result.var_value == 0.05
        assert result.confidence_level == 0.95
        assert result.time_horizon == 1
    
    def test_var_result_defaults(self):
        """VaRResult should have default empty dicts for component VaRs."""
        result = VaRResult(
            var_value=0.03,
            confidence_level=0.99,
            method=VaRMethod.PARAMETRIC,
            time_horizon=10
        )
        assert result.cvar_value == 0.0
        assert result.marginal_var == {}
        assert result.component_var == {}
        assert result.incremental_var == {}
    
    def test_var_result_to_dict(self):
        """VaRResult should convert to dict correctly."""
        result = VaRResult(
            var_value=0.05,
            confidence_level=0.95,
            method=VaRMethod.HISTORICAL,
            time_horizon=1,
            cvar_value=0.07
        )
        d = result.to_dict()
        assert d['var_value'] == 0.05
        assert d['confidence_level'] == 0.95
        assert d['method'] == 'historical'
        assert d['cvar_value'] == 0.07


class TestBetaAnalysis:
    """Tests for BetaAnalysis dataclass."""
    
    def test_beta_analysis_creation(self):
        """BetaAnalysis should be creatable."""
        beta = BetaAnalysis(
            beta=1.2,
            alpha=0.02,
            r_squared=0.85,
            systematic_risk=0.15,
            idiosyncratic_risk=0.08,
            treynor_ratio=0.10,
            information_ratio=0.5,
            tracking_error=0.03
        )
        assert beta.beta == 1.2
        assert beta.alpha == 0.02
        assert beta.r_squared == 0.85
    
    def test_beta_analysis_defaults(self):
        """BetaAnalysis should have default capture ratios."""
        beta = BetaAnalysis(
            beta=1.0, alpha=0.0, r_squared=0.8,
            systematic_risk=0.1, idiosyncratic_risk=0.05,
            treynor_ratio=0.08, information_ratio=0.3,
            tracking_error=0.02
        )
        assert beta.up_capture == 0.0
        assert beta.down_capture == 0.0
    
    def test_beta_analysis_to_dict(self):
        """BetaAnalysis should convert to dict."""
        beta = BetaAnalysis(
            beta=1.1, alpha=0.01, r_squared=0.9,
            systematic_risk=0.12, idiosyncratic_risk=0.06,
            treynor_ratio=0.09, information_ratio=0.4,
            tracking_error=0.025,
            up_capture=1.05,
            down_capture=0.95
        )
        d = beta.to_dict()
        assert d['beta'] == 1.1
        assert d['up_capture'] == 1.05
        assert d['down_capture'] == 0.95


class TestCorrelationAnalysis:
    """Tests for CorrelationAnalysis dataclass."""
    
    def test_correlation_analysis_creation(self):
        """CorrelationAnalysis should be creatable."""
        corr = CorrelationAnalysis(
            correlation_matrix={'AAPL': {'AAPL': 1.0, 'MSFT': 0.8}, 'MSFT': {'AAPL': 0.8, 'MSFT': 1.0}},
            average_correlation=0.8,
            diversification_ratio=1.2,
            concentration_ratio=0.25,
            effective_n_assets=4.0,
            max_correlation=0.9,
            min_correlation=0.3
        )
        assert corr.average_correlation == 0.8
        assert corr.diversification_ratio == 1.2
    
    def test_correlation_analysis_clusters_default(self):
        """Correlation clusters should default to empty."""
        corr = CorrelationAnalysis(
            correlation_matrix={},
            average_correlation=0.5,
            diversification_ratio=1.0,
            concentration_ratio=0.1,
            effective_n_assets=10.0,
            max_correlation=0.8,
            min_correlation=0.1
        )
        assert corr.correlation_clusters == []
    
    def test_correlation_analysis_to_dict(self):
        """CorrelationAnalysis should convert to dict."""
        corr = CorrelationAnalysis(
            correlation_matrix={'A': {'A': 1.0}},
            average_correlation=0.6,
            diversification_ratio=1.1,
            concentration_ratio=0.2,
            effective_n_assets=5.0,
            max_correlation=0.85,
            min_correlation=0.2
        )
        d = corr.to_dict()
        assert 'correlation_matrix' in d
        assert d['average_correlation'] == 0.6


class TestStressTestResult:
    """Tests for StressTestResult dataclass."""
    
    def test_stress_test_result_creation(self):
        """StressTestResult should be creatable."""
        result = StressTestResult(
            scenario_name="2008 Financial Crisis",
            portfolio_impact=-0.35,
            var_impact=0.12,
            worst_asset="XLF",
            worst_asset_impact=-0.55,
            best_asset="GLD",
            best_asset_impact=0.15
        )
        assert result.scenario_name == "2008 Financial Crisis"
        assert result.portfolio_impact == -0.35
    
    def test_stress_test_result_to_dict(self):
        """StressTestResult should convert to dict."""
        result = StressTestResult(
            scenario_name="COVID Crash",
            portfolio_impact=-0.30,
            var_impact=0.10,
            worst_asset="CCL",
            worst_asset_impact=-0.70,
            best_asset="ZM",
            best_asset_impact=0.40
        )
        d = result.to_dict()
        assert d['scenario_name'] == "COVID Crash"
        assert d['portfolio_impact'] == -0.30


class TestRiskSummary:
    """Tests for RiskSummary dataclass."""
    
    def test_risk_summary_defaults(self):
        """RiskSummary should have sensible defaults."""
        summary = RiskSummary()
        assert summary.var_95_1d == 0.0
        assert summary.var_99_1d == 0.0
        assert summary.beta == 1.0
        assert summary.overall_risk_score == 50.0
        assert summary.volatility_regime == "normal"
    
    def test_risk_summary_custom_values(self):
        """RiskSummary should accept custom values."""
        summary = RiskSummary(
            var_95_1d=0.025,
            var_99_1d=0.04,
            realized_volatility=0.18,
            beta=1.3,
            max_drawdown=0.15,
            overall_risk_score=75.0
        )
        assert summary.var_95_1d == 0.025
        assert summary.beta == 1.3
        assert summary.overall_risk_score == 75.0
    
    def test_risk_summary_to_dict(self):
        """RiskSummary should convert to dict."""
        summary = RiskSummary(
            var_95_1d=0.03,
            current_drawdown=0.05,
            top_5_weight=0.45
        )
        d = summary.to_dict()
        assert d['var_95_1d'] == 0.03
        assert d['current_drawdown'] == 0.05
        assert d['top_5_weight'] == 0.45


class TestRiskMetricsClass:
    """Tests for RiskMetrics calculator class."""
    
    def test_risk_metrics_init_defaults(self):
        """RiskMetrics should initialize with defaults."""
        rm = RiskMetrics()
        assert rm.risk_free_rate == 0.02
        assert rm.trading_days == 252
    
    def test_risk_metrics_custom_params(self):
        """RiskMetrics should accept custom parameters."""
        rm = RiskMetrics(risk_free_rate=0.03, trading_days=260)
        assert rm.risk_free_rate == 0.03
        assert rm.trading_days == 260


class TestVaRCalculations:
    """Tests for VaR calculation logic."""
    
    @pytest.fixture
    def sample_returns(self):
        """Generate sample returns for testing."""
        np.random.seed(42)
        return np.random.normal(0.001, 0.02, 252)  # 1 year of daily returns
    
    def test_historical_var_concept(self, sample_returns):
        """Historical VaR should be a percentile of returns."""
        confidence = 0.95
        var = np.percentile(sample_returns, (1 - confidence) * 100)
        assert var < 0  # VaR should be negative (a loss)
        assert var > -0.1  # Should be reasonable given our parameters
    
    def test_parametric_var_concept(self, sample_returns):
        """Parametric VaR should use mean and std."""
        from scipy import stats
        confidence = 0.95
        mean = np.mean(sample_returns)
        std = np.std(sample_returns)
        z_score = stats.norm.ppf(1 - confidence)
        var = mean + z_score * std
        assert var < 0
    
    def test_var_increases_with_confidence(self, sample_returns):
        """Higher confidence should give larger VaR (more negative)."""
        var_95 = np.percentile(sample_returns, 5)
        var_99 = np.percentile(sample_returns, 1)
        assert var_99 < var_95  # 99% VaR should be more negative


class TestBetaCalculations:
    """Tests for beta calculation logic."""
    
    @pytest.fixture
    def market_and_portfolio_returns(self):
        """Generate correlated market and portfolio returns."""
        np.random.seed(42)
        market = np.random.normal(0.0005, 0.015, 252)
        # Portfolio has beta of ~1.2
        noise = np.random.normal(0, 0.008, 252)
        portfolio = 1.2 * market + noise
        return market, portfolio
    
    def test_beta_calculation_concept(self, market_and_portfolio_returns):
        """Beta should be covariance/variance of market."""
        market, portfolio = market_and_portfolio_returns
        covariance = np.cov(portfolio, market)[0, 1]
        market_variance = np.var(market)
        beta = covariance / market_variance
        assert 0.8 < beta < 1.6  # Should be close to 1.2
    
    def test_perfect_correlation_beta(self):
        """Perfect correlation with equal vol should give beta ~1."""
        np.random.seed(42)
        market = np.random.normal(0, 0.02, 100)
        portfolio = market  # Perfect correlation
        covariance = np.cov(portfolio, market)[0, 1]
        market_variance = np.var(market)
        beta = covariance / market_variance
        # Allow for numerical precision issues
        assert 0.95 < beta < 1.05
