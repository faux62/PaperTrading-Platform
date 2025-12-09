"""
Portfolio Optimizer API Endpoints

Provides REST API for portfolio optimization:
- Request new optimization proposals
- View and manage proposals
- Accept/reject proposals
- Get efficient frontier data
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum
import uuid

from app.db.database import get_db
from app.db.models.user import User
from app.db.models.portfolio import Portfolio
from app.core.security import get_current_user
from app.core.optimizer import PortfolioOptimizer, OptimizationMethod
from app.core.optimizer.optimizer import OptimizationRequest, OptimizationResponse
from app.core.optimizer.proposal import ProposalStatus, ProposalType

router = APIRouter(prefix="/optimizer", tags=["Portfolio Optimizer"])


# ============== Pydantic Schemas ==============

class OptimizationMethodEnum(str, Enum):
    """Optimization methods available via API"""
    MEAN_VARIANCE = "mean_variance"
    MIN_VARIANCE = "min_variance"
    MAX_SHARPE = "max_sharpe"
    RISK_PARITY = "risk_parity"
    HRP = "hrp"
    BLACK_LITTERMAN = "black_litterman"


class ViewSchema(BaseModel):
    """Black-Litterman view specification"""
    assets: List[int] = Field(..., description="Asset indices")
    weights: List[float] = Field(..., description="View weights (sum to 0 for relative)")
    expected_return: float = Field(..., alias="return", description="Expected return")


class OptimizationRequestSchema(BaseModel):
    """Request for portfolio optimization"""
    portfolio_id: int = Field(..., description="Portfolio ID")
    
    # Optional overrides (will use portfolio settings if not provided)
    method: Optional[OptimizationMethodEnum] = Field(None, description="Optimization method")
    universe: Optional[List[str]] = Field(None, description="Specific symbols to consider")
    sectors: Optional[List[str]] = Field(None, description="Allowed sectors")
    excluded_symbols: Optional[List[str]] = Field(None, description="Symbols to exclude")
    
    # Position constraints
    min_positions: int = Field(5, ge=3, le=50, description="Minimum number of positions")
    max_positions: int = Field(30, ge=5, le=100, description="Maximum number of positions")
    max_weight_per_asset: float = Field(0.20, ge=0.05, le=0.50, description="Max weight per asset")
    min_weight_per_asset: float = Field(0.02, ge=0.01, le=0.10, description="Min weight per asset")
    
    # Black-Litterman views
    views: Optional[List[ViewSchema]] = Field(None, description="Investor views for BL model")
    
    class Config:
        json_schema_extra = {
            "example": {
                "portfolio_id": "123e4567-e89b-12d3-a456-426614174000",
                "method": "risk_parity",
                "min_positions": 10,
                "max_positions": 25,
                "max_weight_per_asset": 0.15
            }
        }


class AllocationSchema(BaseModel):
    """Single allocation in a proposal"""
    symbol: str
    name: str
    weight: float
    shares: Optional[int]
    value: Optional[float]
    sector: Optional[str]
    rationale: str
    current_weight: float = 0.0
    change: float = 0.0


class ProposalSchema(BaseModel):
    """Portfolio optimization proposal"""
    id: str
    portfolio_id: str
    proposal_type: str
    status: str
    created_at: datetime
    expires_at: Optional[datetime]
    
    allocations: List[AllocationSchema]
    cash_weight: float
    
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    max_drawdown: float
    
    sector_weights: Dict[str, float]
    diversification_ratio: float
    
    summary: str
    methodology: str
    considerations: List[str]
    
    turnover: float
    estimated_costs: float


class OptimizationResponseSchema(BaseModel):
    """Response from optimization request"""
    success: bool
    proposal: Optional[ProposalSchema]
    screened_count: int
    execution_time_ms: float
    error: Optional[str]


class EfficientFrontierPointSchema(BaseModel):
    """Single point on efficient frontier"""
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    weights: List[float]


class ProposalActionSchema(BaseModel):
    """Action on a proposal (approve/reject)"""
    action: str = Field(..., pattern="^(approve|reject)$")
    notes: Optional[str] = Field(None, max_length=500)


class RebalanceCheckSchema(BaseModel):
    """Request to check if rebalancing is needed"""
    portfolio_id: int
    threshold: float = Field(0.05, ge=0.01, le=0.20, description="Drift threshold to trigger rebalance")


# ============== In-Memory Proposal Storage ==============
# In production, this would be stored in database

_proposals: Dict[str, Dict] = {}


# ============== API Endpoints ==============

@router.post(
    "/optimize",
    response_model=OptimizationResponseSchema,
    summary="Request Portfolio Optimization",
    description="Generate an optimized portfolio proposal based on portfolio parameters"
)
async def request_optimization(
    request: OptimizationRequestSchema,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Request a new portfolio optimization.
    
    The optimizer will:
    1. Screen the investment universe based on criteria
    2. Fetch historical data for selected assets
    3. Run the optimization algorithm
    4. Generate a proposal with allocations and rationale
    
    The proposal can then be reviewed, approved, or rejected.
    """
    # Verify portfolio exists and belongs to user
    from sqlalchemy import select
    result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == request.portfolio_id,
            Portfolio.user_id == current_user.id
        )
    )
    portfolio = result.scalar_one_or_none()
    
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    
    if not portfolio.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot optimize inactive portfolio"
        )
    
    # Build optimization request
    opt_request = OptimizationRequest(
        portfolio_id=str(portfolio.id),
        capital=float(portfolio.initial_capital),
        risk_profile=portfolio.risk_profile,
        time_horizon_weeks=portfolio.strategy_period_weeks or 12,
        method=OptimizationMethod(request.method.value) if request.method else None,
        universe=request.universe,
        sectors=request.sectors,
        excluded_symbols=request.excluded_symbols,
        min_positions=request.min_positions,
        max_positions=request.max_positions,
        max_weight_per_asset=request.max_weight_per_asset,
        min_weight_per_asset=request.min_weight_per_asset,
        views=[
            {"assets": v.assets, "weights": v.weights, "return": v.expected_return}
            for v in request.views
        ] if request.views else None
    )
    
    # Run optimization
    optimizer = PortfolioOptimizer()
    response = await optimizer.optimize(opt_request)
    
    # Store proposal if successful
    if response.success and response.proposal:
        proposal_data = response.proposal.to_dict()
        proposal_data['user_id'] = str(current_user.id)
        _proposals[response.proposal.id] = proposal_data
    
    # Build response
    return OptimizationResponseSchema(
        success=response.success,
        proposal=ProposalSchema(**response.proposal.to_dict()) if response.proposal else None,
        screened_count=len(response.screened_assets),
        execution_time_ms=response.execution_time_ms,
        error=response.error
    )


