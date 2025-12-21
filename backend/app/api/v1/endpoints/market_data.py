"""
PaperTrading Platform - Market Data Endpoints
Real data providers only - NO MOCK DATA
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, date, timedelta
from typing import Optional, List
from loguru import logger

from app.dependencies import get_current_active_user
from app.db.models.user import User
from app.data_providers import orchestrator, failover_manager, rate_limiter
from app.data_providers.adapters.base import MarketType, TimeFrame, ProviderError

router = APIRouter()


def _has_providers() -> bool:
    """Check if any providers are registered."""
    return len(failover_manager._providers) > 0


def _detect_market_type(symbol: str) -> MarketType:
    """
    Detect market type from symbol format.
    
    Args:
        symbol: Ticker symbol (e.g., AAPL, ENI.MI, ^GSPC, BTC-USD)
        
    Returns:
        Appropriate MarketType enum value
    """
    symbol = symbol.upper()
    
    # Index
    if symbol.startswith("^"):
        return MarketType.INDEX
    
    # Crypto
    if "-USD" in symbol or "-EUR" in symbol or "-BTC" in symbol:
        return MarketType.CRYPTO
    
    # European markets
    if any(symbol.endswith(suffix) for suffix in [".L", ".MI", ".PA", ".DE", ".AS", ".BR", ".MC", ".SW"]):
        return MarketType.EU_STOCK
    
    # Asian markets  
    if any(symbol.endswith(suffix) for suffix in [".T", ".HK", ".SS", ".SZ", ".KS", ".TW", ".SI"]):
        return MarketType.ASIA_STOCK
    
    # ETF (common US ETFs)
    etf_symbols = {"SPY", "QQQ", "IWM", "DIA", "VOO", "VTI", "GLD", "SLV", "TLT", "XLF", "XLE", "XLK"}
    if symbol in etf_symbols:
        return MarketType.ETF
    
    # Default to US stock
    return MarketType.US_STOCK


# Market indices configuration - Global coverage
MARKET_INDICES = {
    # US Indices
    "^GSPC": {"name": "S&P 500", "region": "US", "type": "index"},
    "^IXIC": {"name": "NASDAQ", "region": "US", "type": "index"},
    "^DJI": {"name": "Dow Jones", "region": "US", "type": "index"},
    "^RUT": {"name": "Russell 2000", "region": "US", "type": "index"},
    "^VIX": {"name": "VIX", "region": "US", "type": "volatility"},
    # European Indices
    "^FTSE": {"name": "FTSE 100", "region": "EU", "type": "index"},
    "^GDAXI": {"name": "DAX", "region": "EU", "type": "index"},
    "^FCHI": {"name": "CAC 40", "region": "EU", "type": "index"},
    "^STOXX50E": {"name": "Euro Stoxx 50", "region": "EU", "type": "index"},
    "FTSEMIB.MI": {"name": "FTSE MIB", "region": "EU", "type": "index"},
    # Asian Indices
    "^N225": {"name": "Nikkei 225", "region": "Asia", "type": "index"},
    "^HSI": {"name": "Hang Seng", "region": "Asia", "type": "index"},
    "000001.SS": {"name": "Shanghai", "region": "Asia", "type": "index"},
    # Crypto
    "BTC-USD": {"name": "Bitcoin", "region": "Crypto", "type": "crypto"},
    "ETH-USD": {"name": "Ethereum", "region": "Crypto", "type": "crypto"},
    # Commodities
    "GC=F": {"name": "Gold", "region": "Commodities", "type": "commodity"},
    "CL=F": {"name": "Crude Oil", "region": "Commodities", "type": "commodity"},
}


@router.get("/indices")
async def get_market_indices(
    region: Optional[str] = Query(None, description="Filter by region: US, EU, Asia, Crypto, Commodities")
):
    """
    Get major market indices - PUBLIC ENDPOINT (no auth required).
    Returns global indices organized by region.
    
    Regions: US, EU, Asia, Crypto, Commodities
    """
    # Filter indices by region if specified
    if region:
        indices_to_fetch = [k for k, v in MARKET_INDICES.items() if v["region"].lower() == region.lower()]
    else:
        # Default: main indices from each region
        indices_to_fetch = ["^GSPC", "^IXIC", "^DJI", "^FTSE", "^GDAXI", "FTSEMIB.MI", "^N225", "BTC-USD", "ETH-USD", "GC=F", "CL=F"]
    
    results = {}
    
    # Group indices by market type for batch fetching
    from collections import defaultdict
    by_market_type = defaultdict(list)
    for symbol in indices_to_fetch:
        market_type = _detect_market_type(symbol)
        by_market_type[market_type].append(symbol)
    
    # Fetch each group in batch
    for market_type, symbols in by_market_type.items():
        try:
            quotes = await orchestrator.get_quotes(
                symbols=symbols,
                market_type=market_type
            )
            
            for symbol, quote in quotes.items():
                info = MARKET_INDICES.get(symbol, {})
                results[symbol] = {
                    "symbol": symbol,
                    "name": info.get("name", quote.name or symbol),
                    "region": info.get("region", "Other"),
                    "type": info.get("type", "index"),
                    "price": float(quote.price),
                    "change": float(quote.change) if quote.change else 0,
                    "change_percent": round(float(quote.change_percent), 2) if quote.change_percent else 0,
                    "timestamp": quote.timestamp.isoformat(),
                    "source": quote.provider,
                }
        except Exception as e:
            logger.warning(f"Failed to fetch batch for {market_type}: {e}")
            # Fallback: mark failed symbols as unavailable
            for symbol in symbols:
                if symbol not in results:
                    info = MARKET_INDICES.get(symbol, {})
                    results[symbol] = {
                        "symbol": symbol,
                        "name": info.get("name", symbol),
                        "region": info.get("region", "Other"),
                        "type": info.get("type", "index"),
                        "price": 0,
                        "change": 0,
                        "change_percent": 0,
                        "timestamp": datetime.utcnow().isoformat(),
                        "source": "unavailable",
                    }
    
    return results


@router.get("/quote/{symbol}")
async def get_quote(
    symbol: str,
    force_refresh: bool = Query(False, description="Skip cache and fetch fresh data"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current quote for symbol.
    
    Automatically detects market type from symbol suffix:
    - .L = London, .MI = Milan, .PA = Paris, .DE = Frankfurt (EU)
    - .T = Tokyo, .HK = Hong Kong (Asia)
    - ^XXX = Index
    - XXX-USD = Crypto
    """
    symbol = symbol.upper()
    
    # Determine market type from symbol
    market_type = _detect_market_type(symbol)
    
    try:
        quote = await orchestrator.get_quote(
            symbol,
            market_type=market_type,
            force_refresh=force_refresh,
        )
        
        return {
            "symbol": quote.symbol,
            "name": getattr(quote, 'name', None) or symbol,
            "exchange": quote.exchange or "",
            "price": float(quote.price),
            "change": float(quote.change) if quote.change else 0,
            "change_percent": float(quote.change_percent) if quote.change_percent else 0,
            "volume": quote.volume or 0,
            "bid": float(quote.bid) if quote.bid else float(quote.price) - 0.01,
            "ask": float(quote.ask) if quote.ask else float(quote.price) + 0.01,
            "high": float(quote.day_high) if quote.day_high else float(quote.price),
            "low": float(quote.day_low) if quote.day_low else float(quote.price),
            "open": float(quote.day_open) if quote.day_open else float(quote.price),
            "previous_close": float(quote.prev_close) if quote.prev_close else float(quote.price),
            "timestamp": quote.timestamp.isoformat(),
            "source": quote.provider,
        }
    except ProviderError as e:
        logger.warning(f"Provider error for {symbol}: {e}")
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found or unavailable")
    except Exception as e:
        logger.error(f"Error fetching quote for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching quote: {str(e)}")


