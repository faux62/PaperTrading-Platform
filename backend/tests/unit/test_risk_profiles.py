"""
Unit Tests - Risk Profiles
Tests for risk profile configurations and constraints.
"""
import pytest
from decimal import Decimal

from app.core.portfolio.risk_profiles import (
    AssetClass,
    Sector,
    AllocationRange,
    PositionLimits,
    RebalancingRules,
    RiskMetrics,
    RiskProfile,
    AGGRESSIVE_PROFILE,
    # BALANCED_PROFILE,
    # PRUDENT_PROFILE
)


class TestAssetClassEnum:
    """Tests for AssetClass enum."""
    
    def test_asset_class_values(self):
        """AssetClass should have expected values."""
        assert AssetClass.EQUITY_US.value == "equity_us"
        assert AssetClass.EQUITY_EU.value == "equity_eu"
        assert AssetClass.EQUITY_ASIA.value == "equity_asia"
        assert AssetClass.FIXED_INCOME.value == "fixed_income"
        assert AssetClass.COMMODITIES.value == "commodities"
        assert AssetClass.CRYPTO.value == "crypto"
        assert AssetClass.CASH.value == "cash"
    
    def test_asset_class_is_string_enum(self):
        """AssetClass should be string enum."""
        assert issubclass(AssetClass, str)


class TestSectorEnum:
    """Tests for Sector enum."""
    
    def test_sector_gics_values(self):
        """Sector should have GICS sector values."""
        assert Sector.TECHNOLOGY.value == "technology"
        assert Sector.HEALTHCARE.value == "healthcare"
        assert Sector.FINANCIALS.value == "financials"
        assert Sector.ENERGY.value == "energy"
        assert Sector.UTILITIES.value == "utilities"
        assert Sector.REAL_ESTATE.value == "real_estate"
    
    def test_sector_count(self):
        """Should have 11 GICS sectors."""
        sectors = list(Sector)
        assert len(sectors) == 11


class TestAllocationRange:
    """Tests for AllocationRange dataclass."""
    
    def test_allocation_range_defaults(self):
        """AllocationRange should have sensible defaults."""
        ar = AllocationRange()
        assert ar.min_weight == Decimal("0")
        assert ar.max_weight == Decimal("100")
    
    def test_allocation_range_target_weight_auto(self):
        """Target weight should auto-calculate as midpoint."""
        ar = AllocationRange(
            min_weight=Decimal("20"),
            max_weight=Decimal("40")
        )
        assert ar.target_weight == Decimal("30")
    
    def test_allocation_range_explicit_target(self):
        """Explicit target weight should override auto-calculation."""
        ar = AllocationRange(
            min_weight=Decimal("20"),
            max_weight=Decimal("40"),
            target_weight=Decimal("25")
        )
        assert ar.target_weight == Decimal("25")
    
    def test_allocation_range_validation_logic(self):
        """Min should be less than max conceptually."""
        ar = AllocationRange(
            min_weight=Decimal("10"),
            max_weight=Decimal("30")
        )
        assert ar.min_weight < ar.max_weight


class TestPositionLimits:
    """Tests for PositionLimits dataclass."""
    
    def test_position_limits_defaults(self):
        """PositionLimits should have sensible defaults."""
        pl = PositionLimits()
        assert pl.max_position_size_percent == Decimal("10")
        assert pl.min_position_size_percent == Decimal("1")
        assert pl.max_sector_exposure == Decimal("30")
        assert pl.min_positions == 10
        assert pl.max_positions == 50
    
    def test_position_limits_custom(self):
        """Custom position limits should work."""
        pl = PositionLimits(
            max_position_size_percent=Decimal("5"),
            min_positions=20,
            max_positions=100
        )
        assert pl.max_position_size_percent == Decimal("5")
        assert pl.min_positions == 20
        assert pl.max_positions == 100
    
    def test_position_limits_max_value(self):
        """Max position value should be optional."""
        pl = PositionLimits()
        assert pl.max_position_value is None
        
        pl_with_max = PositionLimits(max_position_value=Decimal("50000"))
        assert pl_with_max.max_position_value == Decimal("50000")


