"""
PaperTrading Platform - Position Endpoints

API endpoints for managing stock positions within portfolios.

ARCHITECTURE NOTE:
- Positions are stored in DB with TRADE-DRIVEN data only
- Market values (market_value, unrealized_pnl) are COMPUTED AT RUNTIME
- Uses PositionCalculator for real-time calculations with fresh FX rates
"""
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.core.security import get_current_user
from app.db.models.user import User
from app.db.models.portfolio import Portfolio
from app.db.repositories.position import PositionRepository
from app.core.portfolio.service import PortfolioService
from app.services.position_calculator import PositionCalculator, create_calculator


router = APIRouter()


# ==================== Pydantic Schemas ====================

class PositionResponse(BaseModel):
    """Position response schema."""
    id: int
    portfolio_id: int
    symbol: str
    exchange: Optional[str]
    quantity: float
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    native_currency: Optional[str] = "USD"  # Currency the symbol is quoted in
    avg_cost_portfolio: Optional[float] = None  # Average cost in portfolio currency
    entry_exchange_rate: Optional[float] = None  # FX rate at entry
    opened_at: Optional[str]
    updated_at: Optional[str]
    
    class Config:
        from_attributes = True


class UpdatePriceRequest(BaseModel):
    """Request to update position price."""
    current_price: float = Field(..., gt=0)


class UpdatePricesRequest(BaseModel):
    """Request to update multiple position prices."""
    prices: dict[str, float]  # symbol -> price


# ==================== Helper Functions ====================

async def verify_portfolio_ownership(
    portfolio_id: int,
    user_id: int,
    db: AsyncSession,
) -> None:
    """Verify user owns the portfolio."""
    service = PortfolioService(db)
    portfolio = await service.get_portfolio(portfolio_id)
    
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    if portfolio.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this portfolio"
        )


def position_to_dict(position) -> dict:
    """Convert position model to dict with DB values (legacy support)."""
    return {
        "id": position.id,
        "portfolio_id": position.portfolio_id,
        "symbol": position.symbol,
        "exchange": position.exchange,
        "quantity": float(position.quantity),
        "avg_cost": float(position.avg_cost),
        "avg_cost_portfolio": float(position.avg_cost_portfolio) if position.avg_cost_portfolio else None,
        "entry_exchange_rate": float(position.entry_exchange_rate) if position.entry_exchange_rate else None,
        "native_currency": position.native_currency or "USD",
        "current_price": float(position.current_price) if position.current_price else 0,
        "market_value": float(position.market_value) if position.market_value else 0,
        "unrealized_pnl": float(position.unrealized_pnl) if position.unrealized_pnl else 0,
        "unrealized_pnl_percent": float(position.unrealized_pnl_percent) if position.unrealized_pnl_percent else 0,
        "opened_at": position.opened_at.isoformat() if position.opened_at else None,
        "updated_at": position.updated_at.isoformat() if position.updated_at else None,
    }


async def get_portfolio_currency(portfolio_id: int, db: AsyncSession) -> str:
    """Get the base currency of a portfolio."""
    result = await db.execute(
        select(Portfolio.currency).where(Portfolio.id == portfolio_id)
    )
    currency = result.scalar_one_or_none()
    return currency or "EUR"


# ==================== Endpoints ====================