@router.get(
    "/proposals",
    response_model=List[ProposalSchema],
    summary="List Optimization Proposals",
    description="Get all optimization proposals for the current user"
)
async def list_proposals(
    portfolio_id: Optional[int] = Query(None, description="Filter by portfolio"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    current_user: User = Depends(get_current_user)
):
    """
    List all optimization proposals for the current user.
    
    Can be filtered by portfolio ID and/or status.
    """
    user_proposals = [
        p for p in _proposals.values()
        if p.get('user_id') == str(current_user.id)
    ]
    
    if portfolio_id:
        user_proposals = [p for p in user_proposals if p['portfolio_id'] == str(portfolio_id)]
    
    if status_filter:
        user_proposals = [p for p in user_proposals if p['status'] == status_filter]
    
    # Sort by created_at descending
    user_proposals.sort(key=lambda x: x['created_at'], reverse=True)
    
    return [ProposalSchema(**p) for p in user_proposals]


@router.get(
    "/proposals/{proposal_id}",
    response_model=ProposalSchema,
    summary="Get Proposal Details",
    description="Get detailed information about a specific proposal"
)
async def get_proposal(
    proposal_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed information about a specific optimization proposal.
    """
    proposal = _proposals.get(proposal_id)
    
    if not proposal or proposal.get('user_id') != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proposal not found"
        )
    
    return ProposalSchema(**proposal)


@router.post(
    "/proposals/{proposal_id}/action",
    response_model=ProposalSchema,
    summary="Approve or Reject Proposal",
    description="Take action on a pending proposal"
)
async def action_proposal(
    proposal_id: str,
    action: ProposalActionSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Approve or reject a pending optimization proposal.
    
    - **approve**: Mark the proposal as approved (can be executed)
    - **reject**: Reject the proposal
    
    Note: This endpoint only changes the proposal status. 
    To actually execute the trades, use the trading endpoints.
    """
    proposal = _proposals.get(proposal_id)
    
    if not proposal or proposal.get('user_id') != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proposal not found"
        )
    
    if proposal['status'] != ProposalStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Proposal is already {proposal['status']}"
        )
    
    # Check expiration
    if proposal.get('expires_at'):
        expires = datetime.fromisoformat(proposal['expires_at'])
        if datetime.now() > expires:
            proposal['status'] = ProposalStatus.EXPIRED.value
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Proposal has expired"
            )
    
    # Update status
    if action.action == "approve":
        proposal['status'] = ProposalStatus.APPROVED.value
    else:
        proposal['status'] = ProposalStatus.REJECTED.value
    
    if action.notes:
        proposal['action_notes'] = action.notes
    
    proposal['action_at'] = datetime.now().isoformat()
    
    return ProposalSchema(**proposal)


