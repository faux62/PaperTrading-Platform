"""
Portfolio Optimizer Module

Provides intelligent portfolio composition recommendations based on:
- Market data (current and historical)
- Technical indicators
- Fundamental analysis
- ML-based predictions
- Risk profile and time horizon

Main components:
- PortfolioOptimizer: Core optimization algorithms
- AssetScreener: Universe filtering and ranking
- ProposalGenerator: Creates actionable portfolio proposals
"""

from .optimizer import PortfolioOptimizer, OptimizationMethod
from .screener import AssetScreener, ScreenerCriteria
from .proposal import ProposalGenerator, PortfolioProposal

__all__ = [
    "PortfolioOptimizer",
    "OptimizationMethod", 
    "AssetScreener",
    "ScreenerCriteria",
    "ProposalGenerator",
    "PortfolioProposal",
]
