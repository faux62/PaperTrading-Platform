"""
Unit tests for Portfolio Optimizer Service
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from app.core.optimizer import (
    PortfolioOptimizer,
    OptimizationMethod,
    AssetScreener,
    ScreenerCriteria,
    ProposalGenerator,
    PortfolioProposal
)
from app.core.optimizer.optimizer import OptimizationRequest, OptimizationResponse
from app.core.optimizer.risk_models import (
    RiskModel,
    RiskModelType,
    RiskMetrics,
    calculate_drawdown_series
)
from app.core.optimizer.strategies import (
    MeanVarianceOptimizer,
    RiskParityOptimizer,
    HierarchicalRiskParityOptimizer,
    OptimizationConstraints,
    OptimizationObjective
)
from app.core.optimizer.screener import ScreenerConfig, get_screener_for_risk_profile
from app.core.optimizer.proposal import ProposalType, ProposalStatus


class TestRiskModels:
    """Tests for risk models and metrics"""
    
    @pytest.fixture
    def sample_returns(self):
        """Generate sample returns data"""
        np.random.seed(42)
        n_days = 252
        n_assets = 5
        
        # Generate correlated returns
        means = [0.0003, 0.0005, 0.0002, 0.0004, 0.0001]
        vols = [0.015, 0.02, 0.012, 0.018, 0.025]
        
        returns = np.random.multivariate_normal(
            means,
            np.diag(np.array(vols) ** 2),
            n_days
        )
        
        dates = pd.date_range(end=datetime.now(), periods=n_days, freq='D')
        columns = ['AAPL', 'MSFT', 'JNJ', 'JPM', 'TSLA']
        
        return pd.DataFrame(returns, index=dates, columns=columns)
    
    def test_risk_model_covariance_sample(self, sample_returns):
        """Test sample covariance estimation"""
        risk_model = RiskModel(model_type=RiskModelType.SAMPLE)
        cov = risk_model.estimate_covariance(sample_returns)
        
        assert cov.shape == (5, 5)
        assert np.allclose(cov, cov.T)  # Symmetric
        assert all(np.diag(cov) > 0)  # Positive diagonal
    
    def test_risk_model_covariance_ledoit_wolf(self, sample_returns):
        """Test Ledoit-Wolf shrinkage"""
        risk_model = RiskModel(model_type=RiskModelType.LEDOIT_WOLF)
        cov = risk_model.estimate_covariance(sample_returns)
        
        assert cov.shape == (5, 5)
        assert np.allclose(cov, cov.T)
        # Eigenvalues should all be positive (positive definite)
        eigenvalues = np.linalg.eigvalsh(cov.values)
        assert all(eigenvalues > 0)
    
    def test_risk_model_covariance_ewma(self, sample_returns):
        """Test EWMA covariance"""
        risk_model = RiskModel(model_type=RiskModelType.EWMA, halflife=30)
        cov = risk_model.estimate_covariance(sample_returns)
        
        assert cov.shape == (5, 5)
        assert np.allclose(cov, cov.T)
    
    def test_expected_returns(self, sample_returns):
        """Test expected returns calculation"""
        risk_model = RiskModel()
        
        # Mean method
        exp_ret_mean = risk_model.calculate_expected_returns(sample_returns, method='mean')
        assert len(exp_ret_mean) == 5
        assert all(isinstance(r, (int, float)) for r in exp_ret_mean)
        
        # EWMA method
        exp_ret_ewma = risk_model.calculate_expected_returns(sample_returns, method='ewma')
        assert len(exp_ret_ewma) == 5
    
    def test_portfolio_risk_metrics(self, sample_returns):
        """Test portfolio risk calculation"""
        risk_model = RiskModel()
        
        # Equal weight portfolio
        weights = np.array([0.2, 0.2, 0.2, 0.2, 0.2])
        
        metrics = risk_model.calculate_portfolio_risk(weights, sample_returns)
        
        assert isinstance(metrics, RiskMetrics)
        assert metrics.volatility > 0
        assert metrics.var_95 < 0  # VaR should be negative (loss)
        assert metrics.var_99 < metrics.var_95  # 99% VaR more negative
        assert metrics.max_drawdown <= 0
        assert metrics.sharpe_ratio is not None
    
    def test_risk_contribution(self, sample_returns):
        """Test risk contribution calculation"""
        risk_model = RiskModel()
        cov = risk_model.estimate_covariance(sample_returns).values
        
        weights = np.array([0.2, 0.2, 0.2, 0.2, 0.2])
        risk_contrib = risk_model.risk_contribution(weights, cov)
        
        assert len(risk_contrib) == 5
        assert np.isclose(sum(risk_contrib), np.sqrt(weights @ cov @ weights), rtol=0.01)
    
    def test_drawdown_calculation(self, sample_returns):
        """Test drawdown series calculation"""
        portfolio_returns = sample_returns.mean(axis=1)
        drawdown = calculate_drawdown_series(portfolio_returns)
        
        assert len(drawdown) == len(portfolio_returns)
        assert all(drawdown <= 0)  # Drawdown always negative or zero


class TestOptimizationStrategies:
    """Tests for optimization algorithms"""
    
    @pytest.fixture
    def optimization_inputs(self):
        """Generate inputs for optimization"""
        np.random.seed(42)
        n_assets = 5
        
        # Expected returns (annualized)
        expected_returns = np.array([0.08, 0.12, 0.06, 0.10, 0.15])
        
        # Covariance matrix (annualized)
        vols = np.array([0.15, 0.20, 0.12, 0.18, 0.30])
        corr = np.array([
            [1.0, 0.3, 0.2, 0.4, 0.1],
            [0.3, 1.0, 0.1, 0.5, 0.2],
            [0.2, 0.1, 1.0, 0.3, 0.1],
            [0.4, 0.5, 0.3, 1.0, 0.3],
            [0.1, 0.2, 0.1, 0.3, 1.0]
        ])
        cov = np.outer(vols, vols) * corr
        
        return expected_returns, cov
    
    def test_mean_variance_max_sharpe(self, optimization_inputs):
        """Test Mean-Variance optimizer - Max Sharpe"""
        expected_returns, cov = optimization_inputs
        
        risk_model = RiskModel()
        optimizer = MeanVarianceOptimizer(risk_model, risk_free_rate=0.02)
        
        result = optimizer.optimize(
            expected_returns, cov,
            OptimizationObjective.MAX_SHARPE
        )
        
        assert result.success
        assert np.isclose(sum(result.weights), 1.0, rtol=0.01)
        assert all(result.weights >= -0.01)  # Allow small numerical errors
        assert result.sharpe_ratio > 0
        assert result.expected_return > 0
        assert result.expected_volatility > 0
    
    def test_mean_variance_min_variance(self, optimization_inputs):
        """Test Mean-Variance optimizer - Min Variance"""
        expected_returns, cov = optimization_inputs
        
        risk_model = RiskModel()
        optimizer = MeanVarianceOptimizer(risk_model)
        
        result = optimizer.optimize(
            expected_returns, cov,
            OptimizationObjective.MIN_VARIANCE
        )
        
        assert result.success
        assert np.isclose(sum(result.weights), 1.0, rtol=0.01)
        # Should have more weight in low-volatility assets
        assert result.expected_volatility < 0.20  # Less than average vol
    
    def test_mean_variance_with_constraints(self, optimization_inputs):
        """Test optimization with weight constraints"""
        expected_returns, cov = optimization_inputs
        
        risk_model = RiskModel()
        optimizer = MeanVarianceOptimizer(risk_model)
        
        constraints = OptimizationConstraints(
            min_weight=0.05,
            max_weight=0.30
        )
        
        result = optimizer.optimize(
            expected_returns, cov,
            OptimizationObjective.MAX_SHARPE,
            constraints
        )
        
        assert result.success
        assert all(result.weights >= 0.04)  # Allow small tolerance
        assert all(result.weights <= 0.31)
    
    def test_risk_parity(self, optimization_inputs):
        """Test Risk Parity optimizer"""
        _, cov = optimization_inputs
        
        risk_model = RiskModel()
        optimizer = RiskParityOptimizer(risk_model)
        
        result = optimizer.optimize(cov)
        
        assert result.success
        assert np.isclose(sum(result.weights), 1.0, rtol=0.01)
        
        # Risk contributions should be approximately equal
        risk_contrib = result.risk_contributions
        if risk_contrib is not None:
            risk_contrib_pct = risk_contrib / sum(risk_contrib)
            # All should be close to 20% (1/5)
            assert all(abs(rc - 0.2) < 0.05 for rc in risk_contrib_pct)
    
    def test_hrp(self):
        """Test Hierarchical Risk Parity"""
        np.random.seed(42)
        
        # Generate returns
        n_days = 252
        n_assets = 10
        returns = pd.DataFrame(
            np.random.randn(n_days, n_assets) * 0.02,
            columns=[f'ASSET_{i}' for i in range(n_assets)]
        )
        
        optimizer = HierarchicalRiskParityOptimizer()
        result = optimizer.optimize(returns)
        
        assert result.success
        assert np.isclose(sum(result.weights), 1.0, rtol=0.01)
        assert all(result.weights > 0)  # HRP always produces positive weights
    
    def test_efficient_frontier(self, optimization_inputs):
        """Test efficient frontier generation"""
        expected_returns, cov = optimization_inputs
        
        risk_model = RiskModel()
        optimizer = MeanVarianceOptimizer(risk_model)
        
        frontier = optimizer.efficient_frontier(
            expected_returns, cov, n_points=20
        )
        
        assert len(frontier) > 0
        
        # Frontier should be sorted by return
        returns = [p.expected_return for p in frontier]
        assert returns == sorted(returns) or returns == sorted(returns, reverse=True)


class TestAssetScreener:
    """Tests for asset screener"""
    
    @pytest.mark.asyncio
    async def test_screener_default_universe(self):
        """Test screening with default universe"""
        screener = AssetScreener()
        
        config = ScreenerConfig(top_n=10)
        results = await screener.screen(config)
        
        assert len(results) <= 10
        assert all(hasattr(r, 'symbol') for r in results)
        assert all(hasattr(r, 'total_score') for r in results)
        
        # Should be ranked
        scores = [r.total_score for r in results]
        assert scores == sorted(scores, reverse=True)
    
    @pytest.mark.asyncio
    async def test_screener_with_criteria(self):
        """Test screening with custom criteria"""
        screener = AssetScreener()
        
        config = ScreenerConfig(
            criteria=[
                ScreenerCriteria(
                    criteria_type="momentum",
                    metric='momentum_6m',
                    weight=2.0
                ),
                ScreenerCriteria(
                    criteria_type="volatility",
                    metric='volatility',
                    max_value=0.30,
                    weight=1.0
                )
            ],
            min_market_cap=10e9,
            top_n=15
        )
        
        results = await screener.screen(config)
        
        assert len(results) <= 15
    
    def test_screener_config_for_risk_profiles(self):
        """Test screener configs for different risk profiles"""
        prudent = get_screener_for_risk_profile('prudent', 12)
        balanced = get_screener_for_risk_profile('balanced', 12)
        aggressive = get_screener_for_risk_profile('aggressive', 12)
        
        # Prudent should have higher market cap requirement
        assert prudent.min_market_cap >= balanced.min_market_cap
        
        # Aggressive should allow more positions
        assert aggressive.top_n >= prudent.top_n


class TestProposalGenerator:
    """Tests for proposal generation"""
    
    @pytest.fixture
    def sample_optimization_result(self):
        """Create sample optimization result"""
        from app.core.optimizer.strategies import OptimizationResult
        
        return OptimizationResult(
            weights=np.array([0.25, 0.20, 0.15, 0.25, 0.15]),
            expected_return=0.12,
            expected_volatility=0.15,
            sharpe_ratio=0.80,
            success=True,
            message="Success",
            risk_contributions=np.array([0.05, 0.04, 0.03, 0.05, 0.03]),
            diversification_ratio=1.3
        )
    
    @pytest.fixture
    def sample_assets(self):
        """Create sample asset info"""
        return [
            {'symbol': 'AAPL', 'name': 'Apple Inc.', 'sector': 'Technology', 'price': 175},
            {'symbol': 'MSFT', 'name': 'Microsoft Corp.', 'sector': 'Technology', 'price': 380},
            {'symbol': 'JNJ', 'name': 'Johnson & Johnson', 'sector': 'Healthcare', 'price': 155},
            {'symbol': 'JPM', 'name': 'JPMorgan Chase', 'sector': 'Financials', 'price': 150},
            {'symbol': 'XOM', 'name': 'Exxon Mobil', 'sector': 'Energy', 'price': 100},
        ]
    
    @pytest.fixture
    def sample_returns(self):
        """Generate sample returns"""
        np.random.seed(42)
        dates = pd.date_range(end=datetime.now(), periods=252, freq='D')
        columns = ['AAPL', 'MSFT', 'JNJ', 'JPM', 'XOM']
        returns = np.random.randn(252, 5) * 0.02
        return pd.DataFrame(returns, index=dates, columns=columns)
    
    def test_generate_proposal(self, sample_optimization_result, sample_assets, sample_returns):
        """Test proposal generation"""
        risk_model = RiskModel()
        generator = ProposalGenerator(risk_model)
        
        proposal = generator.generate_proposal(
            portfolio_id="test-portfolio-123",
            optimization_result=sample_optimization_result,
            assets=sample_assets,
            capital=100000,
            returns_data=sample_returns,
            proposal_type=ProposalType.INITIAL,
            methodology="Mean-Variance Optimization"
        )
        
        assert isinstance(proposal, PortfolioProposal)
        assert proposal.portfolio_id == "test-portfolio-123"
        assert proposal.status == ProposalStatus.PENDING
        assert len(proposal.allocations) > 0
        assert proposal.expected_return == pytest.approx(0.12, rel=0.01)
        assert proposal.expected_volatility == pytest.approx(0.15, rel=0.01)
        assert proposal.summary != ""
        assert len(proposal.considerations) > 0
    
    def test_proposal_allocations(self, sample_optimization_result, sample_assets, sample_returns):
        """Test allocation details in proposal"""
        risk_model = RiskModel()
        generator = ProposalGenerator(risk_model)
        
        proposal = generator.generate_proposal(
            portfolio_id="test-portfolio",
            optimization_result=sample_optimization_result,
            assets=sample_assets,
            capital=100000,
            returns_data=sample_returns
        )
        
        # Check allocations
        total_weight = sum(a.weight for a in proposal.allocations)
        assert total_weight <= 1.0
        
        for alloc in proposal.allocations:
            assert alloc.symbol in ['AAPL', 'MSFT', 'JNJ', 'JPM', 'XOM']
            assert alloc.weight > 0
            assert alloc.value > 0
            assert alloc.shares >= 0
    
    def test_proposal_sector_weights(self, sample_optimization_result, sample_assets, sample_returns):
        """Test sector weight calculation"""
        risk_model = RiskModel()
        generator = ProposalGenerator(risk_model)
        
        proposal = generator.generate_proposal(
            portfolio_id="test-portfolio",
            optimization_result=sample_optimization_result,
            assets=sample_assets,
            capital=100000,
            returns_data=sample_returns
        )
        
        assert 'Technology' in proposal.sector_weights
        # AAPL + MSFT = 25% + 20% = 45%
        assert proposal.sector_weights['Technology'] > 0.40
    
    def test_proposal_to_dict(self, sample_optimization_result, sample_assets, sample_returns):
        """Test proposal serialization"""
        risk_model = RiskModel()
        generator = ProposalGenerator(risk_model)
        
        proposal = generator.generate_proposal(
            portfolio_id="test-portfolio",
            optimization_result=sample_optimization_result,
            assets=sample_assets,
            capital=100000,
            returns_data=sample_returns
        )
        
        data = proposal.to_dict()
        
        assert isinstance(data, dict)
        assert 'id' in data
        assert 'allocations' in data
        assert 'expected_return' in data
        assert 'summary' in data


class TestPortfolioOptimizer:
    """Integration tests for main optimizer service"""
    
    @pytest.mark.asyncio
    async def test_full_optimization_workflow(self):
        """Test complete optimization workflow"""
        optimizer = PortfolioOptimizer()
        
        request = OptimizationRequest(
            portfolio_id="test-portfolio-123",
            capital=100000,
            risk_profile="balanced",
            time_horizon_weeks=12,
            min_positions=5,
            max_positions=15
        )
        
        response = await optimizer.optimize(request)
        
        assert isinstance(response, OptimizationResponse)
        assert response.success
        assert response.proposal is not None
        assert len(response.screened_assets) > 0
        assert response.execution_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_optimization_prudent_profile(self):
        """Test optimization for prudent risk profile"""
        optimizer = PortfolioOptimizer()
        
        request = OptimizationRequest(
            portfolio_id="prudent-portfolio",
            capital=50000,
            risk_profile="prudent",
            time_horizon_weeks=26,
            max_weight_per_asset=0.15
        )
        
        response = await optimizer.optimize(request)
        
        assert response.success
        assert response.proposal is not None
        # Prudent should have lower volatility
        assert response.proposal.expected_volatility < 0.20
    
    @pytest.mark.asyncio
    async def test_optimization_aggressive_profile(self):
        """Test optimization for aggressive risk profile"""
        optimizer = PortfolioOptimizer()
        
        request = OptimizationRequest(
            portfolio_id="aggressive-portfolio",
            capital=200000,
            risk_profile="aggressive",
            time_horizon_weeks=4,
            max_weight_per_asset=0.30
        )
        
        response = await optimizer.optimize(request)
        
        assert response.success
        assert response.proposal is not None
        # Aggressive should target higher returns
        assert response.proposal.expected_return > 0
    
    @pytest.mark.asyncio
    async def test_optimization_with_custom_universe(self):
        """Test optimization with specific symbols"""
        optimizer = PortfolioOptimizer()
        
        request = OptimizationRequest(
            portfolio_id="custom-portfolio",
            capital=100000,
            risk_profile="balanced",
            time_horizon_weeks=12,
            universe=['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA']
        )
        
        response = await optimizer.optimize(request)
        
        assert response.success
        # All allocations should be from the specified universe
        if response.proposal:
            for alloc in response.proposal.allocations:
                assert alloc.symbol in request.universe
    
    @pytest.mark.asyncio
    async def test_optimization_specific_method(self):
        """Test optimization with specific method"""
        optimizer = PortfolioOptimizer()
        
        request = OptimizationRequest(
            portfolio_id="hrp-portfolio",
            capital=100000,
            risk_profile="balanced",
            time_horizon_weeks=12,
            method=OptimizationMethod.HRP
        )
        
        response = await optimizer.optimize(request)
        
        assert response.success
        assert "HRP" in response.proposal.methodology or "Hierarchical" in response.proposal.methodology
    
    def test_efficient_frontier_generation(self):
        """Test efficient frontier generation"""
        np.random.seed(42)
        
        # Generate sample returns
        dates = pd.date_range(end=datetime.now(), periods=252, freq='D')
        returns = pd.DataFrame(
            np.random.randn(252, 5) * 0.02,
            index=dates,
            columns=['A', 'B', 'C', 'D', 'E']
        )
        
        optimizer = PortfolioOptimizer()
        frontier = optimizer.get_efficient_frontier(returns, n_points=20)
        
        assert len(frontier) > 0
        for point in frontier:
            assert 'expected_return' in point
            assert 'expected_volatility' in point
            assert 'sharpe_ratio' in point
            assert 'weights' in point


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    @pytest.mark.asyncio
    async def test_insufficient_assets(self):
        """Test handling when not enough assets pass screening"""
        optimizer = PortfolioOptimizer()
        
        request = OptimizationRequest(
            portfolio_id="test",
            capital=100000,
            risk_profile="balanced",
            time_horizon_weeks=12,
            universe=['INVALID1', 'INVALID2'],  # Non-existent symbols
            min_positions=10
        )
        
        response = await optimizer.optimize(request)
        
        # Should handle gracefully
        assert isinstance(response, OptimizationResponse)
    
    def test_zero_weight_filtering(self):
        """Test that near-zero weights are filtered out"""
        from app.core.optimizer.strategies import OptimizationResult
        
        risk_model = RiskModel()
        generator = ProposalGenerator(risk_model)
        
        # Result with some very small weights
        result = OptimizationResult(
            weights=np.array([0.30, 0.0001, 0.25, 0.0005, 0.4499]),
            expected_return=0.10,
            expected_volatility=0.15,
            sharpe_ratio=0.67,
            success=True,
            message="Success"
        )
        
        assets = [
            {'symbol': f'ASSET_{i}', 'name': f'Asset {i}', 'price': 100}
            for i in range(5)
        ]
        
        np.random.seed(42)
        returns = pd.DataFrame(
            np.random.randn(252, 5) * 0.02,
            columns=[a['symbol'] for a in assets]
        )
        
        proposal = generator.generate_proposal(
            portfolio_id="test",
            optimization_result=result,
            assets=assets,
            capital=100000,
            returns_data=returns
        )
        
        # Small weights should be filtered
        assert len(proposal.allocations) == 3  # Only 3 significant weights


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
