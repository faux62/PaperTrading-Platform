"""
Position Analytics Service

Provides analytical and audit functions for positions, including
historical cost calculations using FX rates from TRADES table.

These functions are useful for:
- Audit trail: Calculating what was actually paid in portfolio currency
- Historical analysis: Understanding entry FX rates
- Tax reporting: Determining cost basis with historical rates
"""
from decimal import Decimal
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from loguru import logger

from app.db.models.trade import Trade, TradeType, TradeStatus


async def get_historical_cost_in_portfolio_currency(
    db: AsyncSession,
    portfolio_id: int,
    symbol: str,
) -> Decimal:
    """
    Calculate the effective cost paid in portfolio currency
    using the historical FX rates saved in TRADES.
    
    This reflects what was ACTUALLY paid at the time of purchase,
    useful for audit and historical analysis.
    
    Args:
        db: Database session
        portfolio_id: Portfolio ID
        symbol: Stock symbol
        
    Returns:
        Average cost per share in portfolio currency (using historical rates)
    """
    result = await db.execute(
        select(Trade).where(
            and_(
                Trade.portfolio_id == portfolio_id,
                Trade.symbol == symbol.upper(),
                Trade.trade_type == TradeType.BUY,
                Trade.status == TradeStatus.EXECUTED,
            )
        )
    )
    trades = result.scalars().all()
    
    if not trades:
        return Decimal("0")
    
    # Sum of (price × quantity × exchange_rate) for all buys
    total_cost_portfolio = sum(
        (t.executed_price or Decimal("0")) 
        * (t.executed_quantity or Decimal("0")) 
        * (t.exchange_rate or Decimal("1"))
        for t in trades
    )
    
    # Total quantity bought
    total_qty = sum(t.executed_quantity or Decimal("0") for t in trades)
    
    if total_qty <= 0:
        return Decimal("0")
    
    avg_cost = total_cost_portfolio / total_qty
    logger.debug(f"Historical avg cost for {symbol}: {avg_cost} (portfolio currency)")
    
    return avg_cost


async def get_avg_entry_exchange_rate(
    db: AsyncSession,
    portfolio_id: int,
    symbol: str,
) -> Decimal:
    """
    Calculate the weighted average entry exchange rate for a position.
    
    Weighted by quantity: larger purchases have more weight.
    
    Args:
        db: Database session
        portfolio_id: Portfolio ID
        symbol: Stock symbol
        
    Returns:
        Weighted average FX rate at entry (defaults to 1.0 if no trades)
    """
    result = await db.execute(
        select(Trade).where(
            and_(
                Trade.portfolio_id == portfolio_id,
                Trade.symbol == symbol.upper(),
                Trade.trade_type == TradeType.BUY,
                Trade.status == TradeStatus.EXECUTED,
            )
        )
    )
    trades = result.scalars().all()
    
    if not trades:
        return Decimal("1.0")
    
    # Sum of (quantity × exchange_rate) for weighted average
    weighted_rate = sum(
        (t.executed_quantity or Decimal("0")) * (t.exchange_rate or Decimal("1"))
        for t in trades
    )
    
    total_qty = sum(t.executed_quantity or Decimal("0") for t in trades)
    
    if total_qty <= 0:
        return Decimal("1.0")
    
    avg_rate = weighted_rate / total_qty
    logger.debug(f"Avg entry FX rate for {symbol}: {avg_rate}")
    
    return avg_rate


