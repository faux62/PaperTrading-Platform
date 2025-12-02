"""
Portfolio Constraints Validator

Validates portfolio operations against risk profile constraints.
Checks position limits, sector exposure, diversification rules, etc.
"""
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional, Any
from enum import Enum
from loguru import logger

from app.core.portfolio.risk_profiles import (
    RiskProfile,
    AssetClass,
    Sector,
    get_risk_profile,
)


class ViolationType(str, Enum):
    """Types of constraint violations."""
    POSITION_SIZE = "position_size"
    POSITION_COUNT = "position_count"
    SECTOR_EXPOSURE = "sector_exposure"
    COUNTRY_EXPOSURE = "country_exposure"
    ASSET_CLASS = "asset_class"
    CASH_MINIMUM = "cash_minimum"
    VOLATILITY = "volatility"
    DRAWDOWN = "drawdown"
    CONCENTRATION = "concentration"
    INSUFFICIENT_FUNDS = "insufficient_funds"


class Severity(str, Enum):
    """Violation severity levels."""
    WARNING = "warning"       # Approaching limit
    VIOLATION = "violation"   # Constraint violated
    CRITICAL = "critical"     # Critical violation, block trade


@dataclass
class ConstraintViolation:
    """Represents a constraint violation."""
    violation_type: ViolationType
    severity: Severity
    message: str
    current_value: Decimal
    limit_value: Decimal
    asset: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "type": self.violation_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "current_value": float(self.current_value),
            "limit_value": float(self.limit_value),
            "asset": self.asset,
        }


@dataclass
class ValidationResult:
    """Result of constraint validation."""
    is_valid: bool
    violations: list[ConstraintViolation] = field(default_factory=list)
    warnings: list[ConstraintViolation] = field(default_factory=list)
    
    def add_violation(self, violation: ConstraintViolation) -> None:
        if violation.severity == Severity.WARNING:
            self.warnings.append(violation)
        else:
            self.violations.append(violation)
            self.is_valid = False
    
    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "violations": [v.to_dict() for v in self.violations],
            "warnings": [w.to_dict() for w in self.warnings],
        }


@dataclass
class PortfolioSnapshot:
    """
    Current state of a portfolio for validation.
    
    Represents the portfolio's current holdings, values,
    and allocations for constraint checking.
    """
    total_value: Decimal
    cash_balance: Decimal
    positions: list[dict]  # List of position dicts with symbol, value, sector, etc.
    
    @property
    def equity_value(self) -> Decimal:
        return self.total_value - self.cash_balance
    
    def get_position_weight(self, symbol: str) -> Decimal:
        """Get position weight as percentage of portfolio."""
        if self.total_value == 0:
            return Decimal("0")
        for pos in self.positions:
            if pos.get("symbol") == symbol:
                return (Decimal(str(pos.get("market_value", 0))) / self.total_value) * 100
        return Decimal("0")
    
    def get_sector_weight(self, sector: str) -> Decimal:
        """Get total weight of positions in a sector."""
        if self.total_value == 0:
            return Decimal("0")
        sector_value = sum(
            Decimal(str(pos.get("market_value", 0)))
            for pos in self.positions
            if pos.get("sector", "").lower() == sector.lower()
        )
        return (sector_value / self.total_value) * 100
    
    def get_country_weight(self, country: str) -> Decimal:
        """Get total weight of positions in a country."""
        if self.total_value == 0:
            return Decimal("0")
        country_value = sum(
            Decimal(str(pos.get("market_value", 0)))
            for pos in self.positions
            if pos.get("country", "").lower() == country.lower()
        )
        return (country_value / self.total_value) * 100