@router.delete(
    "/proposals/{proposal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Proposal",
    description="Delete an optimization proposal"
)
async def delete_proposal(
    proposal_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete an optimization proposal.
    
    Can only delete proposals that are not in 'executed' status.
    """
    proposal = _proposals.get(proposal_id)
    
    if not proposal or proposal.get('user_id') != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proposal not found"
        )
    
    if proposal['status'] == ProposalStatus.EXECUTED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete executed proposals"
        )
    
    del _proposals[proposal_id]


@router.post(
    "/rebalance-check",
    response_model=OptimizationResponseSchema,
    summary="Check Rebalancing Need",
    description="Check if portfolio needs rebalancing and generate proposal if so"
)
async def check_rebalance(
    request: RebalanceCheckSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Check if a portfolio has drifted beyond the threshold and needs rebalancing.
    
    If drift exceeds threshold, generates a rebalancing proposal.
    """
    from sqlalchemy import select
    from app.db.models.position import Position
    
    # Get portfolio
    result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == request.portfolio_id,
            Portfolio.user_id == current_user.id
        )
    )
    portfolio = result.scalar_one_or_none()
    
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    
    # Get current positions
    result = await db.execute(
        select(Position).where(
            Position.portfolio_id == portfolio.id,
            Position.quantity > 0
        )
    )
    positions = result.scalars().all()
    
    if not positions:
        return OptimizationResponseSchema(
            success=False,
            proposal=None,
            screened_count=0,
            execution_time_ms=0,
            error="No positions to rebalance"
        )
    
    # Convert to dict format
    current_positions = [
        {
            'symbol': p.symbol,
            'name': p.symbol,
            'shares': p.quantity,
            'value': float(p.quantity * p.average_cost),  # Approximate
            'sector': None
        }
        for p in positions
    ]
    
    # Check rebalancing
    optimizer = PortfolioOptimizer()
    proposal = await optimizer.generate_rebalance_proposal(
        portfolio_id=str(portfolio.id),
        current_positions=current_positions,
        rebalance_threshold=request.threshold
    )
    
    if proposal:
        proposal_data = proposal.to_dict()
        proposal_data['user_id'] = str(current_user.id)
        _proposals[proposal.id] = proposal_data
        
        return OptimizationResponseSchema(
            success=True,
            proposal=ProposalSchema(**proposal_data),
            screened_count=len(current_positions),
            execution_time_ms=0,
            error=None
        )
    else:
        return OptimizationResponseSchema(
            success=True,
            proposal=None,
            screened_count=len(current_positions),
            execution_time_ms=0,
            error="Portfolio drift within threshold, no rebalancing needed"
        )