@router.get("/quotes")
async def get_quotes(
    symbols: str = Query(..., description="Comma-separated list of symbols"),
    force_refresh: bool = Query(False, description="Skip cache"),
    current_user: User = Depends(get_current_active_user)
):
    """Get quotes for multiple symbols (comma-separated)."""
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    quotes = []
    errors = []
    
    # Group symbols by market type for efficient batch fetching
    from collections import defaultdict
    by_market_type = defaultdict(list)
    for sym in symbol_list:
        market_type = _detect_market_type(sym)
        by_market_type[market_type].append(sym)
    
    # Fetch each group in batch
    for market_type, syms in by_market_type.items():
        try:
            batch_quotes = await orchestrator.get_quotes(
                symbols=syms,
                market_type=market_type,
                force_refresh=force_refresh,
            )
            
            for sym, quote in batch_quotes.items():
                quotes.append({
                    "symbol": quote.symbol,
                    "name": getattr(quote, 'name', None) or sym,
                    "exchange": quote.exchange or "",
                    "price": float(quote.price),
                    "change": float(quote.change) if quote.change else 0,
                    "change_percent": float(quote.change_percent) if quote.change_percent else 0,
                    "volume": quote.volume or 0,
                    "timestamp": quote.timestamp.isoformat(),
                    "source": quote.provider,
                })
            
            # Check for missing symbols in this batch
            for sym in syms:
                if sym not in batch_quotes:
                    errors.append({"symbol": sym, "error": "Not found"})
                    
        except Exception as e:
            logger.warning(f"Batch fetch failed for {market_type}: {e}")
            # Mark all symbols in failed batch as errors
            for sym in syms:
                errors.append({"symbol": sym, "error": str(e)})
    
    return {"quotes": quotes, "count": len(quotes), "errors": errors}


