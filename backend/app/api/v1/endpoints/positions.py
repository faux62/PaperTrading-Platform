"""
PaperTrading Platform - Position Endpoints

API endpoints for managing stock positions within portfolios.
"""
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.security import get_current_user
from app.db.models.user import User
from app.db.repositories.position import PositionRepository
from app.core.portfolio.service import PortfolioService


router = APIRouter()


# ==================== Pydantic Schemas ====================

class PositionResponse(BaseModel):
    """
    Position response schema.
    
    Note: avg_cost and current_price are in NATIVE CURRENCY of the stock.
    market_value and unrealized_pnl are in PORTFOLIO CURRENCY.
    """
    id: int
    portfolio_id: int
    symbol: str
    exchange: Optional[str]
    native_currency: str  # Currency the stock is quoted in (USD, EUR, GBP, JPY, etc.)
    quantity: float
    avg_cost: float  # In native currency
    current_price: float  # In native currency
    market_value: float  # In portfolio currency (converted via current FX rate)
    unrealized_pnl: float  # In portfolio currency
    unrealized_pnl_percent: float
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
    """Convert position model to dict."""
    return {
        "id": position.id,
        "portfolio_id": position.portfolio_id,
        "symbol": position.symbol,
        "exchange": position.exchange,
        "native_currency": position.native_currency or "USD",  # Currency the stock is quoted in
        "quantity": float(position.quantity),
        "avg_cost": float(position.avg_cost),
        "current_price": float(position.current_price),
        "market_value": float(position.market_value),
        "unrealized_pnl": float(position.unrealized_pnl),
        "unrealized_pnl_percent": float(position.unrealized_pnl_percent),
        "opened_at": position.opened_at.isoformat() if position.opened_at else None,
        "updated_at": position.updated_at.isoformat() if position.updated_at else None,
    }


# ==================== Endpoints ====================

@router.get("/portfolio/{portfolio_id}")
async def get_portfolio_positions(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all positions for a portfolio.
    
    Returns list of positions with current values and P&L.
    """
    await verify_portfolio_ownership(portfolio_id, current_user.id, db)
    
    repo = PositionRepository(db)
    positions = await repo.get_all_by_portfolio(portfolio_id)
    
    # Calculate totals
    total_market_value = sum(float(p.market_value) for p in positions)
    total_unrealized_pnl = sum(float(p.unrealized_pnl) for p in positions)
    
    return {
        "portfolio_id": portfolio_id,
        "positions": [position_to_dict(p) for p in positions],
        "count": len(positions),
        "total_market_value": total_market_value,
        "total_unrealized_pnl": total_unrealized_pnl,
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


@router.post("/portfolio/{portfolio_id}/refresh-prices")
async def refresh_portfolio_prices(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh prices for all positions in a portfolio.
    
    Uses GlobalPriceUpdater to fetch current prices and convert
    market_value/unrealized_pnl to portfolio currency.
    """
    from app.db.models.portfolio import Portfolio
    from sqlalchemy import select
    
    await verify_portfolio_ownership(portfolio_id, current_user.id, db)
    
    # Get portfolio
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id)
    )
    portfolio = result.scalar_one_or_none()
    
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    
    # Use GlobalPriceUpdater for proper FX conversion
    from app.bot.services.global_price_updater import GlobalPriceUpdater
    
    updater = GlobalPriceUpdater(db)
    stats = await updater.update_portfolio_prices(portfolio)
    
    await db.commit()
    
    # Return updated positions
    repo = PositionRepository(db)
    positions = await repo.get_all_by_portfolio(portfolio_id)
    
    return {
        "message": "Prices refreshed",
        "stats": stats,
        "positions": [position_to_dict(p) for p in positions],
    }


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