class TestRebalancingRules:
    """Tests for RebalancingRules dataclass."""
    
    def test_rebalancing_rules_defaults(self):
        """RebalancingRules should have sensible defaults."""
        rr = RebalancingRules()
        assert rr.drift_threshold_percent == Decimal("5")
        assert rr.time_based_days == 90
        assert rr.min_trade_value == Decimal("100")
        assert rr.tax_loss_harvesting is False
        assert rr.immediate_rebalance_drift == Decimal("15")
    
    def test_rebalancing_rules_custom(self):
        """Custom rebalancing rules should work."""
        rr = RebalancingRules(
            drift_threshold_percent=Decimal("3"),
            time_based_days=30,
            tax_loss_harvesting=True
        )
        assert rr.drift_threshold_percent == Decimal("3")
        assert rr.time_based_days == 30
        assert rr.tax_loss_harvesting is True


class TestRiskMetricsDataclass:
    """Tests for RiskMetrics dataclass."""
    
    def test_risk_metrics_defaults(self):
        """RiskMetrics should have sensible defaults."""
        rm = RiskMetrics()
        assert rm.max_portfolio_volatility == Decimal("20")
        assert rm.target_portfolio_volatility == Decimal("15")
        assert rm.max_drawdown_percent == Decimal("20")
        assert rm.target_beta == Decimal("1.0")
        assert rm.max_beta == Decimal("1.5")
        assert rm.var_confidence == Decimal("95")
        assert rm.max_var_percent == Decimal("5")
    
    def test_risk_metrics_stop_loss_optional(self):
        """Stop loss should be optional."""
        rm = RiskMetrics()
        assert rm.stop_loss_percent is None
        
        rm_with_stop = RiskMetrics(stop_loss_percent=Decimal("8"))
        assert rm_with_stop.stop_loss_percent == Decimal("8")


class TestRiskProfile:
    """Tests for RiskProfile dataclass."""
    
    def test_risk_profile_creation(self):
        """RiskProfile should be creatable with basic fields."""
        profile = RiskProfile(
            name="Test Profile",
            description="A test risk profile"
        )
        assert profile.name == "Test Profile"
        assert profile.description == "A test risk profile"
    
    def test_risk_profile_defaults(self):
        """RiskProfile should have default nested objects."""
        profile = RiskProfile(name="Test", description="Test")
        assert isinstance(profile.position_limits, PositionLimits)
        assert isinstance(profile.rebalancing_rules, RebalancingRules)
        assert isinstance(profile.risk_metrics, RiskMetrics)
    
    def test_risk_profile_trading_options(self):
        """Trading options should default to disabled."""
        profile = RiskProfile(name="Test", description="Test")
        assert profile.allow_margin is False
        assert profile.allow_short_selling is False
        assert profile.allow_options is False
        assert profile.allow_futures is False


class TestAggressiveProfile:
    """Tests for AGGRESSIVE_PROFILE preset."""
    
    def test_aggressive_profile_name(self):
        """Aggressive profile should have correct name."""
        assert AGGRESSIVE_PROFILE.name == "Aggressive"
    
    def test_aggressive_profile_description(self):
        """Aggressive profile should have description."""
        assert "growth" in AGGRESSIVE_PROFILE.description.lower()
        assert "risk" in AGGRESSIVE_PROFILE.description.lower()
    
    def test_aggressive_profile_equity_allocation(self):
        """Aggressive profile should have high equity allocation."""
        us_equity = AGGRESSIVE_PROFILE.asset_allocation.get(AssetClass.EQUITY_US)
        assert us_equity is not None
        assert us_equity.max_weight >= Decimal("50")
