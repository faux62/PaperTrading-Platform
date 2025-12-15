"""
Portfolio Optimizer - Main Service

Orchestrates the complete portfolio optimization workflow:
1. Asset screening based on criteria
2. Data fetching and preparation
3. Optimization using selected strategy
4. Proposal generation with rationale

Integrates with:
- Data providers for market data
- ML models for predictions
- Risk models for analysis
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import logging

from .risk_models import RiskModel, RiskModelType, RiskMetrics
from .strategies import (
    MeanVarianceOptimizer,
    RiskParityOptimizer,
    HierarchicalRiskParityOptimizer,
    BlackLittermanOptimizer,
    OptimizationConstraints,
    OptimizationObjective,
    OptimizationResult,
    get_optimizer_for_risk_profile
)
from .screener import (
    AssetScreener,
    ScreenerConfig,
    ScreenedAsset,
    get_screener_for_risk_profile
)
from .proposal import (
    ProposalGenerator,
    PortfolioProposal,
    ProposalType,
    AllocationItem
)


logger = logging.getLogger(__name__)


class OptimizationMethod(str, Enum):
    """Available optimization methods"""
    MEAN_VARIANCE = "mean_variance"        # Classic Markowitz
    MIN_VARIANCE = "min_variance"          # Minimum variance
    MAX_SHARPE = "max_sharpe"              # Maximum Sharpe ratio
    RISK_PARITY = "risk_parity"            # Equal risk contribution
    HRP = "hrp"                            # Hierarchical Risk Parity
    BLACK_LITTERMAN = "black_litterman"    # With investor views


@dataclass
class OptimizationRequest:
    """Request for portfolio optimization"""
    portfolio_id: str
    capital: float
    risk_profile: str  # 'prudent', 'balanced', 'aggressive'
    time_horizon_weeks: int
    
    # Optional overrides
    method: Optional[OptimizationMethod] = None
    universe: Optional[List[str]] = None  # Specific symbols
    sectors: Optional[List[str]] = None  # Allowed sectors
    excluded_symbols: Optional[List[str]] = None
    min_positions: int = 5
    max_positions: int = 30
    max_weight_per_asset: float = 0.20
    min_weight_per_asset: float = 0.02
    
    # Black-Litterman views
    views: Optional[List[Dict]] = None


@dataclass
class OptimizationResponse:
    """Response from optimization"""
    success: bool
    proposal: Optional[PortfolioProposal]
    screened_assets: List[ScreenedAsset]
    optimization_result: Optional[OptimizationResult]
    error: Optional[str] = None
    execution_time_ms: float = 0


class PortfolioOptimizer:
    """
    Main portfolio optimization service.
    
    Coordinates asset screening, optimization, and proposal generation
    based on portfolio parameters and market conditions.
    """
    
    def __init__(
        self,
        data_provider: Any = None,
        ml_service: Any = None,
        risk_free_rate: float = 0.05  # 5% risk-free rate
    ):
        """
        Initialize the portfolio optimizer.
        
        Args:
            data_provider: Service for fetching market data
            ml_service: Optional ML service for predictions
            risk_free_rate: Risk-free rate for calculations
        """
        self.data_provider = data_provider
        self.ml_service = ml_service
        self.risk_free_rate = risk_free_rate
        
        # Initialize components
        self.risk_model = RiskModel(
            model_type=RiskModelType.LEDOIT_WOLF,
            halflife=60
        )
        self.screener = AssetScreener(data_provider)
        self.proposal_generator = ProposalGenerator(self.risk_model)
        
        # Cache for optimization data
        self._returns_cache: Dict[str, pd.DataFrame] = {}
    
    async def optimize(
        self,
        request: OptimizationRequest
    ) -> OptimizationResponse:
        """
        Execute full portfolio optimization workflow.
        
        Args:
            request: OptimizationRequest with parameters
            
        Returns:
            OptimizationResponse with proposal
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting optimization for portfolio {request.portfolio_id}")
            
            # Step 1: Screen assets
            screened = await self._screen_assets(request)
            if len(screened) < request.min_positions:
                return OptimizationResponse(
                    success=False,
                    proposal=None,
                    screened_assets=screened,
                    optimization_result=None,
                    error=f"Only {len(screened)} assets passed screening, "
                          f"minimum {request.min_positions} required"
                )
            
            logger.info(f"Screened {len(screened)} assets")
            
            # Step 2: Fetch historical data
            symbols = [a.symbol for a in screened[:request.max_positions]]
            returns_data = await self._fetch_returns(
                symbols, 
                lookback_days=request.time_horizon_weeks * 7 * 2  # 2x horizon
            )
            
            if returns_data.empty:
                return OptimizationResponse(
                    success=False,
                    proposal=None,
                    screened_assets=screened,
                    optimization_result=None,
                    error="Failed to fetch historical data"
                )
            
            # Step 3: Run optimization
            opt_result = await self._run_optimization(
                request, returns_data, screened
            )
            
            if not opt_result.success:
                return OptimizationResponse(
                    success=False,
                    proposal=None,
                    screened_assets=screened,
                    optimization_result=opt_result,
                    error=f"Optimization failed: {opt_result.message}"
                )
            
            logger.info(f"Optimization complete: Sharpe={opt_result.sharpe_ratio:.2f}")
            
            # Step 4: Generate proposal
            assets = self._prepare_asset_info(screened, returns_data)
            proposal = self.proposal_generator.generate_proposal(
                portfolio_id=request.portfolio_id,
                optimization_result=opt_result,
                assets=assets,
                capital=request.capital,
                returns_data=returns_data,
                proposal_type=ProposalType.INITIAL,
                methodology=self._get_methodology_description(request)
            )
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return OptimizationResponse(
                success=True,
                proposal=proposal,
                screened_assets=screened,
                optimization_result=opt_result,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            logger.exception(f"Optimization failed: {e}")
            return OptimizationResponse(
                success=False,
                proposal=None,
                screened_assets=[],
                optimization_result=None,
                error=str(e)
            )
    
    async def _screen_assets(
        self,
        request: OptimizationRequest
    ) -> List[ScreenedAsset]:
        """Screen assets based on request parameters"""
        # Get base config for risk profile
        config = get_screener_for_risk_profile(
            request.risk_profile,
            request.time_horizon_weeks
        )
        
        # Apply request overrides
        if request.universe:
            config.universe = request.universe
        if request.sectors:
            config.sectors = request.sectors
        if request.max_positions:
            config.top_n = request.max_positions
        
        # Run screening
        screened = await self.screener.screen(config)
        
        # Filter excluded symbols
        if request.excluded_symbols:
            excluded = set(request.excluded_symbols)
            screened = [a for a in screened if a.symbol not in excluded]
        
        return screened
    
    async def _fetch_returns(
        self,
        symbols: List[str],
        lookback_days: int = 252
    ) -> pd.DataFrame:
        """Fetch historical returns for symbols - REAL DATA ONLY"""
        cache_key = f"{','.join(sorted(symbols))}_{lookback_days}"
        
        if cache_key in self._returns_cache:
            return self._returns_cache[cache_key]
        
        if self.data_provider is None:
            raise ValueError("No data provider configured - cannot fetch returns")
        
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days)
            
            prices = await self.data_provider.get_historical_prices_batch(
                symbols, start_date, end_date
            )
            
            if prices.empty:
                raise ValueError(f"No price data returned for symbols: {symbols}")
            
            returns = prices.pct_change().dropna()
            
            if returns.empty:
                raise ValueError("Insufficient data to calculate returns")
            
            self._returns_cache[cache_key] = returns
            return returns
            
        except Exception as e:
            logger.error(f"Failed to fetch returns: {e}")
            raise ValueError(f"Failed to fetch historical data: {e}")
    
    async def _run_optimization(
        self,
        request: OptimizationRequest,
        returns: pd.DataFrame,
        screened: List[ScreenedAsset]
    ) -> OptimizationResult:
        """Run the appropriate optimization algorithm"""
        # Select method based on risk profile or explicit request
        method = request.method or self._select_method(request.risk_profile)
        
        # Calculate inputs
        cov_matrix = self.risk_model.estimate_covariance(returns).values
        expected_returns = self.risk_model.calculate_expected_returns(returns).values
        
        # Apply ML predictions if available
        if self.ml_service:
            try:
                ml_returns = await self._get_ml_predictions(
                    returns.columns.tolist(),
                    request.time_horizon_weeks
                )
                # Blend historical with ML predictions
                expected_returns = 0.7 * expected_returns + 0.3 * ml_returns
            except Exception as e:
                logger.warning(f"ML predictions failed: {e}")
        
        # Build constraints
        constraints = OptimizationConstraints(
            min_weight=request.min_weight_per_asset,
            max_weight=request.max_weight_per_asset,
            long_only=True
        )
        
        # Target volatility based on risk profile
        target_vol = {
            'prudent': 0.10,
            'balanced': 0.15,
            'aggressive': 0.22
        }.get(request.risk_profile, 0.15)
        
        # Run optimizer
        if method == OptimizationMethod.MEAN_VARIANCE:
            optimizer = MeanVarianceOptimizer(self.risk_model, self.risk_free_rate)
            result = optimizer.optimize(
                expected_returns, cov_matrix,
                OptimizationObjective.MAX_SHARPE,
                constraints
            )
            
        elif method == OptimizationMethod.MIN_VARIANCE:
            optimizer = MeanVarianceOptimizer(self.risk_model, self.risk_free_rate)
            result = optimizer.optimize(
                expected_returns, cov_matrix,
                OptimizationObjective.MIN_VARIANCE,
                constraints
            )
            
        elif method == OptimizationMethod.RISK_PARITY:
            optimizer = RiskParityOptimizer(self.risk_model)
            result = optimizer.optimize(cov_matrix, constraints=constraints)
            # Add expected return to result
            result.expected_return = float(result.weights @ expected_returns)
            
        elif method == OptimizationMethod.HRP:
            optimizer = HierarchicalRiskParityOptimizer()
            result = optimizer.optimize(returns, cov_matrix)
            result.expected_return = float(result.weights @ expected_returns)
            result.sharpe_ratio = (
                result.expected_return / result.expected_volatility
                if result.expected_volatility > 0 else 0
            )
            
        elif method == OptimizationMethod.BLACK_LITTERMAN:
            # Get market caps from screened assets
            market_caps = np.array([
                a.market_cap or 1e9 for a in screened[:len(returns.columns)]
            ])
            
            optimizer = BlackLittermanOptimizer(
                self.risk_model, self.risk_free_rate
            )
            result = optimizer.optimize(
                market_caps, cov_matrix,
                views=request.views,
                constraints=constraints
            )
            
        else:
            # Default to max Sharpe
            optimizer = MeanVarianceOptimizer(self.risk_model, self.risk_free_rate)
            result = optimizer.optimize(
                expected_returns, cov_matrix,
                OptimizationObjective.MAX_SHARPE,
                constraints
            )
        
        return result
    
    def _select_method(self, risk_profile: str) -> OptimizationMethod:
        """Select optimization method based on risk profile"""
        if risk_profile == "prudent":
            return OptimizationMethod.MIN_VARIANCE
        elif risk_profile == "aggressive":
            return OptimizationMethod.MAX_SHARPE
        else:  # balanced
            return OptimizationMethod.RISK_PARITY
    
    async def _get_ml_predictions(
        self,
        symbols: List[str],
        horizon_weeks: int
    ) -> np.ndarray:
        """Get ML model predictions for expected returns"""
        if self.ml_service is None:
            raise ValueError("ML service not configured")
        
        predictions = await self.ml_service.predict_returns(
            symbols, horizon_days=horizon_weeks * 7
        )
        
        # Annualize predictions
        return np.array(predictions) * (52 / horizon_weeks)
    
    def _prepare_asset_info(
        self,
        screened: List[ScreenedAsset],
        returns: pd.DataFrame
    ) -> List[Dict]:
        """Prepare asset info for proposal generation"""
        assets = []
        for asset in screened:
            if asset.symbol in returns.columns:
                assets.append({
                    'symbol': asset.symbol,
                    'name': asset.name,
                    'sector': asset.sector,
                    'industry': asset.industry,
                    'market_cap': asset.market_cap,
                    'total_score': asset.total_score,
                    'metrics': asset.metrics,
                    'price': asset.metrics.get('price', 100)
                })
        return assets
    
    def _get_methodology_description(self, request: OptimizationRequest) -> str:
        """Generate methodology description"""
        method = request.method or self._select_method(request.risk_profile)
        
        descriptions = {
            OptimizationMethod.MEAN_VARIANCE: "Mean-Variance (Markowitz) optimization",
            OptimizationMethod.MIN_VARIANCE: "Minimum Variance optimization",
            OptimizationMethod.MAX_SHARPE: "Maximum Sharpe Ratio optimization",
            OptimizationMethod.RISK_PARITY: "Risk Parity optimization",
            OptimizationMethod.HRP: "Hierarchical Risk Parity (HRP)",
            OptimizationMethod.BLACK_LITTERMAN: "Black-Litterman with views"
        }
        
        base = descriptions.get(method, "Portfolio optimization")
        return f"{base} for {request.risk_profile} risk profile, {request.time_horizon_weeks}-week horizon"
    
    async def generate_rebalance_proposal(
        self,
        portfolio_id: str,
        current_positions: List[Dict],
        target_weights: Optional[np.ndarray] = None,
        rebalance_threshold: float = 0.05
    ) -> Optional[PortfolioProposal]:
        """
        Check if rebalancing is needed and generate proposal.
        
        Args:
            portfolio_id: Portfolio ID
            current_positions: Current holdings
            target_weights: Target weights (or recalculate)
            rebalance_threshold: Minimum drift to trigger rebalancing
            
        Returns:
            PortfolioProposal if rebalancing needed
        """
        if not current_positions:
            return None
        
        symbols = [p['symbol'] for p in current_positions]
        capital = sum(p.get('value', 0) for p in current_positions)
        
        # Fetch returns
        returns = await self._fetch_returns(symbols)
        
        # If no target provided, calculate new optimal
        if target_weights is None:
            cov = self.risk_model.estimate_covariance(returns).values
            optimizer = RiskParityOptimizer(self.risk_model)
            result = optimizer.optimize(cov)
            target_weights = result.weights
        
        # Prepare asset info
        assets = [{'symbol': s, 'name': s} for s in symbols]
        
        return self.proposal_generator.generate_rebalance_proposal(
            portfolio_id=portfolio_id,
            current_positions=current_positions,
            target_weights=target_weights,
            assets=assets,
            capital=capital,
            returns_data=returns,
            rebalance_threshold=rebalance_threshold
        )
    
    def get_efficient_frontier(
        self,
        returns: pd.DataFrame,
        n_points: int = 50,
        constraints: Optional[OptimizationConstraints] = None
    ) -> List[Dict]:
        """
        Generate efficient frontier points.
        
        Args:
            returns: Historical returns
            n_points: Number of frontier points
            constraints: Portfolio constraints
            
        Returns:
            List of points with return, volatility, weights
        """
        cov = self.risk_model.estimate_covariance(returns).values
        expected_returns = self.risk_model.calculate_expected_returns(returns).values
        
        optimizer = MeanVarianceOptimizer(self.risk_model, self.risk_free_rate)
        frontier = optimizer.efficient_frontier(
            expected_returns, cov, n_points, constraints
        )
        
        return [
            {
                'expected_return': r.expected_return,
                'expected_volatility': r.expected_volatility,
                'sharpe_ratio': r.sharpe_ratio,
                'weights': r.weights.tolist()
            }
            for r in frontier
        ]


# Export convenience function
async def optimize_portfolio(
    portfolio_id: str,
    capital: float,
    risk_profile: str,
    time_horizon_weeks: int,
    data_provider: Any = None,
    **kwargs
) -> OptimizationResponse:
    """
    Convenience function to run portfolio optimization.
    
    Args:
        portfolio_id: Portfolio ID
        capital: Investment capital
        risk_profile: 'prudent', 'balanced', or 'aggressive'
        time_horizon_weeks: Investment horizon
        data_provider: Optional data provider
        **kwargs: Additional optimization parameters
        
    Returns:
        OptimizationResponse with proposal
    """
    optimizer = PortfolioOptimizer(data_provider)
    
    request = OptimizationRequest(
        portfolio_id=portfolio_id,
        capital=capital,
        risk_profile=risk_profile,
        time_horizon_weeks=time_horizon_weeks,
        **kwargs
    )
    
    return await optimizer.optimize(request)
