"""
Risk Models for Portfolio Optimization

Provides various risk measurement and modeling approaches:
- Historical volatility and correlation
- Exponentially weighted moving average (EWMA)
- GARCH models for volatility forecasting
- Risk metrics: VaR, CVaR, Maximum Drawdown
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from scipy import stats


class RiskModelType(str, Enum):
    """Available risk model types"""
    SAMPLE = "sample"                    # Sample covariance
    EWMA = "ewma"                         # Exponentially weighted
    LEDOIT_WOLF = "ledoit_wolf"          # Ledoit-Wolf shrinkage
    CONSTANT_CORRELATION = "const_corr"  # Constant correlation model


@dataclass
class RiskMetrics:
    """Container for portfolio risk metrics"""
    volatility: float                     # Annualized volatility
    var_95: float                         # 95% Value at Risk
    var_99: float                         # 99% Value at Risk
    cvar_95: float                        # 95% Conditional VaR (Expected Shortfall)
    max_drawdown: float                   # Maximum drawdown
    sharpe_ratio: Optional[float]         # Sharpe ratio if returns provided
    sortino_ratio: Optional[float]        # Sortino ratio
    calmar_ratio: Optional[float]         # Calmar ratio (return/max_dd)
    beta: Optional[float]                 # Market beta if benchmark provided


class RiskModel:
    """
    Risk modeling for portfolio optimization.
    
    Calculates covariance matrices and various risk metrics
    using different estimation approaches.
    """
    
    def __init__(
        self,
        model_type: RiskModelType = RiskModelType.LEDOIT_WOLF,
        halflife: int = 60,  # For EWMA
        annualization_factor: int = 252  # Trading days
    ):
        self.model_type = model_type
        self.halflife = halflife
        self.annualization_factor = annualization_factor
    
    def estimate_covariance(
        self,
        returns: pd.DataFrame,
        model_type: Optional[RiskModelType] = None
    ) -> pd.DataFrame:
        """
        Estimate covariance matrix from returns data.
        
        Args:
            returns: DataFrame of asset returns (assets as columns)
            model_type: Override default model type
            
        Returns:
            Covariance matrix as DataFrame
        """
        model = model_type or self.model_type
        
        if model == RiskModelType.SAMPLE:
            return self._sample_covariance(returns)
        elif model == RiskModelType.EWMA:
            return self._ewma_covariance(returns)
        elif model == RiskModelType.LEDOIT_WOLF:
            return self._ledoit_wolf_covariance(returns)
        elif model == RiskModelType.CONSTANT_CORRELATION:
            return self._constant_correlation_covariance(returns)
        else:
            raise ValueError(f"Unknown model type: {model}")
    
    def _sample_covariance(self, returns: pd.DataFrame) -> pd.DataFrame:
        """Standard sample covariance matrix"""
        return returns.cov() * self.annualization_factor
    
    def _ewma_covariance(self, returns: pd.DataFrame) -> pd.DataFrame:
        """Exponentially weighted covariance matrix"""
        # Calculate decay factor
        alpha = 1 - np.exp(-np.log(2) / self.halflife)
        
        # Initialize
        n_assets = returns.shape[1]
        cov = np.zeros((n_assets, n_assets))
        
        # Calculate EWMA covariance
        returns_np = returns.values
        mean = returns_np.mean(axis=0)
        demeaned = returns_np - mean
        
        weights = np.array([(1 - alpha) ** i for i in range(len(demeaned))])
        weights = weights[::-1]  # Most recent has highest weight
        weights /= weights.sum()
        
        for i in range(n_assets):
            for j in range(i, n_assets):
                cov[i, j] = np.sum(weights * demeaned[:, i] * demeaned[:, j])
                cov[j, i] = cov[i, j]
        
        # Annualize
        cov *= self.annualization_factor
        
        return pd.DataFrame(cov, index=returns.columns, columns=returns.columns)
    
    def _ledoit_wolf_covariance(self, returns: pd.DataFrame) -> pd.DataFrame:
        """
        Ledoit-Wolf shrinkage estimator.
        Shrinks sample covariance toward a structured target (identity scaled).
        """
        returns_np = returns.values
        n, p = returns_np.shape
        
        # Sample covariance
        mean = returns_np.mean(axis=0)
        X = returns_np - mean
        sample_cov = X.T @ X / n
        
        # Compute shrinkage target (scaled identity matrix)
        trace_s = np.trace(sample_cov)
        mu = trace_s / p
        delta = sample_cov - mu * np.eye(p)
        
        # Frobenius norm squared
        delta_2 = (delta ** 2).sum()
        
        # Estimate shrinkage intensity
        X2 = X ** 2
        sum_var = np.sum((X2.T @ X2) / n - sample_cov ** 2)
        
        # Optimal shrinkage
        shrinkage = max(0, min(1, sum_var / delta_2))
        
        # Shrunk covariance
        shrunk_cov = shrinkage * mu * np.eye(p) + (1 - shrinkage) * sample_cov
        
        # Annualize
        shrunk_cov *= self.annualization_factor
        
        return pd.DataFrame(shrunk_cov, index=returns.columns, columns=returns.columns)
    
    def _constant_correlation_covariance(self, returns: pd.DataFrame) -> pd.DataFrame:
        """
        Constant correlation model.
        All pairwise correlations are set to the average correlation.
        """
        # Sample statistics
        sample_cov = returns.cov().values
        vols = np.sqrt(np.diag(sample_cov))
        
        # Correlation matrix
        corr = returns.corr().values
        
        # Average correlation (excluding diagonal)
        n = len(vols)
        avg_corr = (corr.sum() - n) / (n * (n - 1))
        
        # Constant correlation matrix
        const_corr = np.full((n, n), avg_corr)
        np.fill_diagonal(const_corr, 1.0)
        
        # Reconstruct covariance
        vol_matrix = np.outer(vols, vols)
        cov = const_corr * vol_matrix
        
        # Annualize
        cov *= self.annualization_factor
        
        return pd.DataFrame(cov, index=returns.columns, columns=returns.columns)
    
    def calculate_portfolio_risk(
        self,
        weights: np.ndarray,
        returns: pd.DataFrame,
        benchmark_returns: Optional[pd.Series] = None
    ) -> RiskMetrics:
        """
        Calculate comprehensive risk metrics for a portfolio.
        
        Args:
            weights: Portfolio weights
            returns: Historical asset returns
            benchmark_returns: Optional benchmark returns for beta calculation
            
        Returns:
            RiskMetrics dataclass with all metrics
        """
        # Portfolio returns
        portfolio_returns = returns @ weights
        
        # Covariance for volatility
        cov = self.estimate_covariance(returns)
        
        # Annualized volatility
        volatility = np.sqrt(weights @ cov.values @ weights)
        
        # VaR calculations (parametric)
        mean_return = portfolio_returns.mean() * self.annualization_factor
        var_95 = stats.norm.ppf(0.05) * volatility + mean_return
        var_99 = stats.norm.ppf(0.01) * volatility + mean_return
        
        # CVaR (Expected Shortfall) - historical
        sorted_returns = np.sort(portfolio_returns.values)
        n = len(sorted_returns)
        var_95_idx = int(0.05 * n)
        cvar_95 = sorted_returns[:var_95_idx].mean() * self.annualization_factor if var_95_idx > 0 else var_95
        
        # Maximum Drawdown
        cumulative = (1 + portfolio_returns).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # Sharpe Ratio (assuming 0% risk-free rate for simplicity)
        sharpe_ratio = mean_return / volatility if volatility > 0 else 0
        
        # Sortino Ratio
        downside_returns = portfolio_returns[portfolio_returns < 0]
        downside_std = downside_returns.std() * np.sqrt(self.annualization_factor)
        sortino_ratio = mean_return / downside_std if downside_std > 0 else 0
        
        # Calmar Ratio
        calmar_ratio = mean_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        # Beta (if benchmark provided)
        beta = None
        if benchmark_returns is not None:
            aligned = pd.concat([portfolio_returns, benchmark_returns], axis=1).dropna()
            if len(aligned) > 20:
                cov_with_benchmark = aligned.cov().iloc[0, 1]
                benchmark_var = aligned.iloc[:, 1].var()
                beta = cov_with_benchmark / benchmark_var if benchmark_var > 0 else 1.0
        
        return RiskMetrics(
            volatility=volatility,
            var_95=var_95,
            var_99=var_99,
            cvar_95=cvar_95,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            beta=beta
        )
    
    def calculate_correlation_matrix(self, returns: pd.DataFrame) -> pd.DataFrame:
        """Calculate correlation matrix from returns"""
        return returns.corr()
    
    def calculate_expected_returns(
        self,
        returns: pd.DataFrame,
        method: str = "mean"
    ) -> pd.Series:
        """
        Estimate expected returns.
        
        Args:
            returns: Historical returns
            method: 'mean' for historical mean, 'ewma' for exponentially weighted
            
        Returns:
            Expected returns as Series
        """
        if method == "mean":
            return returns.mean() * self.annualization_factor
        elif method == "ewma":
            alpha = 1 - np.exp(-np.log(2) / self.halflife)
            ewma_returns = returns.ewm(alpha=alpha).mean().iloc[-1]
            return ewma_returns * self.annualization_factor
        else:
            raise ValueError(f"Unknown method: {method}")
    
    def risk_contribution(
        self,
        weights: np.ndarray,
        cov: np.ndarray
    ) -> np.ndarray:
        """
        Calculate risk contribution of each asset.
        
        Used for Risk Parity optimization.
        
        Args:
            weights: Portfolio weights
            cov: Covariance matrix
            
        Returns:
            Risk contribution for each asset
        """
        portfolio_vol = np.sqrt(weights @ cov @ weights)
        marginal_risk = cov @ weights / portfolio_vol
        risk_contrib = weights * marginal_risk
        return risk_contrib
    
    def tracking_error(
        self,
        weights: np.ndarray,
        benchmark_weights: np.ndarray,
        cov: np.ndarray
    ) -> float:
        """
        Calculate tracking error vs benchmark.
        
        Args:
            weights: Portfolio weights
            benchmark_weights: Benchmark weights
            cov: Covariance matrix
            
        Returns:
            Annualized tracking error
        """
        diff = weights - benchmark_weights
        tracking_var = diff @ cov @ diff
        return np.sqrt(tracking_var)


def calculate_drawdown_series(returns: pd.Series) -> pd.Series:
    """Calculate drawdown series from returns"""
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    return drawdown


def calculate_rolling_metrics(
    returns: pd.Series,
    window: int = 252
) -> pd.DataFrame:
    """
    Calculate rolling risk metrics.
    
    Args:
        returns: Return series
        window: Rolling window size
        
    Returns:
        DataFrame with rolling volatility, Sharpe, etc.
    """
    rolling = pd.DataFrame(index=returns.index)
    
    # Rolling volatility (annualized)
    rolling['volatility'] = returns.rolling(window).std() * np.sqrt(252)
    
    # Rolling return (annualized)
    rolling['return'] = returns.rolling(window).mean() * 252
    
    # Rolling Sharpe
    rolling['sharpe'] = rolling['return'] / rolling['volatility']
    
    # Rolling max drawdown
    def rolling_max_dd(x):
        cumulative = (1 + x).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        return drawdown.min()
    
    rolling['max_drawdown'] = returns.rolling(window).apply(rolling_max_dd, raw=False)
    
    return rolling