@router.get(
    "/efficient-frontier/{portfolio_id}",
    response_model=List[EfficientFrontierPointSchema],
    summary="Get Efficient Frontier",
    description="Generate efficient frontier for a portfolio's asset universe"
)
async def get_efficient_frontier(
    portfolio_id: int,
    n_points: int = Query(30, ge=10, le=100, description="Number of frontier points"),
    symbols: Optional[str] = Query(None, description="Comma-separated symbols"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate the efficient frontier for visualization.
    
    Returns points along the frontier from minimum variance to maximum return.
    Each point includes the optimal weights at that risk/return level.
    """
    from sqlalchemy import select
    
    # Verify portfolio
    result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == current_user.id
        )
    )
    portfolio = result.scalar_one_or_none()
    
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    
    # Parse symbols
    symbol_list = symbols.split(",") if symbols else None
    
    # Get optimizer and generate frontier
    optimizer = PortfolioOptimizer()
    
    # Fetch returns
    if symbol_list:
        returns = await optimizer._fetch_returns(symbol_list)
    else:
        # Use default universe
        default_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 
                          'NVDA', 'JPM', 'V', 'JNJ', 'PG']
        returns = await optimizer._fetch_returns(default_symbols)
    
    frontier = optimizer.get_efficient_frontier(returns, n_points)
    
    return [EfficientFrontierPointSchema(**point) for point in frontier]


@router.get(
    "/methods",
    response_model=List[Dict[str, Any]],
    summary="List Optimization Methods",
    description="Get available optimization methods with descriptions"
)
async def list_methods():
    """
    List all available portfolio optimization methods with descriptions.
    """
    return [
        {
            "id": "mean_variance",
            "name": "Mean-Variance (Markowitz)",
            "description": "Classic Modern Portfolio Theory optimization. Maximizes return for given risk level.",
            "risk_profiles": ["balanced", "aggressive"],
            "requires_returns": True
        },
        {
            "id": "min_variance",
            "name": "Minimum Variance",
            "description": "Minimizes portfolio volatility. Best for conservative investors.",
            "risk_profiles": ["prudent"],
            "requires_returns": False
        },
        {
            "id": "max_sharpe",
            "name": "Maximum Sharpe Ratio",
            "description": "Maximizes risk-adjusted returns. Optimal for aggressive investors.",
            "risk_profiles": ["aggressive"],
            "requires_returns": True
        },
        {
            "id": "risk_parity",
            "name": "Risk Parity",
            "description": "Equalizes risk contribution from each asset. Good diversification.",
            "risk_profiles": ["balanced"],
            "requires_returns": False
        },
        {
            "id": "hrp",
            "name": "Hierarchical Risk Parity",
            "description": "Uses clustering for robust allocation. Handles estimation error well.",
            "risk_profiles": ["balanced", "prudent"],
            "requires_returns": False
        },
        {
            "id": "black_litterman",
            "name": "Black-Litterman",
            "description": "Combines market equilibrium with investor views. For sophisticated users.",
            "risk_profiles": ["balanced", "aggressive"],
            "requires_returns": True,
            "requires_views": True
        }
    ]


@router.get(
    "/screener/criteria",
    response_model=List[Dict[str, Any]],
    summary="List Screening Criteria",
    description="Get available screening criteria for asset selection"
)
async def list_screener_criteria():
    """
    List all available screening criteria for filtering the investment universe.
    """
    return [
        {
            "type": "momentum",
            "metrics": ["momentum_1m", "momentum_3m", "momentum_6m", "momentum_12m"],
            "description": "Price momentum over various periods"
        },
        {
            "type": "volatility",
            "metrics": ["volatility", "beta", "max_drawdown"],
            "description": "Risk and volatility measures"
        },
        {
            "type": "quality",
            "metrics": ["sharpe", "sortino", "roe", "earnings_growth"],
            "description": "Quality and profitability metrics"
        },
        {
            "type": "value",
            "metrics": ["pe_ratio", "pb_ratio"],
            "description": "Valuation multiples"
        },
        {
            "type": "dividend",
            "metrics": ["dividend_yield"],
            "description": "Income metrics"
        },
        {
            "type": "size",
            "metrics": ["market_cap"],
            "description": "Company size"
        },
        {
            "type": "liquidity",
            "metrics": ["volume"],
            "description": "Trading liquidity"
        }
    ]
