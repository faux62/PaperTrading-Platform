"""
PaperTrading Platform - Market Data Endpoints
Real data providers with mock fallback
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, date, timedelta
from typing import Optional
import random
from loguru import logger

from app.dependencies import get_current_active_user
from app.db.models.user import User
from app.data_providers import orchestrator, failover_manager, rate_limiter
from app.data_providers.adapters.base import MarketType, TimeFrame, ProviderError

router = APIRouter()

# Mock stock database (fallback when providers unavailable)
MOCK_STOCKS = {
    "AAPL": {"name": "Apple Inc.", "exchange": "NASDAQ", "sector": "Technology", "base_price": 178.50},
    "GOOGL": {"name": "Alphabet Inc.", "exchange": "NASDAQ", "sector": "Technology", "base_price": 141.80},
    "MSFT": {"name": "Microsoft Corporation", "exchange": "NASDAQ", "sector": "Technology", "base_price": 378.90},
    "AMZN": {"name": "Amazon.com Inc.", "exchange": "NASDAQ", "sector": "Consumer Cyclical", "base_price": 178.25},
    "TSLA": {"name": "Tesla Inc.", "exchange": "NASDAQ", "sector": "Automotive", "base_price": 248.50},
    "META": {"name": "Meta Platforms Inc.", "exchange": "NASDAQ", "sector": "Technology", "base_price": 505.75},
    "NVDA": {"name": "NVIDIA Corporation", "exchange": "NASDAQ", "sector": "Technology", "base_price": 475.20},
    "JPM": {"name": "JPMorgan Chase & Co.", "exchange": "NYSE", "sector": "Financial", "base_price": 195.30},
    "V": {"name": "Visa Inc.", "exchange": "NYSE", "sector": "Financial", "base_price": 275.40},
    "JNJ": {"name": "Johnson & Johnson", "exchange": "NYSE", "sector": "Healthcare", "base_price": 156.80},
    "WMT": {"name": "Walmart Inc.", "exchange": "NYSE", "sector": "Consumer Defensive", "base_price": 165.20},
    "PG": {"name": "Procter & Gamble Co.", "exchange": "NYSE", "sector": "Consumer Defensive", "base_price": 158.90},
    "MA": {"name": "Mastercard Inc.", "exchange": "NYSE", "sector": "Financial", "base_price": 445.60},
    "HD": {"name": "Home Depot Inc.", "exchange": "NYSE", "sector": "Consumer Cyclical", "base_price": 345.70},
    "DIS": {"name": "Walt Disney Co.", "exchange": "NYSE", "sector": "Communication", "base_price": 112.30},
    "NFLX": {"name": "Netflix Inc.", "exchange": "NASDAQ", "sector": "Communication", "base_price": 478.90},
    "PYPL": {"name": "PayPal Holdings Inc.", "exchange": "NASDAQ", "sector": "Financial", "base_price": 62.45},
    "INTC": {"name": "Intel Corporation", "exchange": "NASDAQ", "sector": "Technology", "base_price": 45.20},
    "AMD": {"name": "Advanced Micro Devices", "exchange": "NASDAQ", "sector": "Technology", "base_price": 138.60},
    "CRM": {"name": "Salesforce Inc.", "exchange": "NYSE", "sector": "Technology", "base_price": 265.30},
    "SPY": {"name": "SPDR S&P 500 ETF", "exchange": "NYSE", "sector": "ETF", "base_price": 595.00},
    "QQQ": {"name": "Invesco QQQ Trust", "exchange": "NASDAQ", "sector": "ETF", "base_price": 520.00},
    "IWM": {"name": "iShares Russell 2000 ETF", "exchange": "NYSE", "sector": "ETF", "base_price": 235.00},
}


def _get_mock_price(symbol: str) -> dict:
    """Generate mock price with small random variation (fallback)."""
    stock = MOCK_STOCKS.get(symbol.upper())
    if not stock:
        return None
    
    base = stock["base_price"]
    variation = random.uniform(-0.02, 0.02)
    price = round(base * (1 + variation), 2)
    change = round(price - base, 2)
    change_pct = round((change / base) * 100, 2)
    
    return {
        "symbol": symbol.upper(),
        "name": stock["name"],
        "exchange": stock["exchange"],
        "price": price,
        "change": change,
        "change_percent": change_pct,
        "volume": random.randint(1000000, 50000000),
        "bid": round(price - 0.01, 2),
        "ask": round(price + 0.01, 2),
        "high": round(price * 1.01, 2),
        "low": round(price * 0.99, 2),
        "open": round(base, 2),
        "previous_close": round(base, 2),
        "timestamp": datetime.utcnow().isoformat(),
        "source": "mock"
    }


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
                "name": MOCK_STOCKS.get(symbol, {}).get("name", symbol),
                "exchange": quote.exchange or MOCK_STOCKS.get(symbol, {}).get("exchange", ""),
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
            logger.warning(f"Provider error for {symbol}, using mock: {e}")
        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {e}")
    
    # Fallback to mock data
    quote = _get_mock_price(symbol)
    if not quote:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
    return quote


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
                    "name": MOCK_STOCKS.get(symbol, {}).get("name", symbol),
                    "exchange": MOCK_STOCKS.get(symbol, {}).get("exchange", ""),
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
    
    # Fallback to mock
    for sym in symbol_list:
        quote = _get_mock_price(sym)
        if quote:
            quotes.append(quote)
        else:
            errors.append({"symbol": sym, "error": "Not found"})
    
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
    query: str = Query(..., min_length=1, description="Search query"),
    current_user: User = Depends(get_current_active_user)
):
    """Search for symbols."""
    query = query.upper()
    results = []
    
    # Search mock database (in future, can use provider search APIs)
    for symbol, info in MOCK_STOCKS.items():
        if query in symbol or query.lower() in info["name"].lower():
            results.append({
                "symbol": symbol,
                "name": info["name"],
                "exchange": info["exchange"],
                "sector": info["sector"],
                "type": "Stock"
            })
    
    return {"results": results, "count": len(results), "query": query}


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