@router.get("/portfolio/{portfolio_id}")
async def get_portfolio_positions(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all positions for a portfolio with REAL-TIME computed values.
    
    Returns list of positions with:
    - Trade-driven data from DB (quantity, avg_cost, avg_cost_portfolio)
    - Market-driven data computed at runtime (market_value, unrealized_pnl)
    - Fresh FX rates applied for currency conversion
    """
    await verify_portfolio_ownership(portfolio_id, current_user.id, db)
    
    # Get portfolio currency for calculations
    portfolio_currency = await get_portfolio_currency(portfolio_id, db)
    
    # Get positions from DB
    repo = PositionRepository(db)
    positions = await repo.get_all_by_portfolio(portfolio_id)
    
    if not positions:
        return {
            "portfolio_id": portfolio_id,
            "portfolio_currency": portfolio_currency,
            "positions": [],
            "count": 0,
            "total_market_value": 0,
            "total_unrealized_pnl": 0,
        }
    
    # Compute values at runtime using fresh prices and FX rates
    calculator = create_calculator(portfolio_currency)
    summary = await calculator.compute_portfolio_summary(positions)
    
    return {
        "portfolio_id": portfolio_id,
        "portfolio_currency": portfolio_currency,
        "positions": summary["positions"],
        "count": summary["position_count"],
        "total_market_value": summary["total_market_value"],
        "total_unrealized_pnl": summary["total_unrealized_pnl"],
        "total_unrealized_pnl_pct": summary["total_unrealized_pnl_pct"],
    }


@router.get("/portfolio/{portfolio_id}/{symbol}")
async def get_position_by_symbol(
    portfolio_id: int,
    symbol: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific position by symbol.
    """
    await verify_portfolio_ownership(portfolio_id, current_user.id, db)
    
    repo = PositionRepository(db)
    position = await repo.get_by_symbol(portfolio_id, symbol)
    
    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Position for {symbol} not found"
        )
    
    return position_to_dict(position)


@router.get("/{position_id}")
async def get_position(
    position_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get position by ID.
    """
    repo = PositionRepository(db)
    position = await repo.get_by_id(position_id)
    
    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Position not found"
        )
    
    # Verify ownership
    await verify_portfolio_ownership(position.portfolio_id, current_user.id, db)
    
    return position_to_dict(position)


@router.put("/{position_id}/price")
async def update_position_price(
    position_id: int,
    data: UpdatePriceRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update position with current market price.
    
    Recalculates market value and unrealized P&L.
    """
    repo = PositionRepository(db)
    position = await repo.get_by_id(position_id)
    
    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Position not found"
        )
    
    # Verify ownership
    await verify_portfolio_ownership(position.portfolio_id, current_user.id, db)
    
    updated = await repo.update(
        position_id=position_id,
        current_price=Decimal(str(data.current_price)),
    )
    
    return position_to_dict(updated)


@router.put("/portfolio/{portfolio_id}/prices")
async def update_portfolio_prices(
    portfolio_id: int,
    data: UpdatePricesRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update prices for multiple positions at once.
    
    Useful for batch price updates from market data.
    """
    await verify_portfolio_ownership(portfolio_id, current_user.id, db)
    
    repo = PositionRepository(db)
    
    # Convert prices to Decimal
    prices = {
        symbol: Decimal(str(price))
        for symbol, price in data.prices.items()
    }
    
    updated_count = await repo.update_prices(portfolio_id, prices)
    
    # Return updated positions
    positions = await repo.get_all_by_portfolio(portfolio_id)
    
    return {
        "updated_count": updated_count,
        "positions": [position_to_dict(p) for p in positions],
    }


@router.get("/portfolio/{portfolio_id}/summary")
async def get_positions_summary(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get positions summary with allocation percentages.
    """
    await verify_portfolio_ownership(portfolio_id, current_user.id, db)
    
    service = PortfolioService(db)
    values = await service.calculate_portfolio_value(portfolio_id)
    
    repo = PositionRepository(db)
    positions = await repo.get_all_by_portfolio(portfolio_id)
    
    total_value = values.get("total_value", Decimal("0"))
    
    # Calculate allocations
    position_summaries = []
    for pos in positions:
        weight = (
            float(pos.market_value / total_value * 100) if total_value > 0 
            else 0
        )
        position_summaries.append({
            "symbol": pos.symbol,
            "quantity": float(pos.quantity),
            "market_value": float(pos.market_value),
            "weight_percent": round(weight, 2),
            "unrealized_pnl": float(pos.unrealized_pnl),
            "unrealized_pnl_percent": float(pos.unrealized_pnl_percent),
        })
    
    # Sort by weight
    position_summaries.sort(key=lambda x: x["weight_percent"], reverse=True)
    
    return {
        "portfolio_id": portfolio_id,
        "total_value": float(total_value),
        "equity_value": float(values.get("equity_value", 0)),
        "cash_balance": float(values.get("cash_balance", 0)),
        "position_count": len(positions),
        "positions": position_summaries,
    }
