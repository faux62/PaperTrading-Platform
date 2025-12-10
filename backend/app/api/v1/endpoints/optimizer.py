"""
Portfolio Optimizer API Endpoints

Provides REST API for portfolio optimization:
- Request new optimization proposals
- View and manage proposals
- Accept/reject proposals
- Get efficient frontier data
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum
import uuid
import json

from app.db.database import get_db
from app.db.models.user import User
from app.db.models.portfolio import Portfolio
from app.core.security import get_current_user
from app.core.optimizer import PortfolioOptimizer, OptimizationMethod
from app.core.optimizer.optimizer import OptimizationRequest, OptimizationResponse
from app.core.optimizer.proposal import ProposalStatus, ProposalType
from app.db.redis_client import redis_client
from app.services.email_service import email_service, should_send_notification

logger = logging.getLogger(__name__)

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


# ============== Redis-based Proposal Storage ==============
# Proposals are stored in Redis for multi-worker support

PROPOSAL_PREFIX = "optimizer:proposal:"
PROPOSAL_TTL = 86400 * 7  # 7 days

async def _save_proposal(proposal_id: str, data: Dict) -> None:
    """Save proposal to Redis."""
    key = f"{PROPOSAL_PREFIX}{proposal_id}"
    await redis_client.client.setex(key, PROPOSAL_TTL, json.dumps(data, default=str))

async def _get_proposal(proposal_id: str) -> Optional[Dict]:
    """Get proposal from Redis."""
    key = f"{PROPOSAL_PREFIX}{proposal_id}"
    data = await redis_client.client.get(key)
    return json.loads(data) if data else None

async def _delete_proposal(proposal_id: str) -> None:
    """Delete proposal from Redis."""
    key = f"{PROPOSAL_PREFIX}{proposal_id}"
    await redis_client.client.delete(key)

async def _get_all_proposals() -> List[Dict]:
    """Get all proposals from Redis."""
    keys = await redis_client.client.keys(f"{PROPOSAL_PREFIX}*")
    if not keys:
        return []
    values = await redis_client.client.mget(keys)
    return [json.loads(v) for v in values if v]


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
        await _save_proposal(response.proposal.id, proposal_data)
        
        # Send email notification for new proposal
        try:
            should_send, user_email = await should_send_notification(
                db, current_user.id, "portfolio_update"
            )
            if should_send and user_email:
                # Format actions for email
                actions = []
                for alloc in response.proposal.allocations[:5]:  # Top 5 actions
                    actions.append({
                        'type': 'BUY',
                        'symbol': alloc.symbol,
                        'quantity': int(alloc.shares),
                        'price': float(alloc.current_price or 0),
                        'rationale': alloc.rationale or 'AI optimized allocation'
                    })
                
                background_tasks.add_task(
                    email_service.send_optimizer_proposal,
                    to_email=user_email,
                    portfolio_name=portfolio.name,
                    actions=actions,
                    review_url=f"http://localhost/portfolio?proposal={response.proposal.id}"
                )
        except Exception as e:
            logger.warning(f"Failed to send optimizer proposal email: {e}")
    
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
    all_proposals = await _get_all_proposals()
    user_proposals = [
        p for p in all_proposals
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
    proposal = await _get_proposal(proposal_id)
    
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
    proposal = await _get_proposal(proposal_id)
    
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
            await _save_proposal(proposal_id, proposal)
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
    
    # Save updated proposal back to Redis
    await _save_proposal(proposal_id, proposal)
    
    return ProposalSchema(**proposal)


@router.post(
    "/proposals/{proposal_id}/execute",
    response_model=Dict[str, Any],
    summary="Execute Approved Proposal",
    description="Execute an approved proposal by creating the actual trades"
)
async def execute_proposal(
    proposal_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Execute an approved optimization proposal.
    
    This will:
    1. Verify the proposal is in 'approved' status
    2. Fetch current market prices for all symbols
    3. Create buy/sell orders for each allocation
    4. Update portfolio positions
    5. Mark proposal as 'executed'
    
    Returns the list of created trades.
    """
    from sqlalchemy import select
    from app.db.models.position import Position
    from app.db.models.trade import Trade, TradeType, OrderType, TradeStatus
    from app.data_providers import orchestrator
    from decimal import Decimal
    
    proposal = await _get_proposal(proposal_id)
    
    if not proposal or proposal.get('user_id') != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proposal not found"
        )
    
    if proposal['status'] != ProposalStatus.APPROVED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Proposal must be approved first. Current status: {proposal['status']}"
        )
    
    # Get portfolio
    portfolio_id = int(proposal['portfolio_id'])
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
    
    # Get current positions
    result = await db.execute(
        select(Position).where(Position.portfolio_id == portfolio_id)
    )
    current_positions = {p.symbol: p for p in result.scalars().all()}
    
    # Fetch current market prices for all symbols in allocations
    allocations = proposal.get('allocations', [])
    symbols = [alloc['symbol'] for alloc in allocations]
    
    market_prices = {}
    try:
        quotes = await orchestrator.get_quotes(symbols)
        # quotes is a dict mapping symbol -> Quote
        logger.info(f"Fetched {len(quotes)} quotes for {len(symbols)} symbols")
        for symbol, quote in quotes.items():
            if quote and hasattr(quote, 'price') and quote.price:
                market_prices[symbol] = float(quote.price)
                logger.debug(f"Price for {symbol}: {quote.price}")
        logger.info(f"Got market prices for {len(market_prices)} symbols: {list(market_prices.keys())}")
    except Exception as e:
        logger.warning(f"Failed to fetch market prices: {e}")
    
    # Calculate total portfolio value
    cash_balance = float(portfolio.cash_balance)
    total_value = cash_balance
    for pos in current_positions.values():
        # Use market price if available, otherwise position's price
        price = market_prices.get(pos.symbol, float(pos.current_price or pos.avg_cost))
        total_value += float(pos.quantity) * price
    
    created_trades = []
    
    for alloc in allocations:
        symbol = alloc['symbol']
        target_weight = alloc['weight']
        target_value = total_value * target_weight
        
        current_pos = current_positions.get(symbol)
        current_value = 0.0
        current_qty = 0.0
        
        # Get current market price (priority: market_prices > position > allocation fallback)
        current_price = market_prices.get(symbol, 0)
        
        if current_price <= 0:
            # Fallback to position's price
            if current_pos:
                if current_pos.current_price and float(current_pos.current_price) > 0:
                    current_price = float(current_pos.current_price)
                elif current_pos.avg_cost and float(current_pos.avg_cost) > 0:
                    current_price = float(current_pos.avg_cost)
        
        if current_price <= 0:
            # Last resort: calculate from allocation data (value / shares)
            alloc_value = float(alloc.get('value', 0))
            alloc_shares = float(alloc.get('shares', 0))
            if alloc_shares > 0 and alloc_value > 0:
                current_price = alloc_value / alloc_shares
        
        if current_price <= 0:
            # Skip if still no valid price
            logger.warning(f"No valid price for {symbol}, skipping")
            continue
        
        if current_pos:
            current_qty = float(current_pos.quantity)
            current_value = current_qty * current_price
        
        # Calculate difference
        value_diff = target_value - current_value
        
        # Skip small changes (less than $50 or 1%)
        if abs(value_diff) < 50 or abs(value_diff / total_value) < 0.01:
            continue
        
        # Determine trade type and quantity
        if value_diff > 0:
            # BUY
            trade_type = TradeType.BUY
            quantity = int(value_diff / current_price)
            if quantity < 1:
                continue
            trade_value = quantity * current_price
            
            # Check if we have enough cash
            if trade_value > cash_balance:
                quantity = int(cash_balance / current_price)
                if quantity < 1:
                    continue
                trade_value = quantity * current_price
        else:
            # SELL
            trade_type = TradeType.SELL
            quantity = min(int(abs(value_diff) / current_price), int(current_qty))
            if quantity < 1:
                continue
            trade_value = quantity * current_price
        
        # Create trade with EXECUTED status
        trade = Trade(
            portfolio_id=portfolio_id,
            symbol=symbol,
            trade_type=trade_type,
            order_type=OrderType.MARKET,
            status=TradeStatus.EXECUTED,
            quantity=Decimal(str(quantity)),
            price=Decimal(str(current_price)),
            executed_price=Decimal(str(current_price)),
            executed_quantity=Decimal(str(quantity)),
            total_value=Decimal(str(trade_value)),
            executed_at=datetime.now(),
            notes=f"AI Optimizer proposal {proposal_id[:8]}"
        )
        db.add(trade)
        
        # Update or create position
        if trade_type == TradeType.BUY:
            if current_pos:
                # Update existing position
                new_qty = float(current_pos.quantity) + quantity
                new_cost = ((float(current_pos.quantity) * float(current_pos.avg_cost)) + trade_value) / new_qty
                current_pos.quantity = Decimal(str(new_qty))
                current_pos.avg_cost = Decimal(str(new_cost))
                current_pos.current_price = Decimal(str(current_price))
                current_pos.market_value = Decimal(str(new_qty * current_price))
            else:
                # Create new position
                new_position = Position(
                    portfolio_id=portfolio_id,
                    symbol=symbol,
                    quantity=Decimal(str(quantity)),
                    avg_cost=Decimal(str(current_price)),
                    current_price=Decimal(str(current_price)),
                    market_value=Decimal(str(trade_value)),
                    unrealized_pnl=Decimal('0'),
                    unrealized_pnl_percent=Decimal('0')
                )
                db.add(new_position)
                current_positions[symbol] = new_position
            
            # Reduce cash
            cash_balance -= trade_value
        else:
            # SELL - update position
            if current_pos:
                new_qty = float(current_pos.quantity) - quantity
                if new_qty <= 0:
                    # Remove position
                    await db.delete(current_pos)
                    del current_positions[symbol]
                else:
                    current_pos.quantity = Decimal(str(new_qty))
                    current_pos.market_value = Decimal(str(new_qty * current_price))
            
            # Add cash
            cash_balance += trade_value
        
        created_trades.append({
            'symbol': symbol,
            'trade_type': trade_type.value,
            'quantity': quantity,
            'price': current_price,
            'estimated_value': trade_value
        })
    
    # Update portfolio cash balance
    portfolio.cash_balance = Decimal(str(cash_balance))
    
    # Mark proposal as executed
    proposal['status'] = ProposalStatus.EXECUTED.value
    proposal['executed_at'] = datetime.now().isoformat()
    proposal['trades_created'] = len(created_trades)
    
    # Save updated proposal to Redis
    await _save_proposal(proposal_id, proposal)
    
    await db.commit()
    
    # Send email notification for executed trades
    try:
        should_send, user_email = await should_send_notification(
            db, current_user.id, "trade_execution"
        )
        if should_send and user_email and created_trades:
            # Send summary of executed trades
            for trade_info in created_trades[:3]:  # First 3 trades
                await email_service.send_trade_notification(
                    to_email=user_email,
                    symbol=trade_info['symbol'],
                    trade_type=trade_info['trade_type'],
                    quantity=trade_info['quantity'],
                    price=trade_info['price'],
                    total_value=trade_info['estimated_value'],
                    portfolio_name=portfolio.name,
                    executed_at=datetime.now(),
                )
    except Exception as e:
        logger.warning(f"Failed to send trade execution emails: {e}")
    
    return {
        'success': True,
        'proposal_id': proposal_id,
        'trades_created': created_trades,
        'total_trades': len(created_trades),
        'message': f"Created {len(created_trades)} trades from proposal"
    }


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
    proposal = await _get_proposal(proposal_id)
    
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
    
    await _delete_proposal(proposal_id)


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
        await _save_proposal(proposal.id, proposal_data)
        
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
