"""
Risk Profiles Configuration

Defines the three risk profiles (Aggressive, Balanced, Prudent)
with their allocation constraints, position limits, and rebalancing rules.
"""
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional
from enum import Enum


class AssetClass(str, Enum):
    """Asset class categories."""
    EQUITY_US = "equity_us"
    EQUITY_EU = "equity_eu"
    EQUITY_ASIA = "equity_asia"
    EQUITY_EMERGING = "equity_emerging"
    FIXED_INCOME = "fixed_income"
    COMMODITIES = "commodities"
    CRYPTO = "crypto"
    CASH = "cash"
    OTHER = "other"


class Sector(str, Enum):
    """Stock sectors (GICS)."""
    TECHNOLOGY = "technology"
    HEALTHCARE = "healthcare"
    FINANCIALS = "financials"
    CONSUMER_DISCRETIONARY = "consumer_discretionary"
    CONSUMER_STAPLES = "consumer_staples"
    INDUSTRIALS = "industrials"
    ENERGY = "energy"
    UTILITIES = "utilities"
    MATERIALS = "materials"
    REAL_ESTATE = "real_estate"
    COMMUNICATION = "communication"


@dataclass
class AllocationRange:
    """Min/max allocation range for an asset class or sector."""
    min_weight: Decimal = Decimal("0")
    max_weight: Decimal = Decimal("100")
    target_weight: Optional[Decimal] = None
    
    def __post_init__(self):
        if self.target_weight is None:
            self.target_weight = (self.min_weight + self.max_weight) / 2


@dataclass
class PositionLimits:
    """Position size and concentration limits."""
    # Single position limits
    max_position_size_percent: Decimal = Decimal("10")  # Max % of portfolio in one stock
    min_position_size_percent: Decimal = Decimal("1")   # Min % to avoid tiny positions
    max_position_value: Optional[Decimal] = None        # Absolute max value
    
    # Concentration limits
    max_sector_exposure: Decimal = Decimal("30")        # Max % in one sector
    max_country_exposure: Decimal = Decimal("50")       # Max % in one country
    max_market_cap_small: Decimal = Decimal("20")       # Max % in small caps
    
    # Diversification
    min_positions: int = 10                              # Minimum number of positions
    max_positions: int = 50                              # Maximum number of positions


@dataclass
class RebalancingRules:
    """Rules for portfolio rebalancing."""
    # Trigger thresholds
    drift_threshold_percent: Decimal = Decimal("5")     # Rebalance if drift > threshold
    time_based_days: int = 90                           # Rebalance every N days
    
    # Execution
    min_trade_value: Decimal = Decimal("100")           # Min trade size
    tax_loss_harvesting: bool = False                   # Enable tax-loss harvesting
    
    # Urgency
    immediate_rebalance_drift: Decimal = Decimal("15")  # Immediate if drift > this


@dataclass
class RiskMetrics:
    """Risk parameters for the profile."""
    # Volatility
    max_portfolio_volatility: Decimal = Decimal("20")   # Max annual volatility %
    target_portfolio_volatility: Decimal = Decimal("15")
    
    # Drawdown
    max_drawdown_percent: Decimal = Decimal("20")       # Max acceptable drawdown
    stop_loss_percent: Optional[Decimal] = None         # Position stop loss
    
    # Beta
    target_beta: Decimal = Decimal("1.0")               # Target market beta
    max_beta: Decimal = Decimal("1.5")
    
    # Value at Risk (VaR)
    var_confidence: Decimal = Decimal("95")             # VaR confidence level
    max_var_percent: Decimal = Decimal("5")             # Max daily VaR


@dataclass
class RiskProfile:
    """
    Complete risk profile configuration.
    
    Defines all constraints and parameters for a portfolio
    based on the investor's risk tolerance.
    """
    name: str
    description: str
    
    # Asset allocation
    asset_allocation: dict[AssetClass, AllocationRange] = field(default_factory=dict)
    sector_allocation: dict[Sector, AllocationRange] = field(default_factory=dict)
    
    # Limits
    position_limits: PositionLimits = field(default_factory=PositionLimits)
    
    # Rebalancing
    rebalancing_rules: RebalancingRules = field(default_factory=RebalancingRules)
    
    # Risk
    risk_metrics: RiskMetrics = field(default_factory=RiskMetrics)
    
    # Additional settings
    allow_margin: bool = False
    allow_short_selling: bool = False
    allow_options: bool = False
    allow_futures: bool = False