class ConstraintsValidator:
    """
    Validates portfolio operations against risk profile constraints.
    
    Usage:
        validator = ConstraintsValidator(risk_profile)
        
        # Validate entire portfolio
        result = validator.validate_portfolio(snapshot)
        
        # Validate a proposed trade
        result = validator.validate_trade(snapshot, trade_order)
        
        if not result.is_valid:
            for violation in result.violations:
                print(f"Violation: {violation.message}")
    """
    
    def __init__(self, risk_profile: RiskProfile | str):
        if isinstance(risk_profile, str):
            self.profile = get_risk_profile(risk_profile)
        else:
            self.profile = risk_profile
    
    def validate_portfolio(self, snapshot: PortfolioSnapshot) -> ValidationResult:
        """
        Validate entire portfolio state against constraints.
        
        Checks all constraints and returns a complete validation result.
        """
        result = ValidationResult(is_valid=True)
        
        # Validate position count
        self._validate_position_count(snapshot, result)
        
        # Validate individual position sizes
        for pos in snapshot.positions:
            self._validate_position_size(snapshot, pos, result)
        
        # Validate sector exposure
        self._validate_sector_exposure(snapshot, result)
        
        # Validate cash minimum
        self._validate_cash_minimum(snapshot, result)
        
        return result
    
    def validate_trade(
        self,
        snapshot: PortfolioSnapshot,
        symbol: str,
        trade_type: str,  # 'buy' or 'sell'
        quantity: Decimal,
        price: Decimal,
        sector: Optional[str] = None,
        country: Optional[str] = None,
    ) -> ValidationResult:
        """
        Validate a proposed trade against constraints.
        
        Simulates the trade and checks if the resulting portfolio
        would violate any constraints.
        """
        result = ValidationResult(is_valid=True)
        
        trade_value = quantity * price
        
        # For buys, check various constraints
        if trade_type.lower() == "buy":
            # Check sufficient funds
            if trade_value > snapshot.cash_balance:
                result.add_violation(ConstraintViolation(
                    violation_type=ViolationType.INSUFFICIENT_FUNDS,
                    severity=Severity.CRITICAL,
                    message=f"Insufficient funds: need ${trade_value:.2f}, have ${snapshot.cash_balance:.2f}",
                    current_value=snapshot.cash_balance,
                    limit_value=trade_value,
                    asset=symbol,
                ))
                return result
            
            # Simulate new portfolio state
            new_cash = snapshot.cash_balance - trade_value
            new_total = snapshot.total_value  # Total doesn't change on trade
            
            # Check cash minimum after trade
            cash_percent = (new_cash / new_total) * 100 if new_total > 0 else Decimal("0")
            cash_min = self.profile.asset_allocation.get(
                AssetClass.CASH
            )
            if cash_min and cash_percent < cash_min.min_weight:
                result.add_violation(ConstraintViolation(
                    violation_type=ViolationType.CASH_MINIMUM,
                    severity=Severity.VIOLATION,
                    message=f"Trade would reduce cash below minimum ({cash_min.min_weight}%)",
                    current_value=cash_percent,
                    limit_value=cash_min.min_weight,
                ))
            
            # Check new position size
            existing_value = Decimal("0")
            for pos in snapshot.positions:
                if pos.get("symbol") == symbol:
                    existing_value = Decimal(str(pos.get("market_value", 0)))
                    break
            
            new_position_value = existing_value + trade_value
            new_position_percent = (new_position_value / new_total) * 100 if new_total > 0 else Decimal("0")
            
            max_position = self.profile.position_limits.max_position_size_percent
            if new_position_percent > max_position:
                result.add_violation(ConstraintViolation(
                    violation_type=ViolationType.POSITION_SIZE,
                    severity=Severity.VIOLATION,
                    message=f"Position {symbol} would exceed max size ({max_position}%)",
                    current_value=new_position_percent,
                    limit_value=max_position,
                    asset=symbol,
                ))
            elif new_position_percent > max_position * Decimal("0.9"):
                result.add_violation(ConstraintViolation(
                    violation_type=ViolationType.POSITION_SIZE,
                    severity=Severity.WARNING,
                    message=f"Position {symbol} approaching max size limit",
                    current_value=new_position_percent,
                    limit_value=max_position,
                    asset=symbol,
                ))
            
            # Check position count (if new position)
            if existing_value == 0:
                current_count = len(snapshot.positions)
                max_positions = self.profile.position_limits.max_positions
                if current_count >= max_positions:
                    result.add_violation(ConstraintViolation(
                        violation_type=ViolationType.POSITION_COUNT,
                        severity=Severity.VIOLATION,
                        message=f"Maximum positions ({max_positions}) reached",
                        current_value=Decimal(str(current_count)),
                        limit_value=Decimal(str(max_positions)),
                    ))
            
            # Check sector exposure
            if sector:
                current_sector_value = sum(
                    Decimal(str(pos.get("market_value", 0)))
                    for pos in snapshot.positions
                    if pos.get("sector", "").lower() == sector.lower()
                )
                new_sector_value = current_sector_value + trade_value
                new_sector_percent = (new_sector_value / new_total) * 100 if new_total > 0 else Decimal("0")
                
                max_sector = self.profile.position_limits.max_sector_exposure
                if new_sector_percent > max_sector:
                    result.add_violation(ConstraintViolation(
                        violation_type=ViolationType.SECTOR_EXPOSURE,
                        severity=Severity.VIOLATION,
                        message=f"Sector {sector} would exceed max exposure ({max_sector}%)",
                        current_value=new_sector_percent,
                        limit_value=max_sector,
                        asset=sector,
                    ))
            
            # Check country exposure
            if country:
                current_country_value = sum(
                    Decimal(str(pos.get("market_value", 0)))
                    for pos in snapshot.positions
                    if pos.get("country", "").lower() == country.lower()
                )
                new_country_value = current_country_value + trade_value
                new_country_percent = (new_country_value / new_total) * 100 if new_total > 0 else Decimal("0")
                
                max_country = self.profile.position_limits.max_country_exposure
                if new_country_percent > max_country:
                    result.add_violation(ConstraintViolation(
                        violation_type=ViolationType.COUNTRY_EXPOSURE,
                        severity=Severity.VIOLATION,
                        message=f"Country {country} would exceed max exposure ({max_country}%)",
                        current_value=new_country_percent,
                        limit_value=max_country,
                        asset=country,
                    ))
        
        # For sells, mainly check minimum position count
        elif trade_type.lower() == "sell":
            # Check if this would close the position
            for pos in snapshot.positions:
                if pos.get("symbol") == symbol:
                    current_qty = Decimal(str(pos.get("quantity", 0)))
                    if quantity >= current_qty:
                        # Position will be closed
                        remaining_positions = len(snapshot.positions) - 1
                        min_positions = self.profile.position_limits.min_positions
                        if remaining_positions < min_positions:
                            result.add_violation(ConstraintViolation(
                                violation_type=ViolationType.POSITION_COUNT,
                                severity=Severity.WARNING,
                                message=f"Closing {symbol} would leave fewer than minimum positions ({min_positions})",
                                current_value=Decimal(str(remaining_positions)),
                                limit_value=Decimal(str(min_positions)),
                            ))
                    break
        
        return result
    
    def _validate_position_count(
        self,
        snapshot: PortfolioSnapshot,
        result: ValidationResult,
    ) -> None:
        """Validate position count constraints."""
        count = len(snapshot.positions)
        limits = self.profile.position_limits
        
        if count < limits.min_positions:
            result.add_violation(ConstraintViolation(
                violation_type=ViolationType.POSITION_COUNT,
                severity=Severity.WARNING,
                message=f"Portfolio has fewer positions ({count}) than minimum ({limits.min_positions})",
                current_value=Decimal(str(count)),
                limit_value=Decimal(str(limits.min_positions)),
            ))
        
        if count > limits.max_positions:
            result.add_violation(ConstraintViolation(
                violation_type=ViolationType.POSITION_COUNT,
                severity=Severity.VIOLATION,
                message=f"Portfolio exceeds maximum positions ({limits.max_positions})",
                current_value=Decimal(str(count)),
                limit_value=Decimal(str(limits.max_positions)),
            ))
    
    def _validate_position_size(
        self,
        snapshot: PortfolioSnapshot,
        position: dict,
        result: ValidationResult,
    ) -> None:
        """Validate individual position size constraints."""
        if snapshot.total_value == 0:
            return
        
        symbol = position.get("symbol", "Unknown")
        market_value = Decimal(str(position.get("market_value", 0)))
        weight = (market_value / snapshot.total_value) * 100
        
        limits = self.profile.position_limits
        
        # Check max position size
        if weight > limits.max_position_size_percent:
            result.add_violation(ConstraintViolation(
                violation_type=ViolationType.POSITION_SIZE,
                severity=Severity.VIOLATION,
                message=f"Position {symbol} ({weight:.1f}%) exceeds maximum ({limits.max_position_size_percent}%)",
                current_value=weight,
                limit_value=limits.max_position_size_percent,
                asset=symbol,
            ))
        elif weight > limits.max_position_size_percent * Decimal("0.9"):
            result.add_violation(ConstraintViolation(
                violation_type=ViolationType.POSITION_SIZE,
                severity=Severity.WARNING,
                message=f"Position {symbol} ({weight:.1f}%) approaching maximum",
                current_value=weight,
                limit_value=limits.max_position_size_percent,
                asset=symbol,
            ))
    
    def _validate_sector_exposure(
        self,
        snapshot: PortfolioSnapshot,
        result: ValidationResult,
    ) -> None:
        """Validate sector exposure constraints."""
        if snapshot.total_value == 0:
            return
        
        # Group positions by sector
        sector_values: dict[str, Decimal] = {}
        for pos in snapshot.positions:
            sector = pos.get("sector", "other").lower()
            value = Decimal(str(pos.get("market_value", 0)))
            sector_values[sector] = sector_values.get(sector, Decimal("0")) + value
        
        max_sector = self.profile.position_limits.max_sector_exposure
        
        for sector, value in sector_values.items():
            weight = (value / snapshot.total_value) * 100
            if weight > max_sector:
                result.add_violation(ConstraintViolation(
                    violation_type=ViolationType.SECTOR_EXPOSURE,
                    severity=Severity.VIOLATION,
                    message=f"Sector {sector} ({weight:.1f}%) exceeds maximum ({max_sector}%)",
                    current_value=weight,
                    limit_value=max_sector,
                    asset=sector,
                ))
    
    def _validate_cash_minimum(
        self,
        snapshot: PortfolioSnapshot,
        result: ValidationResult,
    ) -> None:
        """Validate cash minimum constraints."""
        if snapshot.total_value == 0:
            return
        
        cash_percent = (snapshot.cash_balance / snapshot.total_value) * 100
        
        cash_allocation = self.profile.asset_allocation.get(AssetClass.CASH)
        if cash_allocation and cash_percent < cash_allocation.min_weight:
            result.add_violation(ConstraintViolation(
                violation_type=ViolationType.CASH_MINIMUM,
                severity=Severity.WARNING,
                message=f"Cash ({cash_percent:.1f}%) below minimum ({cash_allocation.min_weight}%)",
                current_value=cash_percent,
                limit_value=cash_allocation.min_weight,
            ))


