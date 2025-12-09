"""
Optimization Strategies for Portfolio Construction

Implements various portfolio optimization approaches:
- Mean-Variance (Markowitz)
- Risk Parity
- Hierarchical Risk Parity (HRP)
- Maximum Diversification
- Minimum Variance
- Black-Litterman
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from scipy.optimize import minimize, LinearConstraint
from scipy.cluster.hierarchy import linkage, leaves_list
from scipy.spatial.distance import squareform
import warnings

from .risk_models import RiskModel, RiskModelType


class OptimizationObjective(str, Enum):
    """Portfolio optimization objectives"""
    MAX_SHARPE = "max_sharpe"
    MIN_VARIANCE = "min_variance"
    MAX_RETURN = "max_return"
    RISK_PARITY = "risk_parity"
    MAX_DIVERSIFICATION = "max_diversification"
    TARGET_RISK = "target_risk"
    TARGET_RETURN = "target_return"


@dataclass
class OptimizationConstraints:
    """Constraints for portfolio optimization"""
    min_weight: float = 0.0              # Minimum weight per asset
    max_weight: float = 1.0              # Maximum weight per asset
    max_total_weight: float = 1.0        # Sum of weights (1.0 = fully invested)
    min_total_weight: float = 1.0        # Minimum total investment
    sector_max: Dict[str, float] = field(default_factory=dict)  # Max per sector
    long_only: bool = True               # No short positions
    max_turnover: Optional[float] = None  # Maximum turnover from current
    current_weights: Optional[np.ndarray] = None  # Current portfolio
    target_volatility: Optional[float] = None  # For target risk optimization
    target_return: Optional[float] = None      # For target return optimization


@dataclass
class OptimizationResult:
    """Result of portfolio optimization"""
    weights: np.ndarray
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    success: bool
    message: str
    risk_contributions: Optional[np.ndarray] = None
    diversification_ratio: Optional[float] = None


class MeanVarianceOptimizer:
    """
    Classical Mean-Variance (Markowitz) Portfolio Optimization.
    
    Finds the optimal portfolio on the efficient frontier.
    """
    
    def __init__(
        self,
        risk_model: RiskModel,
        risk_free_rate: float = 0.0
    ):
        self.risk_model = risk_model
        self.risk_free_rate = risk_free_rate
    
    def optimize(
        self,
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray,
        objective: OptimizationObjective = OptimizationObjective.MAX_SHARPE,
        constraints: Optional[OptimizationConstraints] = None
    ) -> OptimizationResult:
        """
        Optimize portfolio allocation.
        
        Args:
            expected_returns: Expected returns for each asset
            cov_matrix: Covariance matrix
            objective: Optimization objective
            constraints: Portfolio constraints
            
        Returns:
            OptimizationResult with optimal weights
        """
        constraints = constraints or OptimizationConstraints()
        n_assets = len(expected_returns)
        
        # Initial weights
        x0 = np.ones(n_assets) / n_assets
        
        # Bounds
        bounds = [(constraints.min_weight, constraints.max_weight) for _ in range(n_assets)]
        
        # Build constraints list
        opt_constraints = []
        
        # Sum of weights constraint
        opt_constraints.append({
            'type': 'eq',
            'fun': lambda w: np.sum(w) - constraints.max_total_weight
        })
        
        # Turnover constraint if specified
        if constraints.max_turnover is not None and constraints.current_weights is not None:
            opt_constraints.append({
                'type': 'ineq',
                'fun': lambda w: constraints.max_turnover - np.sum(np.abs(w - constraints.current_weights))
            })
        
        # Target volatility constraint
        if objective == OptimizationObjective.TARGET_RISK and constraints.target_volatility is not None:
            opt_constraints.append({
                'type': 'eq',
                'fun': lambda w: np.sqrt(w @ cov_matrix @ w) - constraints.target_volatility
            })
        
        # Target return constraint
        if objective == OptimizationObjective.TARGET_RETURN and constraints.target_return is not None:
            opt_constraints.append({
                'type': 'eq',
                'fun': lambda w: w @ expected_returns - constraints.target_return
            })
        
        # Select objective function
        if objective == OptimizationObjective.MAX_SHARPE:
            def neg_sharpe(w):
                ret = w @ expected_returns
                vol = np.sqrt(w @ cov_matrix @ w)
                if vol < 1e-10:
                    return 1e10
                return -(ret - self.risk_free_rate) / vol
            obj_func = neg_sharpe
            
        elif objective == OptimizationObjective.MIN_VARIANCE:
            def variance(w):
                return w @ cov_matrix @ w
            obj_func = variance
            
        elif objective == OptimizationObjective.MAX_RETURN:
            def neg_return(w):
                return -w @ expected_returns
            obj_func = neg_return
            
        elif objective in [OptimizationObjective.TARGET_RISK, OptimizationObjective.TARGET_RETURN]:
            def neg_sharpe(w):
                ret = w @ expected_returns
                vol = np.sqrt(w @ cov_matrix @ w)
                if vol < 1e-10:
                    return 1e10
                return -(ret - self.risk_free_rate) / vol
            obj_func = neg_sharpe
            
        elif objective == OptimizationObjective.MAX_DIVERSIFICATION:
            def neg_diversification(w):
                weighted_vols = w @ np.sqrt(np.diag(cov_matrix))
                port_vol = np.sqrt(w @ cov_matrix @ w)
                if port_vol < 1e-10:
                    return 1e10
                return -weighted_vols / port_vol
            obj_func = neg_diversification
            
        else:
            raise ValueError(f"Unsupported objective: {objective}")
        
        # Optimize
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = minimize(
                obj_func,
                x0,
                method='SLSQP',
                bounds=bounds,
                constraints=opt_constraints,
                options={'maxiter': 1000, 'ftol': 1e-10}
            )
        
        weights = result.x
        weights = np.clip(weights, constraints.min_weight, constraints.max_weight)
        weights /= weights.sum()  # Normalize to ensure sum = 1
        
        # Calculate metrics
        exp_return = weights @ expected_returns
        exp_vol = np.sqrt(weights @ cov_matrix @ weights)
        sharpe = (exp_return - self.risk_free_rate) / exp_vol if exp_vol > 0 else 0
        
        # Risk contributions
        risk_contrib = self.risk_model.risk_contribution(weights, cov_matrix)
        
        # Diversification ratio
        weighted_vols = np.sum(weights * np.sqrt(np.diag(cov_matrix)))
        div_ratio = weighted_vols / exp_vol if exp_vol > 0 else 1
        
        return OptimizationResult(
            weights=weights,
            expected_return=exp_return,
            expected_volatility=exp_vol,
            sharpe_ratio=sharpe,
            success=result.success,
            message=result.message if not result.success else "Optimization successful",
            risk_contributions=risk_contrib,
            diversification_ratio=div_ratio
        )
    
    def efficient_frontier(
        self,
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray,
        n_points: int = 50,
        constraints: Optional[OptimizationConstraints] = None
    ) -> List[OptimizationResult]:
        """
        Generate the efficient frontier.
        
        Args:
            expected_returns: Expected returns for each asset
            cov_matrix: Covariance matrix
            n_points: Number of points on the frontier
            constraints: Portfolio constraints
            
        Returns:
            List of OptimizationResult on the efficient frontier
        """
        constraints = constraints or OptimizationConstraints()
        
        # Find minimum variance portfolio
        min_var = self.optimize(
            expected_returns, cov_matrix,
            OptimizationObjective.MIN_VARIANCE,
            constraints
        )
        
        # Find maximum return portfolio
        max_ret = self.optimize(
            expected_returns, cov_matrix,
            OptimizationObjective.MAX_RETURN,
            constraints
        )
        
        # Generate target returns
        target_returns = np.linspace(
            min_var.expected_return,
            max_ret.expected_return,
            n_points
        )
        
        frontier = []
        for target in target_returns:
            constr = OptimizationConstraints(
                min_weight=constraints.min_weight,
                max_weight=constraints.max_weight,
                target_return=target
            )
            result = self.optimize(
                expected_returns, cov_matrix,
                OptimizationObjective.TARGET_RETURN,
                constr
            )
            if result.success:
                frontier.append(result)
        
        return frontier


class RiskParityOptimizer:
    """
    Risk Parity Portfolio Optimization.
    
    Equalizes risk contribution from each asset.
    Each asset contributes equally to total portfolio risk.
    """
    
    def __init__(self, risk_model: RiskModel):
        self.risk_model = risk_model
    
    def optimize(
        self,
        cov_matrix: np.ndarray,
        target_risk_contrib: Optional[np.ndarray] = None,
        constraints: Optional[OptimizationConstraints] = None
    ) -> OptimizationResult:
        """
        Optimize for risk parity allocation.
        
        Args:
            cov_matrix: Covariance matrix
            target_risk_contrib: Target risk contributions (equal if None)
            constraints: Portfolio constraints
            
        Returns:
            OptimizationResult with risk parity weights
        """
        constraints = constraints or OptimizationConstraints()
        n_assets = len(cov_matrix)
        
        # Default: equal risk contribution
        if target_risk_contrib is None:
            target_risk_contrib = np.ones(n_assets) / n_assets
        
        # Initial weights
        x0 = np.ones(n_assets) / n_assets
        
        # Bounds
        bounds = [(max(1e-6, constraints.min_weight), constraints.max_weight) 
                  for _ in range(n_assets)]
        
        def risk_parity_objective(w):
            """Minimize squared difference from target risk contributions"""
            port_vol = np.sqrt(w @ cov_matrix @ w)
            if port_vol < 1e-10:
                return 1e10
            
            # Marginal risk contribution
            marginal_contrib = cov_matrix @ w / port_vol
            
            # Risk contribution
            risk_contrib = w * marginal_contrib
            
            # Normalize
            risk_contrib_pct = risk_contrib / risk_contrib.sum()
            
            # SSE from target
            return np.sum((risk_contrib_pct - target_risk_contrib) ** 2)
        
        # Constraint: sum of weights = 1
        opt_constraints = [{
            'type': 'eq',
            'fun': lambda w: np.sum(w) - 1.0
        }]
        
        # Optimize
        result = minimize(
            risk_parity_objective,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=opt_constraints,
            options={'maxiter': 1000, 'ftol': 1e-12}
        )
        
        weights = result.x
        weights = np.clip(weights, constraints.min_weight, constraints.max_weight)
        weights /= weights.sum()
        
        # Calculate metrics
        exp_vol = np.sqrt(weights @ cov_matrix @ weights)
        risk_contrib = self.risk_model.risk_contribution(weights, cov_matrix)
        
        return OptimizationResult(
            weights=weights,
            expected_return=0.0,  # Risk parity doesn't use returns
            expected_volatility=exp_vol,
            sharpe_ratio=0.0,
            success=result.success,
            message=result.message if not result.success else "Risk parity optimization successful",
            risk_contributions=risk_contrib
        )


class HierarchicalRiskParityOptimizer:
    """
    Hierarchical Risk Parity (HRP) Optimization.
    
    Uses hierarchical clustering to build a diversified portfolio
    without requiring return estimates or covariance inversion.
    
    Based on López de Prado's method.
    """
    
    def optimize(
        self,
        returns: pd.DataFrame,
        cov_matrix: Optional[np.ndarray] = None,
        corr_matrix: Optional[np.ndarray] = None
    ) -> OptimizationResult:
        """
        Optimize using Hierarchical Risk Parity.
        
        Args:
            returns: Historical returns DataFrame
            cov_matrix: Optional covariance matrix (calculated if not provided)
            corr_matrix: Optional correlation matrix
            
        Returns:
            OptimizationResult with HRP weights
        """
        # Calculate matrices if not provided
        if cov_matrix is None:
            cov_matrix = returns.cov().values * 252  # Annualize
        if corr_matrix is None:
            corr_matrix = returns.corr().values
        
        # Step 1: Hierarchical clustering
        dist_matrix = self._correlation_distance(corr_matrix)
        link = linkage(squareform(dist_matrix), method='single')
        sort_idx = leaves_list(link)
        
        # Step 2: Quasi-diagonalization
        sorted_corr = corr_matrix[np.ix_(sort_idx, sort_idx)]
        sorted_cov = cov_matrix[np.ix_(sort_idx, sort_idx)]
        
        # Step 3: Recursive bisection
        weights = self._recursive_bisection(sorted_cov, sort_idx)
        
        # Calculate metrics
        exp_vol = np.sqrt(weights @ cov_matrix @ weights)
        
        return OptimizationResult(
            weights=weights,
            expected_return=0.0,
            expected_volatility=exp_vol,
            sharpe_ratio=0.0,
            success=True,
            message="HRP optimization successful"
        )
    
    def _correlation_distance(self, corr: np.ndarray) -> np.ndarray:
        """Convert correlation to distance matrix"""
        return np.sqrt(0.5 * (1 - corr))
    
    def _recursive_bisection(
        self,
        cov: np.ndarray,
        sort_idx: np.ndarray
    ) -> np.ndarray:
        """Recursively bisect and allocate weights"""
        n = len(sort_idx)
        weights = np.ones(n)
        items = [list(range(n))]
        
        while items:
            items = [
                i[j:k]
                for i in items
                for j, k in ((0, len(i) // 2), (len(i) // 2, len(i)))
                if len(i) > 1
            ]
            
            for i in range(0, len(items), 2):
                if i + 1 >= len(items):
                    break
                    
                left = items[i]
                right = items[i + 1]
                
                # Calculate inverse variance weights for each cluster
                var_left = self._cluster_variance(cov, left)
                var_right = self._cluster_variance(cov, right)
                
                alpha = 1 - var_left / (var_left + var_right)
                
                weights[left] *= alpha
                weights[right] *= (1 - alpha)
        
        # Map back to original order
        result = np.zeros(n)
        result[sort_idx] = weights
        
        return result
    
    def _cluster_variance(self, cov: np.ndarray, items: List[int]) -> float:
        """Calculate variance of a cluster using inverse-variance weights"""
        sub_cov = cov[np.ix_(items, items)]
        ivp = 1 / np.diag(sub_cov)
        ivp /= ivp.sum()
        return ivp @ sub_cov @ ivp


class BlackLittermanOptimizer:
    """
    Black-Litterman Model for Portfolio Optimization.
    
    Combines market equilibrium with investor views to generate
    posterior expected returns.
    """
    
    def __init__(
        self,
        risk_model: RiskModel,
        risk_free_rate: float = 0.0,
        tau: float = 0.05  # Scaling factor for prior uncertainty
    ):
        self.risk_model = risk_model
        self.risk_free_rate = risk_free_rate
        self.tau = tau
    
    def optimize(
        self,
        market_caps: np.ndarray,
        cov_matrix: np.ndarray,
        views: Optional[List[Dict]] = None,
        view_confidences: Optional[List[float]] = None,
        risk_aversion: float = 2.5,
        constraints: Optional[OptimizationConstraints] = None
    ) -> OptimizationResult:
        """
        Optimize using Black-Litterman model.
        
        Args:
            market_caps: Market capitalizations for equilibrium weights
            cov_matrix: Covariance matrix
            views: List of views, each with 'assets', 'weights', 'return'
            view_confidences: Confidence in each view (0-1)
            risk_aversion: Market risk aversion parameter
            constraints: Portfolio constraints
            
        Returns:
            OptimizationResult with BL weights
        """
        n_assets = len(market_caps)
        
        # Calculate equilibrium weights (market cap weighted)
        eq_weights = market_caps / market_caps.sum()
        
        # Calculate implied equilibrium returns (reverse optimization)
        pi = risk_aversion * cov_matrix @ eq_weights
        
        # If no views, use equilibrium
        if views is None or len(views) == 0:
            mv_optimizer = MeanVarianceOptimizer(self.risk_model, self.risk_free_rate)
            return mv_optimizer.optimize(
                pi, cov_matrix,
                OptimizationObjective.MAX_SHARPE,
                constraints
            )
        
        # Build view matrices
        n_views = len(views)
        P = np.zeros((n_views, n_assets))
        Q = np.zeros(n_views)
        
        for i, view in enumerate(views):
            for asset_idx, weight in zip(view['assets'], view['weights']):
                P[i, asset_idx] = weight
            Q[i] = view['return']
        
        # View uncertainty (omega)
        if view_confidences is None:
            view_confidences = [0.5] * n_views
        
        omega = np.diag([
            (1 - c) * (P[i] @ (self.tau * cov_matrix) @ P[i].T)
            for i, c in enumerate(view_confidences)
        ])
        
        # Posterior expected returns (BL formula)
        tau_sigma = self.tau * cov_matrix
        tau_sigma_inv = np.linalg.inv(tau_sigma)
        omega_inv = np.linalg.inv(omega)
        
        # Combined precision
        M = tau_sigma_inv + P.T @ omega_inv @ P
        
        # Posterior mean
        posterior_returns = np.linalg.inv(M) @ (
            tau_sigma_inv @ pi + P.T @ omega_inv @ Q
        )
        
        # Optimize with posterior returns
        mv_optimizer = MeanVarianceOptimizer(self.risk_model, self.risk_free_rate)
        return mv_optimizer.optimize(
            posterior_returns, cov_matrix,
            OptimizationObjective.MAX_SHARPE,
            constraints
        )


def get_optimizer_for_risk_profile(
    risk_profile: str,
    risk_model: RiskModel,
    risk_free_rate: float = 0.0
) -> Tuple[type, Dict]:
    """
    Get appropriate optimizer and settings based on risk profile.
    
    Args:
        risk_profile: 'prudent', 'balanced', or 'aggressive'
        risk_model: RiskModel instance
        risk_free_rate: Risk-free rate
        
    Returns:
        Tuple of (optimizer_class, kwargs)
    """
    if risk_profile == "prudent":
        # Conservative: focus on minimum variance
        return MeanVarianceOptimizer, {
            "objective": OptimizationObjective.MIN_VARIANCE,
            "constraints": OptimizationConstraints(
                max_weight=0.15,  # Max 15% per asset
                min_weight=0.0
            )
        }
    elif risk_profile == "aggressive":
        # Aggressive: maximize Sharpe with higher concentration allowed
        return MeanVarianceOptimizer, {
            "objective": OptimizationObjective.MAX_SHARPE,
            "constraints": OptimizationConstraints(
                max_weight=0.30,  # Allow 30% per asset
                min_weight=0.0
            )
        }
    else:  # balanced
        # Balanced: risk parity for diversification
        return RiskParityOptimizer, {
            "constraints": OptimizationConstraints(
                max_weight=0.20,  # Max 20% per asset
                min_weight=0.02  # Min 2% diversification
            )
        }