@router.get("/history/{symbol}")
async def get_history(
    symbol: str,
    period: str = Query("1M", description="Period: 1D, 1W, 1M, 3M, 1Y"),
    timeframe: str = Query("auto", description="Timeframe: auto, 1m, 5m, 15m, 1h, 1d"),
):
    """Get historical OHLCV data. PUBLIC endpoint."""
    symbol = symbol.upper()
    market_type = _detect_market_type(symbol)
    
    # Period mapping to days
    period_days = {
        "1D": 1,
        "1W": 7,
        "1M": 30,
        "3M": 90,
        "1Y": 365,
        "5Y": 1825,
    }
    days = period_days.get(period.upper(), 30)
    
    # Timeframe/interval mapping
    timeframe_map = {
        "1D": "5m",    # 1 day of 5-min bars
        "1W": "15m",   # 5 days of 15-min bars  
        "1M": "1d",    # 1 month of daily bars
        "3M": "1d",    # 3 months of daily bars
        "1Y": "1d",    # 1 year of daily bars
        "5Y": "1wk",   # 5 years of weekly bars
    }
    interval = timeframe_map.get(period.upper(), "1d") if timeframe == "auto" else timeframe
    
    try:
        # Use orchestrator for historical data
        bars = await orchestrator.get_historical(
            symbol=symbol,
            market_type=market_type,
            days=days,
            interval=interval
        )
        
        if not bars:
            raise HTTPException(status_code=404, detail=f"No historical data for {symbol}")
        
        data = []
        for bar in bars:
            # Format date based on interval
            if interval in ["1m", "5m", "15m", "1h"]:
                date_str = bar.timestamp.strftime("%Y-%m-%d %H:%M")
            else:
                date_str = bar.timestamp.strftime("%Y-%m-%d")
            
            data.append({
                "date": date_str,
                "open": round(float(bar.open), 2),
                "high": round(float(bar.high), 2),
                "low": round(float(bar.low), 2),
                "close": round(float(bar.close), 2),
                "volume": int(bar.volume) if bar.volume else 0,
            })
        
        return {
            "symbol": symbol,
            "period": period,
            "timeframe": interval,
            "data": data,
            "source": bars[0].provider if bars else "orchestrator",
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching history for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch history: {str(e)}")


@router.get("/search")
async def search_symbols(
    query: str = Query(..., min_length=1, max_length=50, description="Search query (symbol or company name)"),
    limit: int = Query(20, ge=1, le=50, description="Max results"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Search for symbols using real market data.
    Searches by ticker symbol and company name.
    Returns symbol, name, exchange, sector, type, and current price.
    """
    query = query.strip().upper()
    results = []
    
    # First, try direct symbol lookup if query looks like a ticker
    if len(query) <= 6 and query.isalpha():
        try:
            market_type = _detect_market_type(query)
            quote = await orchestrator.get_quote(query, market_type=market_type)
            company_info = await orchestrator.get_company_info(query)
            
            if quote and quote.price:
                results.append({
                    "symbol": query,
                    "name": company_info.get("shortName") or company_info.get("longName") or getattr(quote, 'name', None) or query,
                    "exchange": quote.exchange or company_info.get("exchange", ""),
                    "sector": company_info.get("sector", ""),
                    "type": company_info.get("quoteType", "EQUITY"),
                    "price": round(float(quote.price), 2),
                    "currency": company_info.get("currency", "USD"),
                })
        except Exception as e:
            logger.debug(f"Direct lookup failed for {query}: {e}")
    
    # Use orchestrator search for broader results
    try:
        search_results = await orchestrator.search_symbols(query, limit=limit)
        
        for item in search_results:
            sym = item.get("symbol", "").upper()
            if any(r["symbol"] == sym for r in results):
                continue
            
            # Get current price for each result
            price = item.get("price")
            if not price:
                try:
                    market_type = _detect_market_type(sym)
                    quote = await orchestrator.get_quote(sym, market_type=market_type)
                    price = float(quote.price) if quote else None
                except Exception:
                    price = None
            
            results.append({
                "symbol": sym,
                "name": item.get("name", sym),
                "exchange": item.get("exchange", ""),
                "sector": item.get("sector", ""),
                "type": item.get("type", "EQUITY"),
                "price": round(float(price), 2) if price else None,
                "currency": item.get("currency", "USD"),
            })
            
            if len(results) >= limit:
                break
                
    except Exception as e:
        logger.warning(f"Search error: {e}")
    
    # If no results yet, try common variations for international stocks
    if not results and len(query) >= 2:
        for suffix in [".L", ".DE", ".PA", ".MI", ".T", ".HK"]:
            sym = f"{query}{suffix}"
            if len(results) >= limit:
                break
            try:
                market_type = _detect_market_type(sym)
                quote = await orchestrator.get_quote(sym, market_type=market_type)
                company_info = await orchestrator.get_company_info(sym)
                
                if quote and quote.price:
                    results.append({
                        "symbol": sym,
                        "name": company_info.get("shortName") or getattr(quote, 'name', None) or sym,
                        "exchange": quote.exchange or company_info.get("exchange", ""),
                        "sector": company_info.get("sector", ""),
                        "type": company_info.get("quoteType", "EQUITY"),
                        "price": round(float(quote.price), 2),
                        "currency": company_info.get("currency", "USD"),
                    })
            except Exception:
                continue
    
    return {
        "results": results[:limit],
        "count": len(results[:limit]),
        "query": query
    }


@router.get("/market-hours")
async def get_market_hours():
    """
    Get market hours status for all major exchanges - PUBLIC ENDPOINT.
    Returns current status, local time, and trading hours for each market.
    """
    from app.scheduler.market_hours import MarketHoursManager, EXCHANGE_HOURS
    
    manager = MarketHoursManager()
    markets = []
    
    # Define market groups with display names
    market_groups = {
        "US": [
            ("NYSE", "New York Stock Exchange"),
            ("NASDAQ", "NASDAQ"),
        ],
        "Europe": [
            ("LSE", "London Stock Exchange"),
            ("XETRA", "Frankfurt (XETRA)"),
            ("EURONEXT", "Euronext Paris"),
            ("BIT", "Borsa Italiana"),
            ("BME", "Bolsa de Madrid"),
            ("SIX", "Swiss Exchange"),
        ],
        "Asia": [
            ("TSE", "Tokyo Stock Exchange"),
            ("HKEX", "Hong Kong Exchange"),
            ("SSE", "Shanghai Stock Exchange"),
            ("SZSE", "Shenzhen Stock Exchange"),
            ("KRX", "Korea Exchange"),
            ("SGX", "Singapore Exchange"),
            ("ASX", "Australian Securities"),
            ("NSE", "National Stock Exchange India"),
        ],
    }
    
    for region, exchanges in market_groups.items():
        for exchange_code, display_name in exchanges:
            try:
                status = manager.get_market_status(exchange_code)
                hours = EXCHANGE_HOURS.get(exchange_code)
                
                markets.append({
                    "code": exchange_code,
                    "name": display_name,
                    "region": region,
                    "is_open": status.is_open,
                    "session": status.session.value,
                    "local_time": status.local_time.strftime("%H:%M"),
                    "timezone": hours.timezone if hours else "UTC",
                    "open_time": hours.open_time.strftime("%H:%M") if hours else None,
                    "close_time": hours.close_time.strftime("%H:%M") if hours else None,
                    "day_type": status.day_type.value,
                    "reason": status.reason,
                })
            except Exception as e:
                logger.warning(f"Could not get status for {exchange_code}: {e}")
    
    # Add Crypto (always open)
    markets.append({
        "code": "CRYPTO",
        "name": "Cryptocurrency",
        "region": "Global",
        "is_open": True,
        "session": "regular",
        "local_time": datetime.utcnow().strftime("%H:%M"),
        "timezone": "UTC",
        "open_time": "00:00",
        "close_time": "24:00",
        "day_type": "regular",
        "reason": None,
    })
    
    return {
        "markets": markets,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/providers/status")
async def get_provider_status(
    current_user: User = Depends(get_current_active_user)
):
    """Get status of all data providers including rate limit consumption."""
    providers = {}
    
    for name in failover_manager._providers.keys():
        stats = rate_limiter.get_stats(name)
        providers[name] = {
            "registered": True,
            "rate_limit": {
                "configured": stats.get("configured", False),
                "limits": stats.get("limits", {}),
                "remaining": stats.get("remaining", {}),
                "can_proceed": stats.get("can_proceed", True),
                "wait_time_seconds": stats.get("wait_time", 0),
            }
        }
    
    return {
        "providers": providers,
        "total_registered": len(providers),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/movers/gainers")
async def get_top_gainers(
    limit: int = 10,
    region: Optional[str] = Query(None, description="Filter by region: US, UK, EU, ASIA"),
):
    """
    Get top gaining stocks for the day - PUBLIC ENDPOINT.
    Uses the global market universe.
    """
    from app.db.database import async_session_maker
    from app.db.models.market_universe import MarketUniverse, MarketRegion
    from app.db.redis_client import redis_client
    from sqlalchemy import select
    
    try:
        async with async_session_maker() as db:
            query = select(MarketUniverse).where(
                MarketUniverse.is_active == True
            )
            
            if region:
                try:
                    region_enum = MarketRegion(region.upper())
                    query = query.where(MarketUniverse.region == region_enum)
                except ValueError:
                    pass
            
            query = query.order_by(
                MarketUniverse.last_quote_update.desc().nullslast()
            ).limit(300)
            
            result = await db.execute(query)
            symbols = result.scalars().all()
            
            quotes = []
            for sym in symbols:
                cached = await redis_client.get_quote(sym.symbol)
                if cached and cached.get("price"):
                    change_pct = float(cached.get("change_percent") or 0)
                    if change_pct > 0.1:  # Only show meaningful gains
                        quotes.append({
                            "symbol": sym.symbol,
                            "name": sym.name or sym.symbol,
                            "region": sym.region.value,
                            "exchange": sym.exchange,
                            "price": round(float(cached.get("price", 0)), 2),
                            "change": round(float(cached.get("change") or 0), 2),
                            "change_percent": round(change_pct, 2),
                            "volume": int(cached.get("volume") or 0),
                        })
            
            quotes.sort(key=lambda x: x['change_percent'], reverse=True)
            return {"gainers": quotes[:limit], "source": "universe"}
        
    except Exception as e:
        logger.error(f"Error fetching gainers: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching gainers: {str(e)}")


@router.get("/movers/losers")
async def get_top_losers(
    limit: int = 10,
    region: Optional[str] = Query(None, description="Filter by region: US, UK, EU, ASIA"),
):
    """
    Get top losing stocks for the day - PUBLIC ENDPOINT.
    Uses the global market universe.
    """
    from app.db.database import async_session_maker
    from app.db.models.market_universe import MarketUniverse, MarketRegion
    from app.db.redis_client import redis_client
    from sqlalchemy import select
    
    try:
        async with async_session_maker() as db:
            query = select(MarketUniverse).where(
                MarketUniverse.is_active == True
            )
            
            if region:
                try:
                    region_enum = MarketRegion(region.upper())
                    query = query.where(MarketUniverse.region == region_enum)
                except ValueError:
                    pass
            
            query = query.order_by(
                MarketUniverse.last_quote_update.desc().nullslast()
            ).limit(300)
            
            result = await db.execute(query)
            symbols = result.scalars().all()
            
            quotes = []
            for sym in symbols:
                cached = await redis_client.get_quote(sym.symbol)
                if cached and cached.get("price"):
                    change_pct = float(cached.get("change_percent") or 0)
                    if change_pct < -0.1:  # Only show meaningful losses
                        quotes.append({
                            "symbol": sym.symbol,
                            "name": sym.name or sym.symbol,
                            "region": sym.region.value,
                            "exchange": sym.exchange,
                            "price": round(float(cached.get("price", 0)), 2),
                            "change": round(float(cached.get("change") or 0), 2),
                            "change_percent": round(change_pct, 2),
                            "volume": int(cached.get("volume") or 0),
                        })
            
            # Sort by change_percent ascending (most negative first)
            quotes.sort(key=lambda x: x['change_percent'])
            return {"losers": quotes[:limit], "source": "universe"}
        
    except Exception as e:
        logger.error(f"Error fetching losers: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching losers: {str(e)}")


@router.get("/movers/most-active")
async def get_most_active(
    limit: int = 10,
    region: Optional[str] = Query(None, description="Filter by region: US, UK, EU, ASIA"),
):
    """
    Get most actively traded stocks by volume - PUBLIC ENDPOINT.
    Uses the global market universe, not just US stocks.
    """
    from app.db.database import async_session_maker
    from app.db.models.market_universe import MarketUniverse, MarketRegion
    from app.db.redis_client import redis_client
    from sqlalchemy import select, desc
    
    try:
        async with async_session_maker() as db:
            # Query active symbols from universe
            query = select(MarketUniverse).where(
                MarketUniverse.is_active == True
            )
            
            if region:
                try:
                    region_enum = MarketRegion(region.upper())
                    query = query.where(MarketUniverse.region == region_enum)
                except ValueError:
                    pass
            
            # Order by recent updates (symbols with fresh data)
            query = query.order_by(
                MarketUniverse.last_quote_update.desc().nullslast()
            ).limit(200)  # Get more to filter by volume
            
            result = await db.execute(query)
            symbols = result.scalars().all()
            
            quotes = []
            for sym in symbols:
                # Get cached quote from Redis
                cached = await redis_client.get_quote(sym.symbol)
                if cached and cached.get("volume") and cached.get("price"):
                    quotes.append({
                        "symbol": sym.symbol,
                        "name": sym.name or sym.symbol,
                        "region": sym.region.value,
                        "exchange": sym.exchange,
                        "price": round(float(cached.get("price", 0)), 2),
                        "change": round(float(cached.get("change") or 0), 2),
                        "change_percent": round(float(cached.get("change_percent") or 0), 2),
                        "volume": int(cached.get("volume", 0)),
                    })
            
            # Sort by volume descending
            quotes.sort(key=lambda x: x['volume'], reverse=True)
            return {"most_active": quotes[:limit], "source": "universe"}
        
    except Exception as e:
        logger.error(f"Error fetching most active: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching most active: {str(e)}")


@router.get("/movers/trending")
async def get_trending(
    limit: int = 10,
    region: Optional[str] = Query(None, description="Filter by region: US, UK, EU, ASIA"),
):
    """
    Get trending stocks based on high volume and price movement - PUBLIC ENDPOINT.
    Uses the global market universe.
    """
    from app.db.database import async_session_maker
    from app.db.models.market_universe import MarketUniverse, MarketRegion
    from app.db.redis_client import redis_client
    from sqlalchemy import select
    
    try:
        async with async_session_maker() as db:
            query = select(MarketUniverse).where(
                MarketUniverse.is_active == True
            )
            
            if region:
                try:
                    region_enum = MarketRegion(region.upper())
                    query = query.where(MarketUniverse.region == region_enum)
                except ValueError:
                    pass
            
            query = query.order_by(
                MarketUniverse.last_quote_update.desc().nullslast()
            ).limit(300)
            
            result = await db.execute(query)
            symbols = result.scalars().all()
            
            quotes = []
            for sym in symbols:
                cached = await redis_client.get_quote(sym.symbol)
                if cached and cached.get("price") and cached.get("volume"):
                    volume = int(cached.get("volume") or 0)
                    change_pct = abs(float(cached.get("change_percent") or 0))
                    
                    # Calculate trending score based on volume and movement
                    # High volume + high movement = trending
                    trending_score = (volume / 1000000) * 0.4 + change_pct * 0.6
                    
                    if volume > 100000 and change_pct > 0.5:  # Minimum thresholds
                        quotes.append({
                            "symbol": sym.symbol,
                            "name": sym.name or sym.symbol,
                            "region": sym.region.value,
                            "exchange": sym.exchange,
                            "price": round(float(cached.get("price", 0)), 2),
                            "change": round(float(cached.get("change") or 0), 2),
                            "change_percent": round(float(cached.get("change_percent") or 0), 2),
                            "volume": volume,
                            "trending_score": round(trending_score, 2),
                        })
            
            quotes.sort(key=lambda x: x['trending_score'], reverse=True)
            return {"trending": quotes[:limit], "source": "universe"}
        
    except Exception as e:
        logger.error(f"Error fetching trending: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching trending: {str(e)}")