async def get_position_cost_breakdown(
    db: AsyncSession,
    portfolio_id: int,
    symbol: str,
) -> dict:
    """
    Get a detailed breakdown of position costs for analysis.
    
    Returns both native currency and portfolio currency values
    using historical FX rates.
    
    Args:
        db: Database session
        portfolio_id: Portfolio ID
        symbol: Stock symbol
        
    Returns:
        Dictionary with cost breakdown:
        - total_quantity: Total shares owned
        - avg_cost_native: Average cost in native currency
        - avg_cost_portfolio: Average cost in portfolio currency (historical)
        - avg_entry_fx_rate: Weighted average FX rate at entry
        - total_cost_native: Total cost in native currency
        - total_cost_portfolio: Total cost in portfolio currency
        - trades_count: Number of BUY trades
    """
    result = await db.execute(
        select(Trade).where(
            and_(
                Trade.portfolio_id == portfolio_id,
                Trade.symbol == symbol.upper(),
                Trade.trade_type == TradeType.BUY,
                Trade.status == TradeStatus.EXECUTED,
            )
        ).order_by(Trade.executed_at)
    )
    trades = result.scalars().all()
    
    if not trades:
        return {
            "symbol": symbol.upper(),
            "total_quantity": Decimal("0"),
            "avg_cost_native": Decimal("0"),
            "avg_cost_portfolio": Decimal("0"),
            "avg_entry_fx_rate": Decimal("1.0"),
            "total_cost_native": Decimal("0"),
            "total_cost_portfolio": Decimal("0"),
            "trades_count": 0,
            "native_currency": None,
        }
    
    total_qty = sum(t.executed_quantity or Decimal("0") for t in trades)
    
    total_cost_native = sum(
        (t.executed_price or Decimal("0")) * (t.executed_quantity or Decimal("0"))
        for t in trades
    )
    
    total_cost_portfolio = sum(
        (t.executed_price or Decimal("0"))
        * (t.executed_quantity or Decimal("0"))
        * (t.exchange_rate or Decimal("1"))
        for t in trades
    )
    
    weighted_fx = sum(
        (t.executed_quantity or Decimal("0")) * (t.exchange_rate or Decimal("1"))
        for t in trades
    )
    
    avg_cost_native = total_cost_native / total_qty if total_qty > 0 else Decimal("0")
    avg_cost_portfolio = total_cost_portfolio / total_qty if total_qty > 0 else Decimal("0")
    avg_entry_fx_rate = weighted_fx / total_qty if total_qty > 0 else Decimal("1.0")
    
    return {
        "symbol": symbol.upper(),
        "total_quantity": total_qty,
        "avg_cost_native": avg_cost_native,
        "avg_cost_portfolio": avg_cost_portfolio,
        "avg_entry_fx_rate": avg_entry_fx_rate,
        "total_cost_native": total_cost_native,
        "total_cost_portfolio": total_cost_portfolio,
        "trades_count": len(trades),
        "native_currency": trades[0].native_currency if trades else None,
    }


async def calculate_forex_impact(
    db: AsyncSession,
    portfolio_id: int,
    symbol: str,
    current_fx_rate: Decimal,
) -> dict:
    """
    Calculate the forex impact on a position.
    
    Compares what the position would be worth with entry FX rate
    vs current FX rate, to isolate forex gains/losses.
    
    Args:
        db: Database session
        portfolio_id: Portfolio ID
        symbol: Stock symbol
        current_fx_rate: Current exchange rate (native -> portfolio)
        
    Returns:
        Dictionary with forex impact analysis:
        - avg_entry_fx_rate: Historical weighted average rate
        - current_fx_rate: Current rate provided
        - fx_change_percent: Percentage change in FX
        - fx_impact_per_share: Impact per share in portfolio currency
        - total_fx_impact: Total forex impact on position
    """
    breakdown = await get_position_cost_breakdown(db, portfolio_id, symbol)
    
    if breakdown["total_quantity"] <= 0:
        return {
            "symbol": symbol.upper(),
            "avg_entry_fx_rate": Decimal("1.0"),
            "current_fx_rate": current_fx_rate,
            "fx_change_percent": Decimal("0"),
            "fx_impact_per_share": Decimal("0"),
            "total_fx_impact": Decimal("0"),
        }
    
    entry_rate = breakdown["avg_entry_fx_rate"]
    qty = breakdown["total_quantity"]
    avg_cost_native = breakdown["avg_cost_native"]
    
    # FX change percentage
    fx_change_pct = ((current_fx_rate - entry_rate) / entry_rate * 100) if entry_rate > 0 else Decimal("0")
    
    # Impact per share = avg_cost_native × (current_rate - entry_rate)
    fx_impact_per_share = avg_cost_native * (current_fx_rate - entry_rate)
    
    # Total impact = impact_per_share × quantity
    total_fx_impact = fx_impact_per_share * qty
    
    return {
        "symbol": symbol.upper(),
        "avg_entry_fx_rate": entry_rate,
        "current_fx_rate": current_fx_rate,
        "fx_change_percent": fx_change_pct,
        "fx_impact_per_share": fx_impact_per_share,
        "total_fx_impact": total_fx_impact,
    }
