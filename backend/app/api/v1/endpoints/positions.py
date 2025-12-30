"""
PaperTrading Platform - Position Endpoints

API endpoints for managing stock positions within portfolios.
"""
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

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


@router.get("/portfolio/{portfolio_id}/daily-stats")
async def get_portfolio_daily_stats(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get portfolio daily change statistics.
    
    Returns:
    - daily_change: $ change today (from prev_close to current)
    - daily_change_pct: % change today
    - overnight_change: $ change from yesterday close to today open
    - overnight_change_pct: % overnight change
    
    Uses prev_close from real-time quotes when available.
    """
    from app.data_providers import orchestrator
    from app.data_providers.adapters.base import MarketType
    from app.services.historical_data_collector import get_market_type_from_symbol
    
    await verify_portfolio_ownership(portfolio_id, current_user.id, db)
    
    repo = PositionRepository(db)
    positions = await repo.get_all_by_portfolio(portfolio_id)
    
    if not positions:
        return {
            "portfolio_id": portfolio_id,
            "daily_change": 0.0,
            "daily_change_pct": 0.0,
            "overnight_change": 0.0,
            "overnight_change_pct": 0.0,
            "positions_with_data": 0,
            "total_positions": 0,
        }
    
    # Group symbols by market type
    symbols_by_market: dict[MarketType, list[str]] = {}
    for pos in positions:
        market_type = get_market_type_from_symbol(pos.symbol)
        if market_type not in symbols_by_market:
            symbols_by_market[market_type] = []
        symbols_by_market[market_type].append(pos.symbol)
    
    # Fetch quotes per market type
    quotes_dict: dict[str, any] = {}
    for market_type, symbols in symbols_by_market.items():
        try:
            logger.debug(f"Fetching {len(symbols)} quotes for market {market_type.value}")
            market_quotes = await orchestrator.get_quotes(symbols, market_type=market_type)
            # get_quotes returns dict[str, Quote]
            quotes_dict.update(market_quotes)
        except Exception as e:
            logger.warning(f"Failed to fetch quotes for {market_type.value}: {e}")
    
    # Calculate daily changes
    total_daily_change = Decimal("0")
    total_prev_close_value = Decimal("0")
    positions_with_data = 0
    
    logger.debug(f"Daily stats: got {len(quotes_dict)} quotes for {len(positions)} positions")
    
    for pos in positions:
        quote = quotes_dict.get(pos.symbol)
        
        if quote:
            logger.debug(f"Quote for {pos.symbol}: price={quote.price}, prev_close={quote.prev_close}")
        else:
            logger.debug(f"No quote found for {pos.symbol}")
        
        if quote and quote.prev_close and quote.prev_close > 0:
            # Calculate position's daily change in native currency
            # daily_change = (current_price - prev_close) × quantity
            prev_close = Decimal(str(quote.prev_close))
            current = pos.current_price
            
            pos_daily_change = (current - prev_close) * pos.quantity
            pos_prev_value = prev_close * pos.quantity
            
            # Apply FX conversion to portfolio currency
            native_currency = pos.native_currency or "USD"
            from sqlalchemy import select as sql_select
            from app.db.models.portfolio import Portfolio
            
            result = await db.execute(
                sql_select(Portfolio.currency).where(Portfolio.id == portfolio_id)
            )
            portfolio_currency = result.scalar() or "EUR"
            
            fx_rate = Decimal("1.0")
            if native_currency != portfolio_currency:
                from app.utils.currency import get_exchange_rate
                fx_rate = await get_exchange_rate(native_currency, portfolio_currency)
            
            total_daily_change += pos_daily_change * fx_rate
            total_prev_close_value += pos_prev_value * fx_rate
            positions_with_data += 1
    
    # Calculate percentages
    daily_change_pct = Decimal("0")
    if total_prev_close_value > 0:
        daily_change_pct = (total_daily_change / total_prev_close_value) * 100
    
    return {
        "portfolio_id": portfolio_id,
        "daily_change": float(total_daily_change),
        "daily_change_pct": float(daily_change_pct),
        "overnight_change": 0.0,  # TODO: Requires storing yesterday's close
        "overnight_change_pct": 0.0,
        "positions_with_data": positions_with_data,
        "total_positions": len(positions),
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
