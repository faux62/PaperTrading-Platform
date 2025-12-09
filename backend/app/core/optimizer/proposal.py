"""
Portfolio Proposal Generator

Creates actionable portfolio composition proposals with:
- Asset allocations with rationale
- Expected performance metrics
- Risk assessment
- Rebalancing recommendations
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

from .risk_models import RiskModel, RiskMetrics
from .strategies import OptimizationResult


class ProposalStatus(str, Enum):
    """Status of a portfolio proposal"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    EXPIRED = "expired"


class ProposalType(str, Enum):
    """Type of portfolio proposal"""
    INITIAL = "initial"           # New portfolio construction
    REBALANCE = "rebalance"       # Periodic rebalancing
    TACTICAL = "tactical"         # Tactical adjustment
    RISK_REDUCTION = "risk_reduction"  # Reduce risk


@dataclass
class AllocationItem:
    """Single allocation in a proposal"""
    symbol: str
    name: str
    weight: float
    shares: Optional[int] = None
    value: Optional[float] = None
    sector: Optional[str] = None
    rationale: str = ""
    current_weight: float = 0.0  # For rebalancing
    change: float = 0.0  # Weight change


@dataclass
class PortfolioProposal:
    """
    Complete portfolio proposal with allocations and analysis.
    """
    id: str
    portfolio_id: str
    proposal_type: ProposalType
    status: ProposalStatus
    created_at: datetime
    expires_at: Optional[datetime]
    
    # Allocations
    allocations: List[AllocationItem]
    cash_weight: float = 0.0
    
    # Expected metrics
    expected_return: float = 0.0
    expected_volatility: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    
    # Risk analysis
    risk_metrics: Optional[RiskMetrics] = None
    sector_weights: Dict[str, float] = field(default_factory=dict)
    diversification_ratio: float = 0.0
    
    # Rationale
    summary: str = ""
    methodology: str = ""
    considerations: List[str] = field(default_factory=list)
    
    # For rebalancing
    turnover: float = 0.0
    estimated_costs: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            "id": self.id,
            "portfolio_id": self.portfolio_id,
            "proposal_type": self.proposal_type.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "allocations": [
                {
                    "symbol": a.symbol,
                    "name": a.name,
                    "weight": a.weight,
                    "shares": a.shares,
                    "value": a.value,
                    "sector": a.sector,
                    "rationale": a.rationale,
                    "current_weight": a.current_weight,
                    "change": a.change
                }
                for a in self.allocations
            ],
            "cash_weight": self.cash_weight,
            "expected_return": self.expected_return,
            "expected_volatility": self.expected_volatility,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "sector_weights": self.sector_weights,
            "diversification_ratio": self.diversification_ratio,
            "summary": self.summary,
            "methodology": self.methodology,
            "considerations": self.considerations,
            "turnover": self.turnover,
            "estimated_costs": self.estimated_costs
        }


