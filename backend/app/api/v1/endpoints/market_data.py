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
    # Filter indices by region if specified
    if region:
        indices_to_fetch = [k for k, v in MARKET_INDICES.items() if v["region"].lower() == region.lower()]
    else:
        # Default: main indices from each region
        indices_to_fetch = ["^GSPC", "^IXIC", "^DJI", "^FTSE", "^GDAXI", "FTSEMIB.MI", "^N225", "BTC-USD", "ETH-USD", "GC=F", "CL=F"]
    
    results = {}
    
    # Try real providers
    if _has_providers():
        for symbol in indices_to_fetch:
            try:
                info = MARKET_INDICES.get(symbol, {})
                market_type = MarketType.CRYPTO if info.get("type") == "crypto" else MarketType.INDEX
                
                quote = await orchestrator.get_quote(
                    symbol,
                    market_type=market_type,
                    force_refresh=False,
                )
                
                results[symbol] = {
                    "symbol": symbol,
                    "name": info.get("name", symbol),
                    "region": info.get("region", "Other"),
                    "type": info.get("type", "index"),
                    "price": float(quote.price),
                    "change": float(quote.change) if quote.change else 0,
                    "change_percent": float(quote.change_percent) if quote.change_percent else 0,
                    "timestamp": quote.timestamp.isoformat(),
                    "source": quote.provider,
                }
            except Exception as e:
                logger.warning(f"Failed to fetch {symbol}: {e}")
    
    # Fill in any missing with placeholder
    for symbol in indices_to_fetch:
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
    timeframe: str = Query("1d", description="Timeframe: 1m, 5m, 15m, 1h, 1d"),
    current_user: User = Depends(get_current_active_user)
):
    """Get historical OHLCV data."""
    symbol = symbol.upper()
    
    # Map period to start date
    period_map = {"1D": 1, "1W": 7, "1M": 30, "3M": 90, "1Y": 365}
    days = period_map.get(period.upper(), 30)
    
    start_date = date.today() - timedelta(days=days)
    end_date = date.today()
    
    # Map timeframe
    tf_map = {
        "1m": TimeFrame.MIN_1,
        "5m": TimeFrame.MIN_5,
        "15m": TimeFrame.MIN_15,
        "1h": TimeFrame.HOUR,
        "1d": TimeFrame.DAY,
    }
    tf = tf_map.get(timeframe.lower(), TimeFrame.DAY)
    
    # Try real providers
    if _has_providers():
        try:
            bars = await orchestrator.get_historical(
                symbol,
                timeframe=tf,
                start_date=start_date,
                end_date=end_date,
                market_type=MarketType.US_STOCK,
            )
            
            data = []
            for bar in bars:
                data.append({
                    "date": bar.timestamp.strftime("%Y-%m-%d") if isinstance(bar.timestamp, datetime) else str(bar.timestamp),
                    "open": float(bar.open),
                    "high": float(bar.high),
                    "low": float(bar.low),
                    "close": float(bar.close),
                    "volume": bar.volume,
                })
            
            return {
                "symbol": symbol,
                "period": period,
                "timeframe": timeframe,
                "data": data,
                "source": bars[0].provider if bars else "unknown",
            }
            
        except Exception as e:
            logger.warning(f"Error fetching history for {symbol}, using mock: {e}")
    
    # Fallback to mock
    stock = MOCK_STOCKS.get(symbol)
    if not stock:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
    
    base = stock["base_price"]
    data = []
    
    for i in range(days):
        variation = random.uniform(-0.03, 0.03)
        price = round(base * (1 + variation), 2)
        d = date.today() - timedelta(days=days - i)
        data.append({
            "date": d.strftime("%Y-%m-%d"),
            "open": round(price * 0.99, 2),
            "high": round(price * 1.02, 2),
            "low": round(price * 0.98, 2),
            "close": price,
            "volume": random.randint(1000000, 50000000)
        })
    
    return {"symbol": symbol, "period": period, "timeframe": timeframe, "data": data, "source": "mock"}


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
async def get_market_hours(
    current_user: User = Depends(get_current_active_user)
):
    """Get market hours status."""
    now = datetime.utcnow()
    hour = now.hour
    weekday = now.weekday()
    
    # US market open 14:30-21:00 UTC (9:30-16:00 ET)
    is_open = weekday < 5 and 14 <= hour < 21
    
    return {
        "us_market": {
            "is_open": is_open,
            "status": "open" if is_open else "closed",
            "next_open": "09:30 ET" if not is_open else None,
            "next_close": "16:00 ET" if is_open else None,
            "timezone": "America/New_York"
        },
        "current_time_utc": now.isoformat(),
        "trading_day": weekday < 5
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
    current_user: User = Depends(get_current_active_user)
):
    """Get top gaining stocks for the day."""
    try:
        import yfinance as yf
        import pandas as pd
        
        # Core stocks to check - smaller list for faster response
        active_symbols = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM',
            'V', 'UNH', 'HD', 'MA', 'NFLX', 'ADBE', 'CRM', 'AMD', 'INTC',
            'ORCL', 'CSCO', 'BA', 'CAT', 'WMT', 'KO', 'PEP', 'MCD'
        ]
        
        quotes = []
        
        # Use yf.download which is faster than individual ticker.info calls
        try:
            # Use 5d to ensure we have data even over weekends
            data = yf.download(active_symbols, period='5d', progress=False, threads=True)
            
            if not data.empty:
                # Get the last two UNIQUE closes to calculate change
                for symbol in active_symbols:
                    try:
                        if isinstance(data.columns, pd.MultiIndex):
                            close_data = data['Close'][symbol].dropna()
                            volume_data = data['Volume'][symbol]
                        else:
                            close_data = data['Close'].dropna()
                            volume_data = data['Volume']
                        
                        if len(close_data) >= 2:
                            current_price = float(close_data.iloc[-1])
                            # Find previous different close (skip duplicates from market closed days)
                            prev_price = current_price
                            for i in range(2, min(len(close_data) + 1, 6)):
                                prev_price = float(close_data.iloc[-i])
                                if abs(prev_price - current_price) > 0.001:
                                    break
                            
                            # If all prices are the same, use the oldest one
                            if abs(prev_price - current_price) < 0.001:
                                prev_price = float(close_data.iloc[0])
                            
                            change = current_price - prev_price
                            change_pct = (change / prev_price) * 100 if prev_price > 0 else 0
                            volume = int(volume_data.iloc[-1]) if not pd.isna(volume_data.iloc[-1]) else 0
                            
                            if change_pct > 0.1:  # Only show meaningful gains
                                quotes.append({
                                    "symbol": symbol,
                                    "name": symbol,
                                    "price": round(current_price, 2),
                                    "change": round(change, 2),
                                    "change_percent": round(change_pct, 2),
                                    "volume": volume,
                                })
                    except Exception:
                        continue
        except Exception as e:
            print(f"yf.download failed: {e}")
        
        # Sort by change_percent descending
        quotes.sort(key=lambda x: x['change_percent'], reverse=True)
        return {"gainers": quotes[:limit], "source": "calculated"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching gainers: {str(e)}")


@router.get("/movers/losers")
async def get_top_losers(
    limit: int = 10,
    current_user: User = Depends(get_current_active_user)
):
    """Get top losing stocks for the day."""
    try:
        import yfinance as yf
        import pandas as pd
        
        # Core stocks to check
        active_symbols = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM',
            'V', 'UNH', 'HD', 'MA', 'NFLX', 'ADBE', 'CRM', 'AMD', 'INTC',
            'ORCL', 'CSCO', 'BA', 'CAT', 'WMT', 'KO', 'PEP', 'MCD'
        ]
        
        quotes = []
        
        try:
            # Use 5d to ensure we have data even over weekends
            data = yf.download(active_symbols, period='5d', progress=False, threads=True)
            
            if not data.empty:
                for symbol in active_symbols:
                    try:
                        if isinstance(data.columns, pd.MultiIndex):
                            close_data = data['Close'][symbol].dropna()
                            volume_data = data['Volume'][symbol]
                        else:
                            close_data = data['Close'].dropna()
                            volume_data = data['Volume']
                        
                        if len(close_data) >= 2:
                            current_price = float(close_data.iloc[-1])
                            # Find previous different close
                            prev_price = current_price
                            for i in range(2, min(len(close_data) + 1, 6)):
                                prev_price = float(close_data.iloc[-i])
                                if abs(prev_price - current_price) > 0.001:
                                    break
                            
                            if abs(prev_price - current_price) < 0.001:
                                prev_price = float(close_data.iloc[0])
                            
                            change = current_price - prev_price
                            change_pct = (change / prev_price) * 100 if prev_price > 0 else 0
                            volume = int(volume_data.iloc[-1]) if not pd.isna(volume_data.iloc[-1]) else 0
                            
                            if change_pct < -0.1:  # Only show meaningful losses
                                quotes.append({
                                    "symbol": symbol,
                                    "name": symbol,
                                    "price": round(current_price, 2),
                                    "change": round(change, 2),
                                    "change_percent": round(change_pct, 2),
                                    "volume": volume,
                                })
                    except Exception:
                        continue
        except Exception as e:
            print(f"yf.download failed: {e}")
        
        # Sort by change_percent ascending (most negative first)
        quotes.sort(key=lambda x: x['change_percent'])
        return {"losers": quotes[:limit], "source": "calculated"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching losers: {str(e)}")


@router.get("/movers/most-active")
async def get_most_active(
    limit: int = 10,
    current_user: User = Depends(get_current_active_user)
):
    """Get most actively traded stocks by volume."""
    try:
        import yfinance as yf
        import pandas as pd
        
        # Core stocks to check
        active_symbols = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM',
            'V', 'UNH', 'HD', 'MA', 'NFLX', 'ADBE', 'CRM', 'AMD', 'INTC',
            'ORCL', 'CSCO', 'BA', 'CAT', 'WMT', 'KO', 'PEP', 'MCD', 'SPY', 'QQQ'
        ]
        
        quotes = []
        
        try:
            data = yf.download(active_symbols, period='2d', progress=False, threads=True)
            
            if not data.empty:
                for symbol in active_symbols:
                    try:
                        if isinstance(data.columns, pd.MultiIndex):
                            close_data = data['Close'][symbol]
                            volume_data = data['Volume'][symbol]
                        else:
                            close_data = data['Close']
                            volume_data = data['Volume']
                        
                        if len(close_data) >= 2 and not pd.isna(close_data.iloc[-1]):
                            current_price = float(close_data.iloc[-1])
                            prev_price = float(close_data.iloc[-2])
                            change = current_price - prev_price
                            change_pct = (change / prev_price) * 100 if prev_price > 0 else 0
                            volume = float(volume_data.iloc[-1])
                            
                            if volume > 0:
                                quotes.append({
                                    "symbol": symbol,
                                    "name": symbol,
                                    "price": round(current_price, 2),
                                    "change": round(change, 2),
                                    "change_percent": round(change_pct, 2),
                                    "volume": int(volume),
                                })
                    except Exception:
                        continue
        except Exception as e:
            print(f"yf.download failed: {e}")
        
        # Sort by volume descending
        quotes.sort(key=lambda x: x['volume'], reverse=True)
        return {"most_active": quotes[:limit], "source": "calculated"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching most active: {str(e)}")


@router.get("/movers/trending")
async def get_trending(
    limit: int = 10,
    current_user: User = Depends(get_current_active_user)
):
    """Get trending stocks based on unusual volume and price movement."""
    try:
        import yfinance as yf
        import pandas as pd
        
        # Core stocks to check - mix of popular and volatile stocks
        trending_candidates = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'AMD',
            'NFLX', 'PLTR', 'SOFI', 'RIVN', 'NIO', 'COIN', 'HOOD',
            'RBLX', 'SNAP', 'UBER', 'ABNB', 'ROKU', 'CRWD', 'NET'
        ]
        
        quotes = []
        
        try:
            # Get 5 days to calculate average volume
            data = yf.download(trending_candidates, period='5d', progress=False, threads=True)
            
            if not data.empty:
                for symbol in trending_candidates:
                    try:
                        if isinstance(data.columns, pd.MultiIndex):
                            close_data = data['Close'][symbol]
                            volume_data = data['Volume'][symbol]
                        else:
                            close_data = data['Close']
                            volume_data = data['Volume']
                        
                        if len(close_data) >= 2 and not pd.isna(close_data.iloc[-1]):
                            current_price = float(close_data.iloc[-1])
                            prev_price = float(close_data.iloc[-2])
                            change = current_price - prev_price
                            change_pct = (change / prev_price) * 100 if prev_price > 0 else 0
                            volume = float(volume_data.iloc[-1])
                            avg_volume = float(volume_data.mean())
                            
                            volume_ratio = volume / avg_volume if avg_volume > 0 else 0
                            trending_score = (volume_ratio * 0.6) + (abs(change_pct) * 0.4)
                            
                            if volume > 0:
                                quotes.append({
                                    "symbol": symbol,
                                    "name": symbol,
                                    "price": round(current_price, 2),
                                    "change": round(change, 2),
                                    "change_percent": round(change_pct, 2),
                                    "volume": int(volume),
                                    "avg_volume": int(avg_volume),
                                    "volume_ratio": round(volume_ratio, 2),
                                    "trending_score": round(trending_score, 2),
                                })
                    except Exception:
                        continue
        except Exception as e:
            print(f"yf.download failed: {e}")
        
        # Sort by trending score descending
        quotes.sort(key=lambda x: x['trending_score'], reverse=True)
        return {"trending": quotes[:limit], "source": "calculated"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching trending: {str(e)}")