# ==================== Predefined Profiles ====================

AGGRESSIVE_PROFILE = RiskProfile(
    name="Aggressive",
    description="High growth focus with higher volatility tolerance. Suitable for long-term investors with high risk appetite.",
    
    asset_allocation={
        AssetClass.EQUITY_US: AllocationRange(
            min_weight=Decimal("40"),
            max_weight=Decimal("70"),
            target_weight=Decimal("55"),
        ),
        AssetClass.EQUITY_EU: AllocationRange(
            min_weight=Decimal("10"),
            max_weight=Decimal("25"),
            target_weight=Decimal("15"),
        ),
        AssetClass.EQUITY_ASIA: AllocationRange(
            min_weight=Decimal("10"),
            max_weight=Decimal("25"),
            target_weight=Decimal("15"),
        ),
        AssetClass.EQUITY_EMERGING: AllocationRange(
            min_weight=Decimal("5"),
            max_weight=Decimal("15"),
            target_weight=Decimal("10"),
        ),
        AssetClass.FIXED_INCOME: AllocationRange(
            min_weight=Decimal("0"),
            max_weight=Decimal("10"),
            target_weight=Decimal("0"),
        ),
        AssetClass.COMMODITIES: AllocationRange(
            min_weight=Decimal("0"),
            max_weight=Decimal("10"),
            target_weight=Decimal("5"),
        ),
        AssetClass.CASH: AllocationRange(
            min_weight=Decimal("0"),
            max_weight=Decimal("10"),
            target_weight=Decimal("0"),
        ),
    },
    
    sector_allocation={
        Sector.TECHNOLOGY: AllocationRange(
            min_weight=Decimal("15"),
            max_weight=Decimal("40"),
            target_weight=Decimal("30"),
        ),
        Sector.HEALTHCARE: AllocationRange(
            min_weight=Decimal("5"),
            max_weight=Decimal("20"),
            target_weight=Decimal("12"),
        ),
        Sector.FINANCIALS: AllocationRange(
            min_weight=Decimal("5"),
            max_weight=Decimal("20"),
            target_weight=Decimal("10"),
        ),
        Sector.CONSUMER_DISCRETIONARY: AllocationRange(
            min_weight=Decimal("5"),
            max_weight=Decimal("20"),
            target_weight=Decimal("12"),
        ),
    },
    
    position_limits=PositionLimits(
        max_position_size_percent=Decimal("15"),
        min_position_size_percent=Decimal("2"),
        max_sector_exposure=Decimal("40"),
        max_country_exposure=Decimal("70"),
        max_market_cap_small=Decimal("30"),
        min_positions=8,
        max_positions=30,
    ),
    
    rebalancing_rules=RebalancingRules(
        drift_threshold_percent=Decimal("10"),
        time_based_days=180,
        min_trade_value=Decimal("500"),
        immediate_rebalance_drift=Decimal("20"),
    ),
    
    risk_metrics=RiskMetrics(
        max_portfolio_volatility=Decimal("30"),
        target_portfolio_volatility=Decimal("22"),
        max_drawdown_percent=Decimal("35"),
        stop_loss_percent=Decimal("25"),
        target_beta=Decimal("1.2"),
        max_beta=Decimal("1.8"),
        max_var_percent=Decimal("8"),
    ),
    
    allow_margin=False,
    allow_short_selling=False,
    allow_options=False,
)


