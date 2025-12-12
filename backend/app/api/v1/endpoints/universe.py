"""
Market Universe API Endpoints

Provides access to the curated market universe (~900 symbols)
with real-time quotes and market data.
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from loguru import logger

from app.db.database import get_db
from app.db.models.market_universe import MarketUniverse, MarketRegion, AssetType
from app.db.redis_client import redis_client


router = APIRouter(prefix="/universe", tags=["universe"])


# =============================================================================
# SCHEMAS
# =============================================================================

class UniverseSymbol(BaseModel):
    """Response model for a universe symbol."""
    id: int
    symbol: str
    name: Optional[str]
    asset_type: str
    region: str
    exchange: Optional[str]
    currency: str
    indices: List[str]
    sector: Optional[str]
    industry: Optional[str]
    market_cap: Optional[float]
    is_active: bool
    priority: int
    last_quote_update: Optional[datetime]
    
    class Config:
        from_attributes = True


class UniverseQuote(BaseModel):
    """Response model for a universe quote."""
    symbol: str
    name: Optional[str]
    region: str
    exchange: Optional[str]
    price: Optional[float]
    change: Optional[float]
    change_percent: Optional[float]
    volume: Optional[int]
    day_high: Optional[float]
    day_low: Optional[float]
    prev_close: Optional[float]
    timestamp: Optional[str]
    last_quote_update: Optional[datetime]


class UniverseStats(BaseModel):
    """Response model for universe statistics."""
    total_symbols: int
    active_symbols: int
    by_region: dict
    by_asset_type: dict
    updated_last_hour: int
    failed_symbols: int


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/stats", response_model=UniverseStats)
async def get_universe_stats(
    db: AsyncSession = Depends(get_db)
):
    """
    Get statistics about the market universe.
    """
    # Total and active
    total_result = await db.execute(select(func.count(MarketUniverse.id)))
    total_symbols = total_result.scalar()
    
    active_result = await db.execute(
        select(func.count(MarketUniverse.id)).where(MarketUniverse.is_active == True)
    )
    active_symbols = active_result.scalar()
    
    # By region
    region_result = await db.execute(
        select(MarketUniverse.region, func.count(MarketUniverse.id))
        .where(MarketUniverse.is_active == True)
        .group_by(MarketUniverse.region)
    )
    by_region = {str(r[0].value): r[1] for r in region_result.all()}
    
    # By asset type
    type_result = await db.execute(
        select(MarketUniverse.asset_type, func.count(MarketUniverse.id))
        .where(MarketUniverse.is_active == True)
        .group_by(MarketUniverse.asset_type)
    )
    by_asset_type = {str(t[0].value) if t[0] else "unknown": t[1] for t in type_result.all()}
    
    # Updated last hour
    from datetime import timedelta
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    updated_result = await db.execute(
        select(func.count(MarketUniverse.id))
        .where(
            and_(
                MarketUniverse.is_active == True,
                MarketUniverse.last_quote_update >= one_hour_ago
            )
        )
    )
    updated_last_hour = updated_result.scalar()
    
    # Failed symbols (consecutive_failures > 3)
    failed_result = await db.execute(
        select(func.count(MarketUniverse.id))
        .where(
            and_(
                MarketUniverse.is_active == True,
                MarketUniverse.consecutive_failures > 3
            )
        )
    )
    failed_symbols = failed_result.scalar()
    
    return UniverseStats(
        total_symbols=total_symbols,
        active_symbols=active_symbols,
        by_region=by_region,
        by_asset_type=by_asset_type,
        updated_last_hour=updated_last_hour,
        failed_symbols=failed_symbols,
    )


@router.get("/symbols", response_model=List[UniverseSymbol])
async def get_universe_symbols(
    region: Optional[str] = Query(None, description="Filter by region: US, UK, EU, ASIA"),
    exchange: Optional[str] = Query(None, description="Filter by exchange"),
    index: Optional[str] = Query(None, description="Filter by index (e.g., SP500, FTSE100)"),
    asset_type: Optional[str] = Query(None, description="Filter by asset type: stock, etf"),
    active_only: bool = Query(True, description="Only return active symbols"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of symbols in the market universe.
    """
    query = select(MarketUniverse)
    
    if active_only:
        query = query.where(MarketUniverse.is_active == True)
    
    if region:
        try:
            region_enum = MarketRegion(region.upper())
            query = query.where(MarketUniverse.region == region_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid region: {region}")
    
    if exchange:
        query = query.where(MarketUniverse.exchange == exchange.upper())
    
    if index:
        query = query.where(MarketUniverse.indices.contains([index.upper()]))
    
    if asset_type:
        try:
            type_enum = AssetType(asset_type.lower())
            query = query.where(MarketUniverse.asset_type == type_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid asset type: {asset_type}")
    
    query = query.order_by(MarketUniverse.priority.asc(), MarketUniverse.symbol.asc())
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    symbols = result.scalars().all()
    
    return [
        UniverseSymbol(
            id=s.id,
            symbol=s.symbol,
            name=s.name,
            asset_type=s.asset_type.value if s.asset_type else "stock",
            region=s.region.value,
            exchange=s.exchange,
            currency=s.currency,
            indices=s.indices or [],
            sector=s.sector,
            industry=s.industry,
            market_cap=float(s.market_cap) if s.market_cap else None,
            is_active=s.is_active,
            priority=s.priority,
            last_quote_update=s.last_quote_update,
        )
        for s in symbols
    ]


@router.get("/quotes", response_model=List[UniverseQuote])
async def get_universe_quotes(
    region: Optional[str] = Query(None, description="Filter by region: US, UK, EU, ASIA"),
    symbols: Optional[str] = Query(None, description="Comma-separated list of symbols"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """
    Get real-time quotes for universe symbols.
    Returns cached quotes from Redis.
    """
    query = select(MarketUniverse).where(MarketUniverse.is_active == True)
    
    if region:
        try:
            region_enum = MarketRegion(region.upper())
            query = query.where(MarketUniverse.region == region_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid region: {region}")
    
    if symbols:
        symbol_list = [s.strip().upper() for s in symbols.split(",")]
        query = query.where(MarketUniverse.symbol.in_(symbol_list))
    
    # Order by most recently updated first
    query = query.order_by(
        MarketUniverse.last_quote_update.desc().nullslast()
    ).limit(limit)
    
    result = await db.execute(query)
    db_symbols = result.scalars().all()
    
    quotes = []
    for sym in db_symbols:
        # Try to get from Redis cache
        cached = await redis_client.get_quote(sym.symbol)
        
        quote_data = UniverseQuote(
            symbol=sym.symbol,
            name=sym.name,
            region=sym.region.value,
            exchange=sym.exchange,
            price=cached.get("price") if cached else None,
            change=cached.get("change") if cached else None,
            change_percent=cached.get("change_percent") if cached else None,
            volume=cached.get("volume") if cached else None,
            day_high=cached.get("day_high") if cached else None,
            day_low=cached.get("day_low") if cached else None,
            prev_close=cached.get("prev_close") if cached else None,
            timestamp=cached.get("timestamp") if cached else None,
            last_quote_update=sym.last_quote_update,
        )
        quotes.append(quote_data)
    
    return quotes


@router.get("/movers", response_model=List[UniverseQuote])
async def get_market_movers(
    region: Optional[str] = Query(None, description="Filter by region"),
    direction: str = Query("gainers", regex="^(gainers|losers)$", description="gainers or losers"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Get top market movers (gainers or losers) from the universe.
    """
    query = select(MarketUniverse).where(
        and_(
            MarketUniverse.is_active == True,
            MarketUniverse.last_quote_update.isnot(None),
        )
    )
    
    if region:
        try:
            region_enum = MarketRegion(region.upper())
            query = query.where(MarketUniverse.region == region_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid region: {region}")
    
    result = await db.execute(query)
    all_symbols = result.scalars().all()
    
    # Get quotes and calculate movers
    movers = []
    for sym in all_symbols:
        cached = await redis_client.get_quote(sym.symbol)
        if cached and cached.get("change_percent") is not None:
            movers.append({
                "symbol": sym,
                "quote": cached,
                "change_percent": cached.get("change_percent", 0)
            })
    
    # Sort by change percent
    if direction == "gainers":
        movers.sort(key=lambda x: x["change_percent"] or 0, reverse=True)
    else:
        movers.sort(key=lambda x: x["change_percent"] or 0)
    
    # Take top N
    top_movers = movers[:limit]
    
    return [
        UniverseQuote(
            symbol=m["symbol"].symbol,
            name=m["symbol"].name,
            region=m["symbol"].region.value,
            exchange=m["symbol"].exchange,
            price=m["quote"].get("price"),
            change=m["quote"].get("change"),
            change_percent=m["quote"].get("change_percent"),
            volume=m["quote"].get("volume"),
            day_high=m["quote"].get("day_high"),
            day_low=m["quote"].get("prev_close"),
            prev_close=m["quote"].get("prev_close"),
            timestamp=m["quote"].get("timestamp"),
            last_quote_update=m["symbol"].last_quote_update,
        )
        for m in top_movers
    ]


@router.get("/search")
async def search_universe(
    q: str = Query(..., min_length=1, description="Search query (symbol or name)"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Search for symbols in the universe by symbol or name.
    """
    search_term = f"%{q.upper()}%"
    
    query = select(MarketUniverse).where(
        and_(
            MarketUniverse.is_active == True,
            (
                MarketUniverse.symbol.ilike(search_term) |
                MarketUniverse.name.ilike(search_term)
            )
        )
    ).order_by(
        # Exact matches first
        MarketUniverse.symbol.asc()
    ).limit(limit)
    
    result = await db.execute(query)
    symbols = result.scalars().all()
    
    return [
        {
            "symbol": s.symbol,
            "name": s.name,
            "region": s.region.value,
            "exchange": s.exchange,
            "asset_type": s.asset_type.value if s.asset_type else "stock",
        }
        for s in symbols
    ]


@router.post("/enrich")
async def trigger_symbol_enrichment(
    limit: int = Query(50, ge=1, le=200, description="Max symbols to enrich"),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger symbol enrichment (fill in missing names).
    
    This uses yfinance to fetch company names, sectors, and industries
    for symbols that don't have them yet.
    """
    from app.bot.services.universe_data_collector import enrich_symbol_names
    
    stats = await enrich_symbol_names(db, limit=limit)
    
    return {
        "message": f"Enriched {stats['updated']} symbols",
        "stats": stats,
    }


@router.post("/refresh-quotes")
async def trigger_quote_refresh(
    region: Optional[str] = Query(None, description="Filter by region: US, UK, EU, ASIA"),
    limit: int = Query(100, ge=1, le=500, description="Max symbols to refresh"),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger a quote refresh for universe symbols.
    
    This forces an immediate update of quotes for the specified region.
    """
    from app.bot.services.universe_data_collector import get_universe_collector
    
    collector = get_universe_collector()
    
    region_enum = None
    if region:
        try:
            region_enum = MarketRegion(region.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid region: {region}")
    
    stats = await collector.update_quotes_batch(
        db=db,
        region=region_enum,
        priority=None,
        limit=limit,
    )
    
    return {
        "message": f"Refreshed {stats['updated']} quotes",
        "stats": stats,
    }


@router.get("/failed")
async def get_failed_symbols(
    min_failures: int = Query(3, ge=1, description="Min consecutive failures"),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """
    Get symbols that are consistently failing to update.
    
    Useful for diagnosing data provider issues.
    """
    query = select(MarketUniverse).where(
        and_(
            MarketUniverse.is_active == True,
            MarketUniverse.consecutive_failures >= min_failures
        )
    ).order_by(
        MarketUniverse.consecutive_failures.desc()
    ).limit(limit)
    
    result = await db.execute(query)
    symbols = result.scalars().all()
    
    return [
        {
            "symbol": s.symbol,
            "name": s.name,
            "region": s.region.value,
            "exchange": s.exchange,
            "consecutive_failures": s.consecutive_failures,
            "last_error": s.last_error,
            "last_quote_update": s.last_quote_update,
        }
        for s in symbols
    ]


@router.post("/reset-failures")
async def reset_failure_counts(
    region: Optional[str] = Query(None, description="Filter by region: US, UK, EU, ASIA"),
    symbols: Optional[str] = Query(None, description="Comma-separated symbols to reset"),
    db: AsyncSession = Depends(get_db)
):
    """
    Reset consecutive_failures count for symbols.
    
    Use after fixing issues to give symbols another chance.
    """
    from sqlalchemy import update as sql_update
    
    stmt = sql_update(MarketUniverse).where(
        MarketUniverse.consecutive_failures > 0
    )
    
    if region:
        try:
            region_enum = MarketRegion(region.upper())
            stmt = stmt.where(MarketUniverse.region == region_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid region: {region}")
    
    if symbols:
        symbol_list = [s.strip().upper() for s in symbols.split(",")]
        stmt = stmt.where(MarketUniverse.symbol.in_(symbol_list))
    
    stmt = stmt.values(consecutive_failures=0, last_error=None)
    
    result = await db.execute(stmt)
    await db.commit()
    
    return {
        "message": f"Reset failures for {result.rowcount} symbols",
        "reset_count": result.rowcount,
    }


@router.post("/cleanup")
async def cleanup_universe(
    deactivate_threshold: int = Query(5, ge=1, description="Deactivate symbols with >= this many failures"),
    db: AsyncSession = Depends(get_db)
):
    """
    Cleanup the market universe:
    1. Fix known incorrect ticker symbols
    2. Deactivate delisted/problematic symbols
    3. Remove symbols that consistently fail
    
    This is a maintenance operation to keep the universe clean.
    """
    from sqlalchemy import update as sql_update, delete as sql_delete
    
    stats = {
        "fixed_tickers": 0,
        "deactivated": 0,
        "deleted_delisted": 0,
    }
    
    # Known ticker corrections (old -> new)
    ticker_fixes = {
        "BT.A.L": "BT-A.L",  # BT Group
    }
    
    # Known delisted/acquired symbols to remove
    delisted_symbols = [
        "ATVI",      # Activision - acquired by Microsoft
        "CSGN.SW",   # Credit Suisse - acquired by UBS
        "TWTR",      # Twitter - acquired by Elon Musk (now X)
        "CTVA",      # Corteva - if delisted
    ]
    
    # Fix incorrect tickers
    for old_ticker, new_ticker in ticker_fixes.items():
        stmt = sql_update(MarketUniverse).where(
            MarketUniverse.symbol == old_ticker
        ).values(
            symbol=new_ticker,
            consecutive_failures=0,
            last_error=None
        )
        result = await db.execute(stmt)
        if result.rowcount > 0:
            stats["fixed_tickers"] += result.rowcount
    
    # Delete known delisted symbols
    for symbol in delisted_symbols:
        stmt = sql_delete(MarketUniverse).where(
            MarketUniverse.symbol == symbol
        )
        result = await db.execute(stmt)
        if result.rowcount > 0:
            stats["deleted_delisted"] += result.rowcount
    
    # Deactivate symbols with too many consecutive failures
    # (they might be temporarily unavailable, so don't delete)
    stmt = sql_update(MarketUniverse).where(
        and_(
            MarketUniverse.consecutive_failures >= deactivate_threshold,
            MarketUniverse.is_active == True
        )
    ).values(
        is_active=False,
        last_error=f"Auto-deactivated: {deactivate_threshold}+ consecutive failures"
    )
    result = await db.execute(stmt)
    stats["deactivated"] = result.rowcount
    
    await db.commit()
    
    return {
        "message": "Universe cleanup completed",
        "stats": stats,
    }


@router.post("/reactivate")
async def reactivate_symbols(
    symbols: str = Query(..., description="Comma-separated symbols to reactivate"),
    db: AsyncSession = Depends(get_db)
):
    """
    Reactivate previously deactivated symbols.
    Use after fixing issues with specific symbols.
    """
    from sqlalchemy import update as sql_update
    
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    
    stmt = sql_update(MarketUniverse).where(
        MarketUniverse.symbol.in_(symbol_list)
    ).values(
        is_active=True,
        consecutive_failures=0,
        last_error=None
    )
    
    result = await db.execute(stmt)
    await db.commit()
    
    return {
        "message": f"Reactivated {result.rowcount} symbols",
        "reactivated": result.rowcount,
    }
