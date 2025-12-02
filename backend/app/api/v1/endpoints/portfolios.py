"""
PaperTrading Platform - Portfolio Endpoints

API endpoints for portfolio management including CRUD operations,
performance metrics, allocation analysis, and rebalancing.
"""
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.api.v1.endpoints.auth import get_current_user
from app.db.models.user import User
from app.core.portfolio.service import PortfolioService
from app.core.portfolio.risk_profiles import get_all_profiles, get_profile_summary


router = APIRouter()


# ==================== Pydantic Schemas ====================

class PortfolioCreate(BaseModel):
    """Schema for creating a portfolio."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    risk_profile: str = Field(default="balanced", pattern="^(aggressive|balanced|prudent)$")
    initial_capital: float = Field(default=100000, ge=1000, le=100000000)
    currency: str = Field(default="USD", pattern="^[A-Z]{3}$")


class PortfolioUpdate(BaseModel):
    """Schema for updating a portfolio."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    risk_profile: Optional[str] = Field(None, pattern="^(aggressive|balanced|prudent)$")
    is_active: Optional[str] = Field(None, pattern="^(active|archived|closed)$")


class ValidateTradeRequest(BaseModel):
    """Schema for trade validation request."""
    symbol: str
    trade_type: str = Field(..., pattern="^(buy|sell)$")
    quantity: float = Field(..., gt=0)
    price: float = Field(..., gt=0)
    sector: Optional[str] = None
    country: Optional[str] = None


# ==================== Endpoints ====================

@router.get("/risk-profiles")
async def list_risk_profiles():
    """
    Get available risk profiles with their configurations.
    
    Returns summary of each profile suitable for selection UI.
    """
    profiles = get_all_profiles()
    return {
        "profiles": [
            get_profile_summary(name)
            for name in profiles.keys()
        ]
    }


@router.get("/")
async def list_portfolios(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all portfolios for the current user.
    
    Returns lightweight summary for each portfolio.
    """
    service = PortfolioService(db)
    portfolios = await service.get_portfolios_by_user(current_user.id)
    
    summaries = []
    for portfolio in portfolios:
        summary = await service.get_portfolio_summary(portfolio.id)
        if summary:
            summaries.append(summary)
    
    return {"portfolios": summaries, "count": len(summaries)}


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    data: PortfolioCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new portfolio.
    
    Creates portfolio with specified risk profile and initial capital.
    """
    service = PortfolioService(db)
    
    portfolio = await service.create_portfolio(
        user_id=current_user.id,
        name=data.name,
        description=data.description,
        risk_profile=data.risk_profile,
        initial_capital=Decimal(str(data.initial_capital)),
        currency=data.currency,
    )
    
    return await service.get_portfolio_with_positions(portfolio.id)


@router.get("/{portfolio_id}")
async def get_portfolio(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get portfolio by ID with all positions and performance data.
    """
    service = PortfolioService(db)
    portfolio_data = await service.get_portfolio_with_positions(portfolio_id)
    
    if not portfolio_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    
    # Verify ownership
    if portfolio_data.get("user_id") != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this portfolio"
        )
    
    return portfolio_data


@router.put("/{portfolio_id}")
async def update_portfolio(
    portfolio_id: int,
    data: PortfolioUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update portfolio settings.
    
    Can update name, description, risk profile, and status.
    """
    service = PortfolioService(db)
    
    # Verify existence and ownership
    portfolio = await service.get_portfolio(portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    if portfolio.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this portfolio"
        )
    
    updated = await service.update_portfolio(
        portfolio_id=portfolio_id,
        name=data.name,
        description=data.description,
        risk_profile=data.risk_profile,
        is_active=data.is_active,
    )
    
    return await service.get_portfolio_with_positions(portfolio_id)


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a portfolio and all associated data.
    
    This action is irreversible.
    """
    service = PortfolioService(db)
    
    # Verify existence and ownership
    portfolio = await service.get_portfolio(portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    if portfolio.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this portfolio"
        )
    
    await service.delete_portfolio(portfolio_id)
    return None


@router.get("/{portfolio_id}/summary")
async def get_portfolio_summary(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get portfolio performance summary.
    
    Returns returns, P&L, and allocation breakdown.
    """
    service = PortfolioService(db)
    
    # Verify existence and ownership
    portfolio = await service.get_portfolio(portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    if portfolio.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this portfolio"
        )
    
    return await service.calculate_performance(portfolio_id)


@router.get("/{portfolio_id}/allocation")
async def get_portfolio_allocation(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get portfolio allocation analysis.
    
    Compares current allocation to risk profile targets
    and returns drift metrics.
    """
    service = PortfolioService(db)
    
    # Verify existence and ownership
    portfolio = await service.get_portfolio(portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    if portfolio.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this portfolio"
        )
    
    analysis = await service.analyze_allocation(portfolio_id)
    return analysis.to_dict()


@router.post("/{portfolio_id}/validate-trade")
async def validate_trade(
    portfolio_id: int,
    data: ValidateTradeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Validate a proposed trade against portfolio constraints.
    
    Checks position limits, sector exposure, cash requirements, etc.
    """
    service = PortfolioService(db)
    
    # Verify existence and ownership
    portfolio = await service.get_portfolio(portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    if portfolio.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this portfolio"
        )
    
    result = await service.validate_trade(
        portfolio_id=portfolio_id,
        symbol=data.symbol,
        trade_type=data.trade_type,
        quantity=Decimal(str(data.quantity)),
        price=Decimal(str(data.price)),
        sector=data.sector,
        country=data.country,
    )
    
    return result.to_dict()


@router.post("/{portfolio_id}/rebalance")
async def get_rebalance_recommendations(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get rebalancing recommendations for portfolio.
    
    Analyzes current allocation and returns recommended
    trades to bring portfolio back to target allocation.
    """
    service = PortfolioService(db)
    
    # Verify existence and ownership
    portfolio = await service.get_portfolio(portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    if portfolio.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this portfolio"
        )
    
    analysis = await service.analyze_allocation(portfolio_id)
    
    return {
        "needs_rebalancing": analysis.needs_rebalancing,
        "max_drift": float(analysis.max_drift),
        "recommendations": [r.to_dict() for r in analysis.rebalance_recommendations],
    }