BALANCED_PROFILE = RiskProfile(
    name="Balanced",
    description="Mix of growth and stability. Suitable for medium-term investors with moderate risk tolerance.",
    
    asset_allocation={
        AssetClass.EQUITY_US: AllocationRange(
            min_weight=Decimal("30"),
            max_weight=Decimal("50"),
            target_weight=Decimal("40"),
        ),
        AssetClass.EQUITY_EU: AllocationRange(
            min_weight=Decimal("10"),
            max_weight=Decimal("20"),
            target_weight=Decimal("15"),
        ),
        AssetClass.EQUITY_ASIA: AllocationRange(
            min_weight=Decimal("5"),
            max_weight=Decimal("15"),
            target_weight=Decimal("10"),
        ),
        AssetClass.EQUITY_EMERGING: AllocationRange(
            min_weight=Decimal("0"),
            max_weight=Decimal("10"),
            target_weight=Decimal("5"),
        ),
        AssetClass.FIXED_INCOME: AllocationRange(
            min_weight=Decimal("15"),
            max_weight=Decimal("30"),
            target_weight=Decimal("20"),
        ),
        AssetClass.COMMODITIES: AllocationRange(
            min_weight=Decimal("0"),
            max_weight=Decimal("10"),
            target_weight=Decimal("5"),
        ),
        AssetClass.CASH: AllocationRange(
            min_weight=Decimal("2"),
            max_weight=Decimal("15"),
            target_weight=Decimal("5"),
        ),
    },
    
    sector_allocation={
        Sector.TECHNOLOGY: AllocationRange(
            min_weight=Decimal("10"),
            max_weight=Decimal("25"),
            target_weight=Decimal("20"),
        ),
        Sector.HEALTHCARE: AllocationRange(
            min_weight=Decimal("8"),
            max_weight=Decimal("18"),
            target_weight=Decimal("12"),
        ),
        Sector.FINANCIALS: AllocationRange(
            min_weight=Decimal("8"),
            max_weight=Decimal("18"),
            target_weight=Decimal("12"),
        ),
        Sector.CONSUMER_STAPLES: AllocationRange(
            min_weight=Decimal("5"),
            max_weight=Decimal("15"),
            target_weight=Decimal("10"),
        ),
        Sector.UTILITIES: AllocationRange(
            min_weight=Decimal("3"),
            max_weight=Decimal("12"),
            target_weight=Decimal("8"),
        ),
    },
    
    position_limits=PositionLimits(
        max_position_size_percent=Decimal("10"),
        min_position_size_percent=Decimal("1"),
        max_sector_exposure=Decimal("30"),
        max_country_exposure=Decimal("55"),
        max_market_cap_small=Decimal("15"),
        min_positions=15,
        max_positions=40,
    ),
    
    rebalancing_rules=RebalancingRules(
        drift_threshold_percent=Decimal("5"),
        time_based_days=90,
        min_trade_value=Decimal("200"),
        immediate_rebalance_drift=Decimal("15"),
    ),
    
    risk_metrics=RiskMetrics(
        max_portfolio_volatility=Decimal("18"),
        target_portfolio_volatility=Decimal("12"),
        max_drawdown_percent=Decimal("20"),
        stop_loss_percent=Decimal("15"),
        target_beta=Decimal("0.9"),
        max_beta=Decimal("1.2"),
        max_var_percent=Decimal("4"),
    ),
    
    allow_margin=False,
    allow_short_selling=False,
    allow_options=False,
)