class ProposalGenerator:
    """
    Generates portfolio proposals from optimization results.
    
    Transforms raw optimization outputs into actionable proposals
    with clear rationale and execution guidance.
    """
    
    def __init__(
        self,
        risk_model: RiskModel,
        transaction_cost: float = 0.001  # 0.1% per trade
    ):
        self.risk_model = risk_model
        self.transaction_cost = transaction_cost
    
    def generate_proposal(
        self,
        portfolio_id: str,
        optimization_result: OptimizationResult,
        assets: List[Dict],
        capital: float,
        returns_data: pd.DataFrame,
        proposal_type: ProposalType = ProposalType.INITIAL,
        current_allocations: Optional[List[AllocationItem]] = None,
        methodology: str = "",
        expiry_hours: int = 24
    ) -> PortfolioProposal:
        """
        Generate a complete portfolio proposal.
        
        Args:
            portfolio_id: ID of the target portfolio
            optimization_result: Result from optimizer
            assets: List of asset info dicts with symbol, name, sector
            capital: Total capital to invest
            returns_data: Historical returns for risk calculations
            proposal_type: Type of proposal
            current_allocations: Current holdings (for rebalancing)
            methodology: Description of optimization method used
            expiry_hours: Hours until proposal expires
            
        Returns:
            Complete PortfolioProposal
        """
        proposal_id = str(uuid.uuid4())
        now = datetime.now()
        
        # Build allocations
        allocations = self._build_allocations(
            optimization_result.weights,
            assets,
            capital,
            current_allocations
        )
        
        # Calculate sector weights
        sector_weights = self._calculate_sector_weights(allocations)
        
        # Calculate turnover if rebalancing
        turnover = 0.0
        if current_allocations:
            turnover = self._calculate_turnover(allocations, current_allocations)
        
        # Estimate transaction costs
        estimated_costs = turnover * capital * self.transaction_cost
        
        # Calculate risk metrics
        weights = optimization_result.weights
        risk_metrics = self.risk_model.calculate_portfolio_risk(
            weights, returns_data
        )
        
        # Generate summary and considerations
        summary = self._generate_summary(
            proposal_type, optimization_result, allocations, methodology
        )
        considerations = self._generate_considerations(
            optimization_result, allocations, risk_metrics
        )
        
        return PortfolioProposal(
            id=proposal_id,
            portfolio_id=portfolio_id,
            proposal_type=proposal_type,
            status=ProposalStatus.PENDING,
            created_at=now,
            expires_at=datetime.fromtimestamp(
                now.timestamp() + expiry_hours * 3600
            ),
            allocations=allocations,
            cash_weight=max(0, 1 - sum(a.weight for a in allocations)),
            expected_return=optimization_result.expected_return,
            expected_volatility=optimization_result.expected_volatility,
            sharpe_ratio=optimization_result.sharpe_ratio,
            max_drawdown=risk_metrics.max_drawdown,
            risk_metrics=risk_metrics,
            sector_weights=sector_weights,
            diversification_ratio=optimization_result.diversification_ratio or 0,
            summary=summary,
            methodology=methodology,
            considerations=considerations,
            turnover=turnover,
            estimated_costs=estimated_costs
        )
    
    def _build_allocations(
        self,
        weights: np.ndarray,
        assets: List[Dict],
        capital: float,
        current_allocations: Optional[List[AllocationItem]] = None
    ) -> List[AllocationItem]:
        """Build allocation items from weights"""
        # Build current weights lookup
        current_weights = {}
        if current_allocations:
            current_weights = {a.symbol: a.weight for a in current_allocations}
        
        allocations = []
        for i, (weight, asset) in enumerate(zip(weights, assets)):
            if weight < 0.001:  # Skip tiny allocations
                continue
            
            symbol = asset.get('symbol', f'ASSET_{i}')
            current_weight = current_weights.get(symbol, 0.0)
            value = weight * capital
            
            # Estimate shares (would need price data for accuracy)
            price = asset.get('price', 100)  # Default price
            shares = int(value / price) if price > 0 else 0
            
            # Generate rationale based on metrics
            rationale = self._generate_allocation_rationale(asset, weight)
            
            allocations.append(AllocationItem(
                symbol=symbol,
                name=asset.get('name', symbol),
                weight=weight,
                shares=shares,
                value=value,
                sector=asset.get('sector'),
                rationale=rationale,
                current_weight=current_weight,
                change=weight - current_weight
            ))
        
        # Sort by weight descending
        allocations.sort(key=lambda x: x.weight, reverse=True)
        
        return allocations
    
    def _generate_allocation_rationale(
        self,
        asset: Dict,
        weight: float
    ) -> str:
        """Generate rationale for individual allocation"""
        reasons = []
        
        score = asset.get('total_score', 0)
        if score > 0.7:
            reasons.append("high composite score")
        
        momentum = asset.get('metrics', {}).get('momentum_6m', 0)
        if momentum and momentum > 0.1:
            reasons.append("strong momentum")
        
        vol = asset.get('metrics', {}).get('volatility', 0)
        if vol and vol < 0.2:
            reasons.append("low volatility")
        
        div_yield = asset.get('metrics', {}).get('dividend_yield', 0)
        if div_yield and div_yield > 0.02:
            reasons.append(f"{div_yield*100:.1f}% dividend yield")
        
        if not reasons:
            reasons.append("good risk-adjusted characteristics")
        
        return f"Weight {weight*100:.1f}%: {', '.join(reasons)}"
    
    def _calculate_sector_weights(
        self,
        allocations: List[AllocationItem]
    ) -> Dict[str, float]:
        """Calculate sector exposure"""
        sector_weights = {}
        for alloc in allocations:
            sector = alloc.sector or "Unknown"
            sector_weights[sector] = sector_weights.get(sector, 0) + alloc.weight
        return sector_weights
    
    def _calculate_turnover(
        self,
        new_allocations: List[AllocationItem],
        current_allocations: List[AllocationItem]
    ) -> float:
        """Calculate portfolio turnover"""
        current = {a.symbol: a.weight for a in current_allocations}
        new = {a.symbol: a.weight for a in new_allocations}
        
        all_symbols = set(current.keys()) | set(new.keys())
        
        turnover = sum(
            abs(new.get(s, 0) - current.get(s, 0))
            for s in all_symbols
        ) / 2  # Divide by 2 as buys equal sells
        
        return turnover
    
    def _generate_summary(
        self,
        proposal_type: ProposalType,
        result: OptimizationResult,
        allocations: List[AllocationItem],
        methodology: str
    ) -> str:
        """Generate executive summary"""
        n_assets = len(allocations)
        top_3 = allocations[:3]
        top_names = ", ".join(a.symbol for a in top_3)
        
        type_desc = {
            ProposalType.INITIAL: "Initial portfolio construction",
            ProposalType.REBALANCE: "Portfolio rebalancing",
            ProposalType.TACTICAL: "Tactical adjustment",
            ProposalType.RISK_REDUCTION: "Risk reduction"
        }
        
        summary = f"{type_desc[proposal_type]} using {methodology}. "
        summary += f"Proposes {n_assets} positions with top holdings: {top_names}. "
        summary += f"Expected annual return: {result.expected_return*100:.1f}%, "
        summary += f"volatility: {result.expected_volatility*100:.1f}%, "
        summary += f"Sharpe ratio: {result.sharpe_ratio:.2f}."
        
        return summary
    
    def _generate_considerations(
        self,
        result: OptimizationResult,
        allocations: List[AllocationItem],
        risk_metrics: RiskMetrics
    ) -> List[str]:
        """Generate considerations and caveats"""
        considerations = []
        
        # Concentration risk
        top_weight = allocations[0].weight if allocations else 0
        if top_weight > 0.15:
            considerations.append(
                f"High concentration: largest position is {top_weight*100:.1f}% of portfolio"
            )
        
        # Volatility warning
        if result.expected_volatility > 0.25:
            considerations.append(
                f"Higher volatility ({result.expected_volatility*100:.1f}%) may lead to significant drawdowns"
            )
        
        # Max drawdown warning
        if risk_metrics.max_drawdown < -0.2:
            considerations.append(
                f"Historical max drawdown of {risk_metrics.max_drawdown*100:.1f}% observed"
            )
        
        # Sector concentration
        sector_weights = self._calculate_sector_weights(allocations)
        max_sector = max(sector_weights.values()) if sector_weights else 0
        if max_sector > 0.4:
            top_sector = max(sector_weights, key=sector_weights.get)
            considerations.append(
                f"Sector concentration: {top_sector} represents {max_sector*100:.1f}%"
            )
        
        # Number of positions
        if len(allocations) < 10:
            considerations.append(
                "Limited diversification with fewer than 10 positions"
            )
        
        # General disclaimer
        considerations.append(
            "Past performance does not guarantee future results. "
            "This proposal is based on historical data and optimization models."
        )
        
        return considerations
    
    def generate_rebalance_proposal(
        self,
        portfolio_id: str,
        current_positions: List[Dict],
        target_weights: np.ndarray,
        assets: List[Dict],
        capital: float,
        returns_data: pd.DataFrame,
        rebalance_threshold: float = 0.05,
        methodology: str = "Threshold-based rebalancing"
    ) -> Optional[PortfolioProposal]:
        """
        Generate rebalancing proposal if drift exceeds threshold.
        
        Args:
            portfolio_id: Portfolio ID
            current_positions: Current holdings
            target_weights: Target allocation weights
            assets: Asset information
            capital: Current portfolio value
            returns_data: Historical returns
            rebalance_threshold: Minimum drift to trigger rebalancing
            methodology: Description of method
            
        Returns:
            PortfolioProposal if rebalancing needed, None otherwise
        """
        # Build current allocations
        current_allocations = []
        current_value = sum(p.get('value', 0) for p in current_positions)
        
        for pos in current_positions:
            weight = pos.get('value', 0) / current_value if current_value > 0 else 0
            current_allocations.append(AllocationItem(
                symbol=pos.get('symbol', ''),
                name=pos.get('name', ''),
                weight=weight,
                shares=pos.get('shares'),
                value=pos.get('value'),
                sector=pos.get('sector')
            ))
        
        # Calculate drift
        current_weights = {a.symbol: a.weight for a in current_allocations}
        max_drift = 0
        
        for i, asset in enumerate(assets):
            symbol = asset.get('symbol', '')
            current = current_weights.get(symbol, 0)
            target = target_weights[i]
            drift = abs(current - target)
            max_drift = max(max_drift, drift)
        
        # Check if rebalancing needed
        if max_drift < rebalance_threshold:
            return None
        
        # Create optimization result from target weights
        cov = returns_data.cov().values * 252
        expected_returns = returns_data.mean().values * 252
        
        opt_result = OptimizationResult(
            weights=target_weights,
            expected_return=float(target_weights @ expected_returns),
            expected_volatility=float(np.sqrt(target_weights @ cov @ target_weights)),
            sharpe_ratio=0,
            success=True,
            message="Rebalancing target"
        )
        opt_result.sharpe_ratio = (
            opt_result.expected_return / opt_result.expected_volatility
            if opt_result.expected_volatility > 0 else 0
        )
        
        return self.generate_proposal(
            portfolio_id=portfolio_id,
            optimization_result=opt_result,
            assets=assets,
            capital=capital,
            returns_data=returns_data,
            proposal_type=ProposalType.REBALANCE,
            current_allocations=current_allocations,
            methodology=methodology
        )
