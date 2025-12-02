"""
Portfolio Optimizer

Mean-Variance Optimization and portfolio construction:
- Markowitz efficient frontier
- Black-Litterman model
- Risk parity
- Maximum Sharpe ratio
"""
import numpy as np
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from scipy.optimize import minimize
from loguru import logger


class OptimizationObjective(str, Enum):
    """Portfolio optimization objective."""
    MAX_SHARPE = "max_sharpe"
    MIN_VOLATILITY = "min_volatility"
    MAX_RETURN = "max_return"
    RISK_PARITY = "risk_parity"
    TARGET_RETURN = "target_return"
    TARGET_VOLATILITY = "target_volatility"


@dataclass
class PortfolioConstraints:
    """Constraints for portfolio optimization."""
    min_weight: float = 0.0  # Minimum weight per asset
    max_weight: float = 1.0  # Maximum weight per asset
    max_sector_weight: float = 0.4  # Maximum weight per sector
    min_assets: int = 3  # Minimum number of assets
    max_assets: int = 20  # Maximum number of assets
    long_only: bool = True  # No short selling
    target_return: Optional[float] = None
    target_volatility: Optional[float] = None
    sector_constraints: Dict[str, float] = field(default_factory=dict)


@dataclass
class OptimizedPortfolio:
    """Result of portfolio optimization."""
    weights: Dict[str, float]
    expected_return: float
    volatility: float
    sharpe_ratio: float
    objective: OptimizationObjective
    risk_contribution: Dict[str, float] = field(default_factory=dict)
    efficient_frontier: Optional[List[Dict[str, float]]] = None
    optimization_status: str = "success"
    optimization_message: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            'weights': self.weights,
            'expected_return': self.expected_return,
            'volatility': self.volatility,
            'sharpe_ratio': self.sharpe_ratio,
            'objective': self.objective.value,
            'risk_contribution': self.risk_contribution,
            'efficient_frontier': self.efficient_frontier,
            'optimization_status': self.optimization_status,
            'optimization_message': self.optimization_message,
            'timestamp': self.timestamp.isoformat()
        }


