"""
Asset Allocation Logic

Calculates target allocations, rebalancing recommendations,
and allocation drift for portfolios based on risk profiles.
"""
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Any
from datetime import datetime
from loguru import logger

from app.core.portfolio.risk_profiles import (
    RiskProfile,
    AssetClass,
    Sector,
    AllocationRange,
    get_risk_profile,
)


@dataclass
class AllocationTarget:
    """Target allocation for an asset/sector."""
    name: str
    target_weight: Decimal
    current_weight: Decimal
    drift: Decimal  # current - target
    drift_percent: Decimal  # drift / target * 100
    
    @property
    def is_overweight(self) -> bool:
        return self.drift > 0
    
    @property
    def is_underweight(self) -> bool:
        return self.drift < 0
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "target_weight": float(self.target_weight),
            "current_weight": float(self.current_weight),
            "drift": float(self.drift),
            "drift_percent": float(self.drift_percent),
            "status": "overweight" if self.is_overweight else "underweight" if self.is_underweight else "on_target",
        }


@dataclass
class RebalanceRecommendation:
    """Recommendation for rebalancing a position."""
    symbol: str
    action: str  # 'buy', 'sell', 'hold'
    current_value: Decimal
    target_value: Decimal
    trade_value: Decimal  # Amount to buy (positive) or sell (negative)
    current_weight: Decimal
    target_weight: Decimal
    reason: str
    priority: int = 1  # 1=high, 2=medium, 3=low
    
    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "action": self.action,
            "current_value": float(self.current_value),
            "target_value": float(self.target_value),
            "trade_value": float(self.trade_value),
            "current_weight": float(self.current_weight),
            "target_weight": float(self.target_weight),
            "reason": self.reason,
            "priority": self.priority,
        }


@dataclass
class AllocationAnalysis:
    """Complete allocation analysis for a portfolio."""
    total_value: Decimal
    cash_balance: Decimal
    asset_class_allocations: list[AllocationTarget]
    sector_allocations: list[AllocationTarget]
    needs_rebalancing: bool
    max_drift: Decimal
    rebalance_recommendations: list[RebalanceRecommendation]
    analysis_date: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "total_value": float(self.total_value),
            "cash_balance": float(self.cash_balance),
            "asset_class_allocations": [a.to_dict() for a in self.asset_class_allocations],
            "sector_allocations": [s.to_dict() for s in self.sector_allocations],
            "needs_rebalancing": self.needs_rebalancing,
            "max_drift": float(self.max_drift),
            "rebalance_recommendations": [r.to_dict() for r in self.rebalance_recommendations],
            "analysis_date": self.analysis_date.isoformat(),
        }