# ==================== Convenience Functions ====================

def validate_buy_order(
    risk_profile: str,
    portfolio_value: Decimal,
    cash_balance: Decimal,
    positions: list[dict],
    symbol: str,
    quantity: Decimal,
    price: Decimal,
    sector: Optional[str] = None,
    country: Optional[str] = None,
) -> ValidationResult:
    """
    Convenience function to validate a buy order.
    
    Args:
        risk_profile: Profile name ('aggressive', 'balanced', 'prudent')
        portfolio_value: Total portfolio value
        cash_balance: Available cash
        positions: List of current positions
        symbol: Symbol to buy
        quantity: Quantity to buy
        price: Price per share
        sector: Stock sector (optional)
        country: Stock country (optional)
        
    Returns:
        ValidationResult with any violations or warnings
    """
    snapshot = PortfolioSnapshot(
        total_value=portfolio_value,
        cash_balance=cash_balance,
        positions=positions,
    )
    
    validator = ConstraintsValidator(risk_profile)
    return validator.validate_trade(
        snapshot=snapshot,
        symbol=symbol,
        trade_type="buy",
        quantity=quantity,
        price=price,
        sector=sector,
        country=country,
    )


def validate_sell_order(
    risk_profile: str,
    portfolio_value: Decimal,
    cash_balance: Decimal,
    positions: list[dict],
    symbol: str,
    quantity: Decimal,
    price: Decimal,
) -> ValidationResult:
    """
    Convenience function to validate a sell order.
    """
    snapshot = PortfolioSnapshot(
        total_value=portfolio_value,
        cash_balance=cash_balance,
        positions=positions,
    )
    
    validator = ConstraintsValidator(risk_profile)
    return validator.validate_trade(
        snapshot=snapshot,
        symbol=symbol,
        trade_type="sell",
        quantity=quantity,
        price=price,
    )