class PortfolioOptimizer:
    """
    Mean-Variance Portfolio Optimizer.
    
    Features:
    - Multiple optimization objectives
    - Constraints handling
    - Efficient frontier calculation
    - Risk parity
    - Black-Litterman views integration
    """
    
    def __init__(
        self,
        risk_free_rate: float = 0.02,
        trading_days: int = 252
    ):
        self.risk_free_rate = risk_free_rate
        self.trading_days = trading_days
    
    def optimize(
        self,
        returns: np.ndarray,
        symbols: List[str],
        objective: OptimizationObjective = OptimizationObjective.MAX_SHARPE,
        constraints: Optional[PortfolioConstraints] = None,
        expected_returns: Optional[np.ndarray] = None,
        cov_matrix: Optional[np.ndarray] = None
    ) -> OptimizedPortfolio:
        """
        Optimize portfolio weights.
        
        Args:
            returns: Historical returns matrix (n_periods x n_assets)
            symbols: Asset symbols
            objective: Optimization objective
            constraints: Portfolio constraints
            expected_returns: Optional custom expected returns
            cov_matrix: Optional custom covariance matrix
            
        Returns:
            OptimizedPortfolio with optimal weights
        """
        constraints = constraints or PortfolioConstraints()
        n_assets = len(symbols)
        
        # Calculate statistics if not provided
        if expected_returns is None:
            expected_returns = np.mean(returns, axis=0) * self.trading_days
        
        if cov_matrix is None:
            cov_matrix = np.cov(returns.T) * self.trading_days
        
        # Initial weights (equal weight)
        init_weights = np.array([1.0 / n_assets] * n_assets)
        
        # Set up bounds
        if constraints.long_only:
            bounds = tuple((constraints.min_weight, constraints.max_weight) for _ in range(n_assets))
        else:
            bounds = tuple((-constraints.max_weight, constraints.max_weight) for _ in range(n_assets))
        
        # Constraint: weights sum to 1
        eq_constraint = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
        constraint_list = [eq_constraint]
        
        # Add target return constraint if specified
        if objective == OptimizationObjective.TARGET_RETURN and constraints.target_return:
            target_ret_constraint = {
                'type': 'eq',
                'fun': lambda w: np.dot(w, expected_returns) - constraints.target_return
            }
            constraint_list.append(target_ret_constraint)
        
        # Add target volatility constraint if specified
        if objective == OptimizationObjective.TARGET_VOLATILITY and constraints.target_volatility:
            target_vol_constraint = {
                'type': 'eq',
                'fun': lambda w: np.sqrt(np.dot(w.T, np.dot(cov_matrix, w))) - constraints.target_volatility
            }
            constraint_list.append(target_vol_constraint)
        
        # Define objective function
        if objective == OptimizationObjective.MAX_SHARPE:
            def objective_func(weights):
                ret = np.dot(weights, expected_returns)
                vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
                return -(ret - self.risk_free_rate) / vol if vol > 0 else 0
        
        elif objective == OptimizationObjective.MIN_VOLATILITY:
            def objective_func(weights):
                return np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        
        elif objective == OptimizationObjective.MAX_RETURN:
            def objective_func(weights):
                return -np.dot(weights, expected_returns)
        
        elif objective == OptimizationObjective.RISK_PARITY:
            def objective_func(weights):
                # Risk parity: equal risk contribution from each asset
                port_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
                marginal_contrib = np.dot(cov_matrix, weights)
                risk_contrib = weights * marginal_contrib / port_vol
                target_risk = port_vol / n_assets
                return np.sum((risk_contrib - target_risk) ** 2)
        
        else:  # TARGET_RETURN or TARGET_VOLATILITY with min vol/max ret
            def objective_func(weights):
                return np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        
        # Run optimization
        try:
            result = minimize(
                objective_func,
                init_weights,
                method='SLSQP',
                bounds=bounds,
                constraints=constraint_list,
                options={'maxiter': 1000, 'ftol': 1e-9}
            )
            
            if not result.success:
                logger.warning(f"Optimization did not converge: {result.message}")
            
            optimal_weights = result.x
            status = "success" if result.success else "warning"
            message = result.message
            
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            optimal_weights = init_weights
            status = "failed"
            message = str(e)
        
        # Clean up small weights
        optimal_weights = np.where(np.abs(optimal_weights) < 1e-6, 0, optimal_weights)
        optimal_weights = optimal_weights / np.sum(optimal_weights)  # Re-normalize
        
        # Calculate portfolio metrics
        port_return = np.dot(optimal_weights, expected_returns)
        port_vol = np.sqrt(np.dot(optimal_weights.T, np.dot(cov_matrix, optimal_weights)))
        sharpe = (port_return - self.risk_free_rate) / port_vol if port_vol > 0 else 0
        
        # Calculate risk contributions
        marginal_contrib = np.dot(cov_matrix, optimal_weights)
        risk_contrib = optimal_weights * marginal_contrib / port_vol if port_vol > 0 else np.zeros(n_assets)
        
        # Create weights dictionary
        weights_dict = {sym: float(w) for sym, w in zip(symbols, optimal_weights) if abs(w) > 1e-6}
        risk_contrib_dict = {sym: float(rc) for sym, rc in zip(symbols, risk_contrib) if abs(optimal_weights[symbols.index(sym)]) > 1e-6}
        
        return OptimizedPortfolio(
            weights=weights_dict,
            expected_return=float(port_return),
            volatility=float(port_vol),
            sharpe_ratio=float(sharpe),
            objective=objective,
            risk_contribution=risk_contrib_dict,
            optimization_status=status,
            optimization_message=message
        )
    
    def calculate_efficient_frontier(
        self,
        returns: np.ndarray,
        symbols: List[str],
        n_portfolios: int = 50,
        constraints: Optional[PortfolioConstraints] = None
    ) -> List[Dict[str, Any]]:
        """
        Calculate the efficient frontier.
        
        Args:
            returns: Historical returns
            symbols: Asset symbols
            n_portfolios: Number of portfolios to calculate
            constraints: Portfolio constraints
            
        Returns:
            List of portfolios on the efficient frontier
        """
        constraints = constraints or PortfolioConstraints()
        
        # Calculate return range
        expected_returns = np.mean(returns, axis=0) * self.trading_days
        min_ret = np.min(expected_returns)
        max_ret = np.max(expected_returns)
        
        # Get minimum volatility portfolio
        min_vol_portfolio = self.optimize(
            returns, symbols,
            OptimizationObjective.MIN_VOLATILITY,
            constraints
        )
        min_frontier_ret = min_vol_portfolio.expected_return
        
        # Generate target returns
        target_returns = np.linspace(min_frontier_ret, max_ret * 0.95, n_portfolios)
        
        frontier = []
        for target_ret in target_returns:
            constraints_copy = PortfolioConstraints(
                min_weight=constraints.min_weight,
                max_weight=constraints.max_weight,
                long_only=constraints.long_only,
                target_return=target_ret
            )
            
            try:
                portfolio = self.optimize(
                    returns, symbols,
                    OptimizationObjective.TARGET_RETURN,
                    constraints_copy
                )
                
                frontier.append({
                    'return': portfolio.expected_return,
                    'volatility': portfolio.volatility,
                    'sharpe': portfolio.sharpe_ratio,
                    'weights': portfolio.weights
                })
            except Exception:
                continue
        
        return frontier
    
    def black_litterman(
        self,
        returns: np.ndarray,
        symbols: List[str],
        market_cap_weights: Dict[str, float],
        views: Dict[str, float],
        view_confidence: Dict[str, float],
        tau: float = 0.05
    ) -> OptimizedPortfolio:
        """
        Black-Litterman model with investor views.
        
        Args:
            returns: Historical returns
            symbols: Asset symbols
            market_cap_weights: Market cap weights
            views: Investor views (symbol -> expected return)
            view_confidence: Confidence in views
            tau: Scaling factor
            
        Returns:
            Optimized portfolio incorporating views
        """
        n_assets = len(symbols)
        
        # Covariance matrix
        cov_matrix = np.cov(returns.T) * self.trading_days
        
        # Market cap weights vector
        w_mkt = np.array([market_cap_weights.get(s, 1/n_assets) for s in symbols])
        w_mkt = w_mkt / np.sum(w_mkt)  # Normalize
        
        # Implied equilibrium returns
        risk_aversion = (np.mean(returns) - self.risk_free_rate / self.trading_days) / np.var(returns)
        pi = risk_aversion * np.dot(cov_matrix, w_mkt)
        
        # Build views matrix
        P = []
        Q = []
        omega_diag = []
        
        for sym, view_ret in views.items():
            if sym in symbols:
                idx = symbols.index(sym)
                p_row = np.zeros(n_assets)
                p_row[idx] = 1
                P.append(p_row)
                Q.append(view_ret)
                # View uncertainty
                confidence = view_confidence.get(sym, 0.5)
                omega_diag.append((1 - confidence) * cov_matrix[idx, idx])
        
        if not P:
            # No views, use equilibrium returns
            return self.optimize(returns, symbols, OptimizationObjective.MAX_SHARPE)
        
        P = np.array(P)
        Q = np.array(Q)
        omega = np.diag(omega_diag)
        
        # Black-Litterman posterior
        tau_cov = tau * cov_matrix
        
        # Posterior expected returns
        inv_tau_cov = np.linalg.inv(tau_cov)
        inv_omega = np.linalg.inv(omega) if len(omega) > 0 else np.zeros_like(P.T @ P)
        
        posterior_cov = np.linalg.inv(inv_tau_cov + P.T @ inv_omega @ P)
        posterior_returns = posterior_cov @ (inv_tau_cov @ pi + P.T @ inv_omega @ Q)
        
        # Optimize with posterior returns
        return self.optimize(
            returns, symbols,
            OptimizationObjective.MAX_SHARPE,
            expected_returns=posterior_returns,
            cov_matrix=cov_matrix
        )
    
    def rebalance_portfolio(
        self,
        current_weights: Dict[str, float],
        target_weights: Dict[str, float],
        current_prices: Dict[str, float],
        portfolio_value: float,
        min_trade_value: float = 100.0
    ) -> Dict[str, Dict[str, Any]]:
        """
        Calculate rebalancing trades.
        
        Args:
            current_weights: Current portfolio weights
            target_weights: Target portfolio weights
            current_prices: Current asset prices
            portfolio_value: Total portfolio value
            min_trade_value: Minimum trade value
            
        Returns:
            Dictionary of trades needed
        """
        trades = {}
        
        all_symbols = set(current_weights.keys()) | set(target_weights.keys())
        
        for symbol in all_symbols:
            current_w = current_weights.get(symbol, 0)
            target_w = target_weights.get(symbol, 0)
            
            weight_diff = target_w - current_w
            value_diff = weight_diff * portfolio_value
            
            price = current_prices.get(symbol, 0)
            if price > 0 and abs(value_diff) >= min_trade_value:
                shares = int(value_diff / price)
                
                if shares != 0:
                    trades[symbol] = {
                        'action': 'BUY' if shares > 0 else 'SELL',
                        'shares': abs(shares),
                        'value': abs(shares * price),
                        'current_weight': current_w,
                        'target_weight': target_w,
                        'weight_change': weight_diff
                    }
        
        return trades