class AssetAllocator:
    """
    Asset allocation calculator and rebalancing engine.
    
    Analyzes portfolio allocation vs target allocation defined
    by the risk profile and generates rebalancing recommendations.
    
    Usage:
        allocator = AssetAllocator(risk_profile="balanced")
        
        # Analyze current allocation
        analysis = allocator.analyze_allocation(
            total_value=Decimal("100000"),
            cash_balance=Decimal("10000"),
            positions=[...],
        )
        
        if analysis.needs_rebalancing:
            for rec in analysis.rebalance_recommendations:
                print(f"{rec.action.upper()} {rec.symbol}: ${rec.trade_value:.2f}")
    """
    
    def __init__(self, risk_profile: RiskProfile | str):
        if isinstance(risk_profile, str):
            self.profile = get_risk_profile(risk_profile)
        else:
            self.profile = risk_profile
    
    def analyze_allocation(
        self,
        total_value: Decimal,
        cash_balance: Decimal,
        positions: list[dict],
    ) -> AllocationAnalysis:
        """
        Analyze current portfolio allocation vs target.
        
        Args:
            total_value: Total portfolio value (positions + cash)
            cash_balance: Current cash balance
            positions: List of position dicts with keys:
                - symbol: Stock symbol
                - market_value: Current market value
                - sector: Stock sector (optional)
                - asset_class: Asset class (optional)
                - country: Country (optional)
                
        Returns:
            AllocationAnalysis with drift metrics and recommendations
        """
        if total_value == 0:
            return self._empty_analysis()
        
        # Calculate current allocations
        asset_class_current = self._calculate_asset_class_allocation(
            total_value, cash_balance, positions
        )
        sector_current = self._calculate_sector_allocation(
            total_value, positions
        )
        
        # Calculate drift vs targets
        asset_allocations = self._calculate_drift(
            asset_class_current,
            self.profile.asset_allocation,
        )
        sector_allocations = self._calculate_sector_drift(
            sector_current,
            self.profile.sector_allocation,
        )
        
        # Determine if rebalancing is needed
        max_drift = max(
            [abs(a.drift) for a in asset_allocations] + 
            [abs(s.drift) for s in sector_allocations],
            default=Decimal("0")
        )
        
        needs_rebalancing = max_drift > self.profile.rebalancing_rules.drift_threshold_percent
        
        # Generate recommendations if needed
        recommendations = []
        if needs_rebalancing:
            recommendations = self._generate_recommendations(
                total_value, cash_balance, positions,
                asset_allocations, sector_allocations,
            )
        
        return AllocationAnalysis(
            total_value=total_value,
            cash_balance=cash_balance,
            asset_class_allocations=asset_allocations,
            sector_allocations=sector_allocations,
            needs_rebalancing=needs_rebalancing,
            max_drift=max_drift,
            rebalance_recommendations=recommendations,
        )
    
    def calculate_target_allocation(
        self,
        total_value: Decimal,
    ) -> dict[str, Decimal]:
        """
        Calculate target dollar amounts for each asset class.
        
        Returns dict mapping asset class to target value.
        """
        targets = {}
        for asset_class, allocation in self.profile.asset_allocation.items():
            target_weight = allocation.target_weight or Decimal("0")
            target_value = (total_value * target_weight / 100).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            targets[asset_class.value] = target_value
        return targets
    
    def get_optimal_position_size(
        self,
        total_value: Decimal,
        symbol: str,
        current_price: Decimal,
        sector: Optional[str] = None,
    ) -> dict:
        """
        Calculate optimal position size for a new position.
        
        Returns recommended quantity and value based on
        position limits and diversification rules.
        """
        limits = self.profile.position_limits
        
        # Start with target position size (between min and max)
        target_percent = (limits.min_position_size_percent + limits.max_position_size_percent) / 2
        target_value = (total_value * target_percent / 100).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        
        # Calculate quantity
        if current_price > 0:
            quantity = (target_value / current_price).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
            actual_value = quantity * current_price
        else:
            quantity = Decimal("0")
            actual_value = Decimal("0")
        
        return {
            "symbol": symbol,
            "recommended_quantity": int(quantity),
            "recommended_value": float(actual_value),
            "target_weight_percent": float(target_percent),
            "min_weight_percent": float(limits.min_position_size_percent),
            "max_weight_percent": float(limits.max_position_size_percent),
        }
    
    def _calculate_asset_class_allocation(
        self,
        total_value: Decimal,
        cash_balance: Decimal,
        positions: list[dict],
    ) -> dict[AssetClass, Decimal]:
        """Calculate current allocation by asset class."""
        allocations: dict[AssetClass, Decimal] = {ac: Decimal("0") for ac in AssetClass}
        
        # Cash allocation
        cash_percent = (cash_balance / total_value * 100) if total_value > 0 else Decimal("0")
        allocations[AssetClass.CASH] = cash_percent
        
        # Position allocations
        for pos in positions:
            value = Decimal(str(pos.get("market_value", 0)))
            weight = (value / total_value * 100) if total_value > 0 else Decimal("0")
            
            # Determine asset class
            asset_class_str = pos.get("asset_class", "").lower()
            country = pos.get("country", "").lower()
            
            # Map to asset class
            if asset_class_str == "fixed_income":
                ac = AssetClass.FIXED_INCOME
            elif asset_class_str == "commodities":
                ac = AssetClass.COMMODITIES
            elif asset_class_str == "crypto":
                ac = AssetClass.CRYPTO
            elif country in ["us", "usa", "united states"]:
                ac = AssetClass.EQUITY_US
            elif country in ["uk", "gb", "germany", "france", "italy", "spain", "switzerland"]:
                ac = AssetClass.EQUITY_EU
            elif country in ["japan", "china", "hong kong", "korea", "taiwan", "singapore", "australia"]:
                ac = AssetClass.EQUITY_ASIA
            elif country in ["brazil", "india", "mexico", "indonesia", "turkey"]:
                ac = AssetClass.EQUITY_EMERGING
            else:
                ac = AssetClass.OTHER
            
            allocations[ac] = allocations.get(ac, Decimal("0")) + weight
        
        return allocations
    
    def _calculate_sector_allocation(
        self,
        total_value: Decimal,
        positions: list[dict],
    ) -> dict[str, Decimal]:
        """Calculate current allocation by sector."""
        allocations: dict[str, Decimal] = {}
        
        for pos in positions:
            value = Decimal(str(pos.get("market_value", 0)))
            weight = (value / total_value * 100) if total_value > 0 else Decimal("0")
            sector = pos.get("sector", "other").lower()
            allocations[sector] = allocations.get(sector, Decimal("0")) + weight
        
        return allocations
    
    def _calculate_drift(
        self,
        current: dict[AssetClass, Decimal],
        targets: dict[AssetClass, AllocationRange],
    ) -> list[AllocationTarget]:
        """Calculate drift from target for each asset class."""
        results = []
        
        for asset_class in AssetClass:
            current_weight = current.get(asset_class, Decimal("0"))
            target_range = targets.get(asset_class)
            
            if target_range:
                target_weight = target_range.target_weight or Decimal("0")
            else:
                target_weight = Decimal("0")
            
            drift = current_weight - target_weight
            drift_percent = (
                (abs(drift) / target_weight * 100) if target_weight > 0 
                else Decimal("0")
            )
            
            results.append(AllocationTarget(
                name=asset_class.value,
                target_weight=target_weight,
                current_weight=current_weight,
                drift=drift,
                drift_percent=drift_percent,
            ))
        
        return results
    
    def _calculate_sector_drift(
        self,
        current: dict[str, Decimal],
        targets: dict[Sector, AllocationRange],
    ) -> list[AllocationTarget]:
        """Calculate drift from target for each sector."""
        results = []
        
        # Get all sectors (from current and targets)
        all_sectors = set(current.keys())
        for sector in Sector:
            all_sectors.add(sector.value)
        
        for sector_name in all_sectors:
            current_weight = current.get(sector_name, Decimal("0"))
            
            # Find target
            target_weight = Decimal("0")
            for sector_enum, allocation in targets.items():
                if sector_enum.value == sector_name:
                    target_weight = allocation.target_weight or Decimal("0")
                    break
            
            drift = current_weight - target_weight
            drift_percent = (
                (abs(drift) / target_weight * 100) if target_weight > 0 
                else Decimal("0")
            )
            
            results.append(AllocationTarget(
                name=sector_name,
                target_weight=target_weight,
                current_weight=current_weight,
                drift=drift,
                drift_percent=drift_percent,
            ))
        
        # Sort by absolute drift (highest first)
        results.sort(key=lambda x: abs(x.drift), reverse=True)
        
        return results
    
    def _generate_recommendations(
        self,
        total_value: Decimal,
        cash_balance: Decimal,
        positions: list[dict],
        asset_allocations: list[AllocationTarget],
        sector_allocations: list[AllocationTarget],
    ) -> list[RebalanceRecommendation]:
        """Generate rebalancing recommendations."""
        recommendations = []
        min_trade = self.profile.rebalancing_rules.min_trade_value
        
        # Analyze each position
        for pos in positions:
            symbol = pos.get("symbol", "")
            current_value = Decimal(str(pos.get("market_value", 0)))
            current_weight = (current_value / total_value * 100) if total_value > 0 else Decimal("0")
            
            sector = pos.get("sector", "other").lower()
            
            # Find sector drift
            sector_drift = Decimal("0")
            for sa in sector_allocations:
                if sa.name == sector:
                    sector_drift = sa.drift
                    break
            
            # Determine action based on drift
            if sector_drift > self.profile.rebalancing_rules.drift_threshold_percent:
                # Sector is overweight, consider selling
                target_reduction = sector_drift / 100 * total_value
                trade_value = min(target_reduction / len([p for p in positions if p.get("sector", "").lower() == sector]), current_value * Decimal("0.3"))
                
                if trade_value >= min_trade:
                    recommendations.append(RebalanceRecommendation(
                        symbol=symbol,
                        action="sell",
                        current_value=current_value,
                        target_value=current_value - trade_value,
                        trade_value=-trade_value,
                        current_weight=current_weight,
                        target_weight=current_weight - (trade_value / total_value * 100),
                        reason=f"Reduce {sector} sector overweight ({sector_drift:.1f}% drift)",
                        priority=1 if sector_drift > self.profile.rebalancing_rules.immediate_rebalance_drift else 2,
                    ))
            
            elif sector_drift < -self.profile.rebalancing_rules.drift_threshold_percent:
                # Sector is underweight, consider buying more
                target_increase = abs(sector_drift) / 100 * total_value
                trade_value = min(target_increase, cash_balance * Decimal("0.2"))
                
                if trade_value >= min_trade:
                    recommendations.append(RebalanceRecommendation(
                        symbol=symbol,
                        action="buy",
                        current_value=current_value,
                        target_value=current_value + trade_value,
                        trade_value=trade_value,
                        current_weight=current_weight,
                        target_weight=current_weight + (trade_value / total_value * 100),
                        reason=f"Increase {sector} sector allocation ({abs(sector_drift):.1f}% underweight)",
                        priority=2,
                    ))
        
        # Check if cash is too high
        cash_allocation = None
        for aa in asset_allocations:
            if aa.name == AssetClass.CASH.value:
                cash_allocation = aa
                break
        
        if cash_allocation and cash_allocation.is_overweight:
            excess_cash = cash_allocation.drift / 100 * total_value
            if excess_cash >= min_trade:
                # Recommend deploying excess cash (will be handled by user choosing stocks)
                recommendations.append(RebalanceRecommendation(
                    symbol="CASH",
                    action="deploy",
                    current_value=cash_balance,
                    target_value=cash_balance - excess_cash,
                    trade_value=-excess_cash,
                    current_weight=cash_allocation.current_weight,
                    target_weight=cash_allocation.target_weight,
                    reason=f"Deploy excess cash ({cash_allocation.drift:.1f}% overweight)",
                    priority=3,
                ))
        
        # Sort by priority
        recommendations.sort(key=lambda x: x.priority)
        
        return recommendations
    
    def _empty_analysis(self) -> AllocationAnalysis:
        """Return empty analysis for zero-value portfolio."""
        return AllocationAnalysis(
            total_value=Decimal("0"),
            cash_balance=Decimal("0"),
            asset_class_allocations=[],
            sector_allocations=[],
            needs_rebalancing=False,
            max_drift=Decimal("0"),
            rebalance_recommendations=[],
        )


# ==================== Convenience Functions ====================

def analyze_portfolio_allocation(
    risk_profile: str,
    total_value: Decimal,
    cash_balance: Decimal,
    positions: list[dict],
) -> dict:
    """
    Convenience function to analyze portfolio allocation.
    
    Returns dict with allocation analysis suitable for API response.
    """
    allocator = AssetAllocator(risk_profile)
    analysis = allocator.analyze_allocation(total_value, cash_balance, positions)
    return analysis.to_dict()


def get_rebalancing_trades(
    risk_profile: str,
    total_value: Decimal,
    cash_balance: Decimal,
    positions: list[dict],
) -> list[dict]:
    """
    Get list of recommended trades for rebalancing.
    
    Returns list of trade recommendations.
    """
    allocator = AssetAllocator(risk_profile)
    analysis = allocator.analyze_allocation(total_value, cash_balance, positions)
    return [r.to_dict() for r in analysis.rebalance_recommendations]
