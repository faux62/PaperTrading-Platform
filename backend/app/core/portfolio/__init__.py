"""
Portfolio Management Module

Core business logic for portfolio management including:
- Risk profiles (Aggressive, Balanced, Prudent)
- Allocation analysis and rebalancing
- Portfolio constraints validation
- Portfolio CRUD service
"""
from app.core.portfolio.risk_profiles import (
    RiskProfile,
    AssetClass,
    Sector,
    AllocationRange,
    PositionLimits,
    RebalancingRules,
    RiskMetrics,
    AGGRESSIVE_PROFILE,
    BALANCED_PROFILE,
    PRUDENT_PROFILE,
    RISK_PROFILES,
    get_risk_profile,
    get_all_profiles,
    get_profile_summary,
)
from app.core.portfolio.constraints import (
    ConstraintsValidator,
    PortfolioSnapshot,
    ValidationResult,
    ConstraintViolation,
    ViolationType,
    Severity,
    validate_buy_order,
    validate_sell_order,
)
from app.core.portfolio.allocation import (
    AssetAllocator,
    AllocationTarget,
    AllocationAnalysis,
    RebalanceRecommendation,
    analyze_portfolio_allocation,
    get_rebalancing_trades,
)
from app.core.portfolio.service import (
    PortfolioService,
    get_portfolio_service,
)

__all__ = [
    # Risk Profiles
    "RiskProfile",
    "AssetClass",
    "Sector",
    "AllocationRange",
    "PositionLimits",
    "RebalancingRules",
    "RiskMetrics",
    "AGGRESSIVE_PROFILE",
    "BALANCED_PROFILE",
    "PRUDENT_PROFILE",
    "RISK_PROFILES",
    "get_risk_profile",
    "get_all_profiles",
    "get_profile_summary",
    # Constraints
    "ConstraintsValidator",
    "PortfolioSnapshot",
    "ValidationResult",
    "ConstraintViolation",
    "ViolationType",
    "Severity",
    "validate_buy_order",
    "validate_sell_order",
    # Allocation
    "AssetAllocator",
    "AllocationTarget",
    "AllocationAnalysis",
    "RebalanceRecommendation",
    "analyze_portfolio_allocation",
    "get_rebalancing_trades",
    # Service
    "PortfolioService",
    "get_portfolio_service",
]