PRUDENT_PROFILE = RiskProfile(
    name="Prudent",
    description="Capital preservation with steady income. Suitable for conservative investors or those nearing retirement.",
    
    asset_allocation={
        AssetClass.EQUITY_US: AllocationRange(
            min_weight=Decimal("15"),
            max_weight=Decimal("35"),
            target_weight=Decimal("25"),
        ),
        AssetClass.EQUITY_EU: AllocationRange(
            min_weight=Decimal("5"),
            max_weight=Decimal("15"),
            target_weight=Decimal("10"),
        ),
        AssetClass.EQUITY_ASIA: AllocationRange(
            min_weight=Decimal("0"),
            max_weight=Decimal("10"),
            target_weight=Decimal("5"),
        ),
        AssetClass.EQUITY_EMERGING: AllocationRange(
            min_weight=Decimal("0"),
            max_weight=Decimal("5"),
            target_weight=Decimal("0"),
        ),
        AssetClass.FIXED_INCOME: AllocationRange(
            min_weight=Decimal("35"),
            max_weight=Decimal("55"),
            target_weight=Decimal("45"),
        ),
        AssetClass.COMMODITIES: AllocationRange(
            min_weight=Decimal("0"),
            max_weight=Decimal("5"),
            target_weight=Decimal("0"),
        ),
        AssetClass.CASH: AllocationRange(
            min_weight=Decimal("10"),
            max_weight=Decimal("25"),
            target_weight=Decimal("15"),
        ),
    },
    
    sector_allocation={
        Sector.CONSUMER_STAPLES: AllocationRange(
            min_weight=Decimal("10"),
            max_weight=Decimal("25"),
            target_weight=Decimal("18"),
        ),
        Sector.HEALTHCARE: AllocationRange(
            min_weight=Decimal("10"),
            max_weight=Decimal("22"),
            target_weight=Decimal("15"),
        ),
        Sector.UTILITIES: AllocationRange(
            min_weight=Decimal("10"),
            max_weight=Decimal("22"),
            target_weight=Decimal("15"),
        ),
        Sector.FINANCIALS: AllocationRange(
            min_weight=Decimal("5"),
            max_weight=Decimal("15"),
            target_weight=Decimal("10"),
        ),
        Sector.TECHNOLOGY: AllocationRange(
            min_weight=Decimal("5"),
            max_weight=Decimal("15"),
            target_weight=Decimal("10"),
        ),
    },
    
    position_limits=PositionLimits(
        max_position_size_percent=Decimal("7"),
        min_position_size_percent=Decimal("1"),
        max_sector_exposure=Decimal("25"),
        max_country_exposure=Decimal("45"),
        max_market_cap_small=Decimal("5"),
        min_positions=20,
        max_positions=50,
    ),
    
    rebalancing_rules=RebalancingRules(
        drift_threshold_percent=Decimal("3"),
        time_based_days=60,
        min_trade_value=Decimal("100"),
        tax_loss_harvesting=True,
        immediate_rebalance_drift=Decimal("10"),
    ),
    
    risk_metrics=RiskMetrics(
        max_portfolio_volatility=Decimal("10"),
        target_portfolio_volatility=Decimal("7"),
        max_drawdown_percent=Decimal("12"),
        stop_loss_percent=Decimal("10"),
        target_beta=Decimal("0.6"),
        max_beta=Decimal("0.9"),
        max_var_percent=Decimal("2"),
    ),
    
    allow_margin=False,
    allow_short_selling=False,
    allow_options=False,
)


# ==================== Profile Registry ====================

RISK_PROFILES: dict[str, RiskProfile] = {
    "aggressive": AGGRESSIVE_PROFILE,
    "balanced": BALANCED_PROFILE,
    "prudent": PRUDENT_PROFILE,
}


def get_risk_profile(profile_name: str) -> RiskProfile:
    """
    Get a risk profile by name.
    
    Args:
        profile_name: One of 'aggressive', 'balanced', 'prudent'
        
    Returns:
        The corresponding RiskProfile configuration
        
    Raises:
        ValueError: If profile name is not recognized
    """
    profile_name = profile_name.lower()
    if profile_name not in RISK_PROFILES:
        raise ValueError(
            f"Unknown risk profile: {profile_name}. "
            f"Valid profiles: {list(RISK_PROFILES.keys())}"
        )
    return RISK_PROFILES[profile_name]


def get_all_profiles() -> dict[str, RiskProfile]:
    """Get all available risk profiles."""
    return RISK_PROFILES.copy()


def get_profile_summary(profile_name: str) -> dict:
    """
    Get a summary of a risk profile for UI display.
    
    Returns dict with key metrics suitable for displaying
    in a profile selection interface.
    """
    profile = get_risk_profile(profile_name)
    
    # Calculate total equity allocation
    equity_classes = [
        AssetClass.EQUITY_US,
        AssetClass.EQUITY_EU,
        AssetClass.EQUITY_ASIA,
        AssetClass.EQUITY_EMERGING,
    ]
    total_equity_target = sum(
        profile.asset_allocation.get(ac, AllocationRange()).target_weight or Decimal("0")
        for ac in equity_classes
    )
    
    fixed_income = profile.asset_allocation.get(
        AssetClass.FIXED_INCOME, AllocationRange()
    ).target_weight or Decimal("0")
    
    return {
        "name": profile.name,
        "description": profile.description,
        "equity_allocation": float(total_equity_target),
        "fixed_income_allocation": float(fixed_income),
        "cash_allocation": float(
            profile.asset_allocation.get(AssetClass.CASH, AllocationRange()).target_weight or Decimal("0")
        ),
        "max_volatility": float(profile.risk_metrics.max_portfolio_volatility),
        "max_drawdown": float(profile.risk_metrics.max_drawdown_percent),
        "max_position_size": float(profile.position_limits.max_position_size_percent),
        "min_positions": profile.position_limits.min_positions,
        "max_positions": profile.position_limits.max_positions,
        "rebalance_frequency_days": profile.rebalancing_rules.time_based_days,
    }
