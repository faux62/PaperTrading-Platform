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
    import yfinance as yf
    
    # Filter indices by region if specified
    if region:
        indices_to_fetch = [k for k, v in MARKET_INDICES.items() if v["region"].lower() == region.lower()]
    else:
        # Default: main indices from each region
        indices_to_fetch = ["^GSPC", "^IXIC", "^DJI", "^FTSE", "^GDAXI", "FTSEMIB.MI", "^N225", "BTC-USD", "ETH-USD", "GC=F", "CL=F"]
    
    results = {}
    
    # Use yfinance directly for indices (orchestrator doesn't support them well)
    for symbol in indices_to_fetch:
        info = MARKET_INDICES.get(symbol, {})
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="2d")
            
            if not hist.empty and len(hist) >= 1:
                latest = hist.iloc[-1]
                price = float(latest["Close"])
                
                # Calculate change from previous day or open
                if len(hist) >= 2:
                    prev_close = float(hist.iloc[-2]["Close"])
                else:
                    prev_close = float(latest.get("Open", price))
                
                change = price - prev_close
                change_pct = (change / prev_close * 100) if prev_close else 0
                
                results[symbol] = {
                    "symbol": symbol,
                    "name": info.get("name", symbol),
                    "region": info.get("region", "Other"),
                    "type": info.get("type", "index"),
                    "price": price,
                    "change": change,
                    "change_percent": round(change_pct, 2),
                    "timestamp": datetime.utcnow().isoformat(),
                    "source": "yfinance",
                }
            else:
                raise ValueError("No data")
        except Exception as e:
            logger.warning(f"Failed to fetch index {symbol}: {e}")
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
    
    Uses real data providers when available, falls back to mock data.
    """
    symbol = symbol.upper()
    
    # Try real providers first
    if _has_providers():
        try:
            quote = await orchestrator.get_quote(
                symbol,
                market_type=MarketType.US_STOCK,
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
        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {e}")
    
    # Try yfinance as fallback (real data source)
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="5d")
        
        if hist.empty:
            raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
        
        latest = hist.iloc[-1]
        price = float(latest["Close"])
        prev_close = float(hist.iloc[-2]["Close"]) if len(hist) >= 2 else price
        change = price - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0
        
        # Get ticker info for name
        info = ticker.info
        
        return {
            "symbol": symbol,
            "name": info.get("shortName") or info.get("longName") or symbol,
            "exchange": info.get("exchange", ""),
            "price": round(price, 2),
            "change": round(change, 2),
            "change_percent": round(change_pct, 2),
            "volume": int(latest.get("Volume", 0)),
            "bid": round(price - 0.01, 2),
            "ask": round(price + 0.01, 2),
            "high": round(float(latest.get("High", price)), 2),
            "low": round(float(latest.get("Low", price)), 2),
            "open": round(float(latest.get("Open", price)), 2),
            "previous_close": round(prev_close, 2),
            "timestamp": datetime.utcnow().isoformat(),
            "source": "yfinance",
        }
    except Exception as e:
        logger.error(f"yfinance also failed for {symbol}: {e}")
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found or unavailable")


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
    
    # Try real providers first
    if _has_providers():
        try:
            result = await orchestrator.get_quotes(
                symbol_list,
                market_type=MarketType.US_STOCK,
                force_refresh=force_refresh,
            )
            
            for symbol, quote in result.items():
                quotes.append({
                    "symbol": quote.symbol,
                    "name": getattr(quote, 'name', None) or symbol,
                    "exchange": quote.exchange or "",
                    "price": float(quote.price),
                    "change": float(quote.change) if quote.change else 0,
                    "change_percent": float(quote.change_percent) if quote.change_percent else 0,
                    "volume": quote.volume or 0,
                    "timestamp": quote.timestamp.isoformat(),
                    "source": quote.provider,
                })
            
            # Check for missing symbols
            fetched = set(result.keys())
            for sym in symbol_list:
                if sym not in fetched:
                    errors.append({"symbol": sym, "error": "Not found"})
            
            return {"quotes": quotes, "count": len(quotes), "errors": errors}
            
        except Exception as e:
            logger.error(f"Error fetching quotes: {e}")
    
    # yfinance fallback for missing symbols
    import yfinance as yf
    for sym in symbol_list:
        try:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="5d")
            if hist.empty:
                errors.append({"symbol": sym, "error": "Not found"})
                continue
            
            latest = hist.iloc[-1]
            price = float(latest["Close"])
            prev_close = float(hist.iloc[-2]["Close"]) if len(hist) >= 2 else price
            change = price - prev_close
            change_pct = (change / prev_close * 100) if prev_close else 0
            
            quotes.append({
                "symbol": sym,
                "name": ticker.info.get("shortName", sym),
                "exchange": ticker.info.get("exchange", ""),
                "price": round(price, 2),
                "change": round(change, 2),
                "change_percent": round(change_pct, 2),
                "volume": int(latest.get("Volume", 0)),
                "timestamp": datetime.utcnow().isoformat(),
                "source": "yfinance",
            })
        except Exception as e:
            errors.append({"symbol": sym, "error": str(e)})
    
    return {"quotes": quotes, "count": len(quotes), "errors": errors}


@router.get("/history/{symbol}")
async def get_history(
    symbol: str,
    period: str = Query("1M", description="Period: 1D, 1W, 1M, 3M, 1Y"),
    timeframe: str = Query("auto", description="Timeframe: auto, 1m, 5m, 15m, 1h, 1d"),
):
    """Get historical OHLCV data. PUBLIC endpoint."""
    import yfinance as yf
    
    symbol = symbol.upper()
    
    # Intelligent period and interval mapping for good chart display
    # yfinance: period is how far back, interval is bar size
    period_config = {
        "1D": {"period": "1d", "interval": "5m"},    # 1 day of 5-min bars
        "1W": {"period": "5d", "interval": "15m"},   # 5 days of 15-min bars  
        "1M": {"period": "1mo", "interval": "1d"},   # 1 month of daily bars
        "3M": {"period": "3mo", "interval": "1d"},   # 3 months of daily bars
        "1Y": {"period": "1y", "interval": "1d"},    # 1 year of daily bars
        "5Y": {"period": "5y", "interval": "1wk"},   # 5 years of weekly bars
    }
    
    config = period_config.get(period.upper(), {"period": "1mo", "interval": "1d"})
    yf_period = config["period"]
    yf_interval = config["interval"] if timeframe == "auto" else timeframe
    
    # Use yfinance directly for reliable data
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=yf_period, interval=yf_interval)
        
        if hist.empty:
            raise HTTPException(status_code=404, detail=f"No historical data for {symbol}")
        
        data = []
        for idx, row in hist.iterrows():
            # Format date based on interval
            if yf_interval in ["1m", "5m", "15m", "1h"]:
                date_str = idx.strftime("%Y-%m-%d %H:%M")
            else:
                date_str = idx.strftime("%Y-%m-%d")
            
            data.append({
                "date": date_str,
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"]) if row["Volume"] > 0 else 0,
            })
        
        return {
            "symbol": symbol,
            "period": period,
            "timeframe": yf_interval,
            "data": data,
            "source": "yfinance",
        }
        
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
    import yfinance as yf
    
    query = query.strip().upper()
    results = []
    
    # First, try direct symbol lookup if query looks like a ticker
    if len(query) <= 6 and query.isalpha():
        try:
            ticker = yf.Ticker(query)
            info = ticker.info
            
            # Check if valid ticker
            if info.get("regularMarketPrice") or info.get("previousClose"):
                price = info.get("regularMarketPrice") or info.get("previousClose") or 0
                results.append({
                    "symbol": query,
                    "name": info.get("shortName") or info.get("longName") or query,
                    "exchange": info.get("exchange", ""),
                    "sector": info.get("sector", ""),
                    "type": info.get("quoteType", "EQUITY"),
                    "price": round(float(price), 2) if price else None,
                    "currency": info.get("currency", "USD"),
                })
        except Exception as e:
            logger.debug(f"Direct lookup failed for {query}: {e}")
    
    # Use yfinance search for broader results
    try:
        # Try with .search (available in newer yfinance)
        search_results = yf.Tickers(query)
        
        # Also try common variations
        variations = [query]
        if len(query) >= 2:
            # Try with common suffixes for international stocks
            for suffix in ["", ".L", ".DE", ".PA", ".MI", ".T", ".HK"]:
                if f"{query}{suffix}" not in variations:
                    variations.append(f"{query}{suffix}")
        
        for sym in variations[:10]:  # Limit variations to check
            if len(results) >= limit:
                break
            if any(r["symbol"] == sym for r in results):
                continue
            
            try:
                ticker = yf.Ticker(sym)
                info = ticker.info
                
                # Skip if no valid data
                if not (info.get("regularMarketPrice") or info.get("previousClose")):
                    continue
                
                price = info.get("regularMarketPrice") or info.get("previousClose") or 0
                name = info.get("shortName") or info.get("longName") or sym
                
                # Filter: include if symbol matches or name contains query
                if query in sym.upper() or query.lower() in name.lower():
                    results.append({
                        "symbol": sym.upper(),
                        "name": name,
                        "exchange": info.get("exchange", ""),
                        "sector": info.get("sector", ""),
                        "type": info.get("quoteType", "EQUITY"),
                        "price": round(float(price), 2) if price else None,
                        "currency": info.get("currency", "USD"),
                    })
            except Exception:
                continue
                
    except Exception as e:
        logger.warning(f"Search error: {e}")
    
    # If no results yet, try searching by name patterns in common stocks
    if not results:
        # Common large-cap symbols to search through
        common_symbols = [
            "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "NVDA", "TSLA",
            "JPM", "V", "JNJ", "WMT", "MA", "PG", "HD", "DIS", "NFLX", "PYPL",
            "INTC", "AMD", "CRM", "ORCL", "IBM", "CSCO", "ADBE", "QCOM", "TXN",
            "BA", "GE", "CAT", "MMM", "HON", "UPS", "FDX", "RTX", "LMT",
            "KO", "PEP", "MCD", "SBUX", "NKE", "COST", "TGT", "LOW",
            "BAC", "WFC", "C", "GS", "MS", "AXP", "BLK", "SCHW",
            "UNH", "PFE", "MRK", "ABBV", "LLY", "BMY", "TMO", "ABT",
            "XOM", "CVX", "COP", "SLB", "EOG", "OXY",
            "SPY", "QQQ", "IWM", "DIA", "VOO", "VTI", "GLD", "SLV"
        ]
        
        for sym in common_symbols:
            if len(results) >= limit:
                break
            try:
                ticker = yf.Ticker(sym)
                info = ticker.info
                name = info.get("shortName") or info.get("longName") or sym
                
                if query in sym or query.lower() in name.lower():
                    price = info.get("regularMarketPrice") or info.get("previousClose") or 0
                    results.append({
                        "symbol": sym,
                        "name": name,
                        "exchange": info.get("exchange", ""),
                        "sector": info.get("sector", ""),
                        "type": info.get("quoteType", "EQUITY"),
                        "price": round(float(price), 2) if price else None,
                        "currency": info.get("currency", "USD"),
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