class RiskParityOptimizer:
    """
    Risk Parity Portfolio Optimizer.
    
    Allocates such that each asset contributes equally to portfolio risk.
    """
    
    def __init__(self):
        pass
    
    def optimize(
        self,
        returns: np.ndarray,
        symbols: List[str],
        risk_budgets: Optional[Dict[str, float]] = None
    ) -> OptimizedPortfolio:
        """
        Optimize for risk parity.
        
        Args:
            returns: Historical returns
            symbols: Asset symbols
            risk_budgets: Optional custom risk budgets per asset
            
        Returns:
            Risk parity portfolio
        """
        n_assets = len(symbols)
        cov_matrix = np.cov(returns.T) * 252
        
        # Default: equal risk budget
        if risk_budgets:
            budgets = np.array([risk_budgets.get(s, 1/n_assets) for s in symbols])
            budgets = budgets / np.sum(budgets)
        else:
            budgets = np.ones(n_assets) / n_assets
        
        def risk_parity_objective(weights):
            weights = np.maximum(weights, 1e-10)
            port_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            marginal_contrib = np.dot(cov_matrix, weights)
            risk_contrib = weights * marginal_contrib / port_vol
            target_risk = budgets * port_vol
            return np.sum((risk_contrib - target_risk) ** 2)
        
        # Constraints
        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]
        bounds = tuple((0.01, 1.0) for _ in range(n_assets))
        init_weights = np.array([1.0 / n_assets] * n_assets)
        
        result = minimize(
            risk_parity_objective,
            init_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        
        optimal_weights = result.x
        optimal_weights = optimal_weights / np.sum(optimal_weights)
        
        # Calculate metrics
        expected_returns = np.mean(returns, axis=0) * 252
        port_return = np.dot(optimal_weights, expected_returns)
        port_vol = np.sqrt(np.dot(optimal_weights.T, np.dot(cov_matrix, optimal_weights)))
        sharpe = (port_return - 0.02) / port_vol if port_vol > 0 else 0
        
        # Risk contributions
        marginal = np.dot(cov_matrix, optimal_weights)
        risk_contrib = optimal_weights * marginal / port_vol
        
        weights_dict = {sym: float(w) for sym, w in zip(symbols, optimal_weights)}
        risk_dict = {sym: float(rc) for sym, rc in zip(symbols, risk_contrib)}
        
        return OptimizedPortfolio(
            weights=weights_dict,
            expected_return=float(port_return),
            volatility=float(port_vol),
            sharpe_ratio=float(sharpe),
            objective=OptimizationObjective.RISK_PARITY,
            risk_contribution=risk_dict,
            optimization_status="success" if result.success else "warning",
            optimization_message=result.message
        )
