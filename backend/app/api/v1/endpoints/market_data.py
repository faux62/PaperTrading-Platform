"""
PaperTrading Platform - Market Data Endpoints
Mock data for Phase 1 testing
"""
from fastapi import APIRouter
from datetime import datetime
import random

router = APIRouter()

# Mock stock database
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

def get_mock_price(symbol: str) -> dict:
    """Generate mock price with small random variation."""
    stock = MOCK_STOCKS.get(symbol.upper())
    if not stock:
        return None
    
    base = stock["base_price"]
    # Random variation +/- 2%
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
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/quote/{symbol}")
async def get_quote(symbol: str):
    """Get current quote for symbol."""
    quote = get_mock_price(symbol)
    if not quote:
        return {"error": f"Symbol {symbol} not found", "symbol": symbol}
    return quote


@router.get("/quotes")
async def get_quotes(symbols: str):
    """Get quotes for multiple symbols (comma-separated)."""
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    quotes = []
    for sym in symbol_list:
        quote = get_mock_price(sym)
        if quote:
            quotes.append(quote)
    return {"quotes": quotes, "count": len(quotes)}


@router.get("/history/{symbol}")
async def get_history(symbol: str, period: str = "1M"):
    """Get historical OHLCV data."""
    stock = MOCK_STOCKS.get(symbol.upper())
    if not stock:
        return {"error": f"Symbol {symbol} not found"}
    
    # Generate mock historical data
    base = stock["base_price"]
    data = []
    days = {"1D": 1, "1W": 7, "1M": 30, "3M": 90, "1Y": 365}.get(period, 30)
    
    for i in range(days):
        variation = random.uniform(-0.03, 0.03)
        price = round(base * (1 + variation), 2)
        data.append({
            "date": f"2024-{12-i//30:02d}-{28-i%28:02d}",
            "open": round(price * 0.99, 2),
            "high": round(price * 1.02, 2),
            "low": round(price * 0.98, 2),
            "close": price,
            "volume": random.randint(1000000, 50000000)
        })
    
    return {"symbol": symbol.upper(), "period": period, "data": list(reversed(data))}


@router.get("/search")
async def search_symbols(query: str):
    """Search for symbols."""
    query = query.upper()
    results = []
    
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
    """Get market hours status."""
    now = datetime.utcnow()
    hour = now.hour
    weekday = now.weekday()
    
    # Simplified: US market open 14:30-21:00 UTC (9:30-16:00 ET)
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
