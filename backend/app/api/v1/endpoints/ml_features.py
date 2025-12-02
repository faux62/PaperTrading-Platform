"""
PaperTrading Platform - ML Features Endpoints

API endpoints for ML feature calculation and retrieval.
"""
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from loguru import logger

from app.ml.features import (
    calculate_technical_features,
    calculate_market_features,
    TechnicalFeaturesCalculator,
    FundamentalFeaturesCalculator,
    MarketFeaturesCalculator,
    get_feature_store,
)


router = APIRouter()


# ==================== SCHEMAS ====================

class TechnicalFeaturesRequest(BaseModel):
    """Request for technical feature calculation."""
    symbol: str = Field(..., description="Stock symbol")
    prices: List[float] = Field(..., min_length=50, description="Close prices (most recent last)")
    highs: List[float] = Field(..., min_length=50, description="High prices")
    lows: List[float] = Field(..., min_length=50, description="Low prices")
    volumes: List[float] = Field(..., min_length=50, description="Trading volumes")


class MarketFeaturesRequest(BaseModel):
    """Request for market feature calculation."""
    symbol: str = Field(..., description="Stock symbol")
    stock_returns: List[float] = Field(..., min_length=60, description="Stock daily returns")
    spy_returns: List[float] = Field(..., min_length=60, description="S&P 500 daily returns")
    sector_returns: Optional[List[float]] = Field(None, description="Sector ETF returns")
    vix: Optional[float] = Field(None, description="Current VIX level")
    spy_above_sma_50: Optional[bool] = Field(None, description="SPY above 50-day SMA")
    spy_above_sma_200: Optional[bool] = Field(None, description="SPY above 200-day SMA")


class BatchFeaturesRequest(BaseModel):
    """Request for batch feature calculation."""
    symbols: List[str] = Field(..., max_length=50, description="List of stock symbols")


class FeatureNamesResponse(BaseModel):
    """Response with available feature names."""
    technical: List[str]
    fundamental: List[str]
    market: List[str]
    total: int


# ==================== ENDPOINTS ====================

@router.get("/names")
async def get_feature_names() -> FeatureNamesResponse:
    """
    Get list of all available feature names.
    
    Returns feature names organized by category (technical, fundamental, market).
    """
    tech_names = TechnicalFeaturesCalculator.get_feature_names()
    fund_names = FundamentalFeaturesCalculator.get_feature_names()
    mkt_names = MarketFeaturesCalculator.get_feature_names()
    
    return FeatureNamesResponse(
        technical=tech_names,
        fundamental=fund_names,
        market=mkt_names,
        total=len(tech_names) + len(fund_names) + len(mkt_names),
    )


@router.post("/technical")
async def calculate_technical(request: TechnicalFeaturesRequest):
    """
    Calculate technical indicators for a symbol.
    
    Requires at least 50 data points for accurate calculation.
    Returns 40+ technical indicators including RSI, MACD, Bollinger Bands,
    ATR, ADX, moving averages, and more.
    """
    try:
        features = calculate_technical_features(
            symbol=request.symbol,
            timestamp="",  # Will be set by function
            prices=request.prices,
            highs=request.highs,
            lows=request.lows,
            volumes=request.volumes,
        )
        
        # Store in feature store
        store = get_feature_store()
        store.store_features(
            symbol=request.symbol,
            technical=features,
        )
        
        return {
            "symbol": request.symbol,
            "features": features.to_dict(),
            "feature_count": len([v for v in features.to_dict().values() if v is not None]) - 2,
        }
        
    except Exception as e:
        logger.error(f"Error calculating technical features: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/market")
async def calculate_market(request: MarketFeaturesRequest):
    """
    Calculate market/correlation features for a symbol.
    
    Returns correlations with market indices, sector analysis,
    relative strength, and market regime indicators.
    """
    try:
        market_data = {}
        if request.vix is not None:
            market_data['vix'] = request.vix
        if request.spy_above_sma_50 is not None:
            market_data['spy_above_sma_50'] = request.spy_above_sma_50
        if request.spy_above_sma_200 is not None:
            market_data['spy_above_sma_200'] = request.spy_above_sma_200
        
        features = calculate_market_features(
            symbol=request.symbol,
            stock_returns=request.stock_returns,
            spy_returns=request.spy_returns,
            sector_returns=request.sector_returns,
            market_data=market_data if market_data else None,
        )
        
        # Store in feature store
        store = get_feature_store()
        store.store_features(
            symbol=request.symbol,
            market=features,
        )
        
        return {
            "symbol": request.symbol,
            "features": features.to_dict(),
            "feature_count": len([v for v in features.to_dict().values() if v is not None]) - 3,
        }
        
    except Exception as e:
        logger.error(f"Error calculating market features: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{symbol}")
async def get_stored_features(
    symbol: str,
    include: Optional[str] = Query(
        None, 
        description="Comma-separated feature types (technical,fundamental,market)"
    ),
):
    """
    Get cached/stored features for a symbol.
    
    Returns most recent features from the feature store.
    """
    store = get_feature_store()
    
    include_types = None
    if include:
        include_types = [t.strip() for t in include.split(',')]
    
    features = store.get_features(symbol, include=include_types)
    
    if not features:
        raise HTTPException(
            status_code=404,
            detail=f"No features found for {symbol}"
        )
    
    return features.to_dict()


@router.get("/{symbol}/vector")
async def get_feature_vector(symbol: str):
    """
    Get feature vector for ML model input.
    
    Returns numerical array of all features suitable for model inference.
    """
    store = get_feature_store()
    features = store.get_features(symbol)
    
    if not features:
        raise HTTPException(
            status_code=404,
            detail=f"No features found for {symbol}"
        )
    
    vector = features.to_feature_vector()
    
    return {
        "symbol": symbol,
        "vector": vector,
        "length": len(vector),
        "feature_names": features.get_feature_names()[:len(vector)],
    }


@router.get("/store/stats")
async def get_store_stats():
    """
    Get feature store statistics.
    
    Returns cache and history statistics.
    """
    store = get_feature_store()
    return store.stats()


@router.delete("/{symbol}")
async def invalidate_features(symbol: str):
    """
    Invalidate cached features for a symbol.
    
    Forces recalculation on next request.
    """
    store = get_feature_store()
    store.invalidate(symbol)
    
    return {"message": f"Features invalidated for {symbol}"}


@router.delete("/store/cache")
async def clear_cache():
    """
    Clear the entire feature cache.
    """
    store = get_feature_store()
    store.clear_cache()
    
    return {"message": "Feature cache cleared"}


# ==================== INDICATOR EXPLANATIONS ====================

INDICATOR_DESCRIPTIONS = {
    'rsi_14': {
        'name': 'RSI (14)',
        'description': 'Relative Strength Index - momentum oscillator measuring overbought/oversold',
        'interpretation': 'Above 70 = overbought, Below 30 = oversold',
        'category': 'momentum',
    },
    'macd_line': {
        'name': 'MACD Line',
        'description': 'Moving Average Convergence Divergence - trend-following momentum',
        'interpretation': 'Positive = bullish momentum, Negative = bearish momentum',
        'category': 'trend',
    },
    'macd_histogram': {
        'name': 'MACD Histogram',
        'description': 'Difference between MACD and signal line',
        'interpretation': 'Increasing = strengthening trend, Decreasing = weakening',
        'category': 'trend',
    },
    'bb_percent_b': {
        'name': 'Bollinger %B',
        'description': 'Position within Bollinger Bands',
        'interpretation': 'Above 100% = above upper band, Below 0% = below lower band',
        'category': 'volatility',
    },
    'adx_14': {
        'name': 'ADX (14)',
        'description': 'Average Directional Index - trend strength indicator',
        'interpretation': 'Above 25 = strong trend, Below 20 = weak/no trend',
        'category': 'trend',
    },
    'atr_percent': {
        'name': 'ATR %',
        'description': 'Average True Range as percentage of price',
        'interpretation': 'Higher = more volatile, Lower = less volatile',
        'category': 'volatility',
    },
    'mfi_14': {
        'name': 'MFI (14)',
        'description': 'Money Flow Index - volume-weighted RSI',
        'interpretation': 'Above 80 = overbought, Below 20 = oversold',
        'category': 'volume',
    },
    'correlation_spy': {
        'name': 'SPY Correlation',
        'description': '60-day correlation with S&P 500',
        'interpretation': 'Higher = moves with market, Lower = independent',
        'category': 'market',
    },
    'beta_spy': {
        'name': 'Beta',
        'description': 'Sensitivity to market movements',
        'interpretation': 'Above 1 = more volatile than market, Below 1 = less volatile',
        'category': 'market',
    },
    'pe_ratio': {
        'name': 'P/E Ratio',
        'description': 'Price to Earnings ratio',
        'interpretation': 'Higher = more expensive, Compare to sector average',
        'category': 'valuation',
    },
    'roe': {
        'name': 'ROE',
        'description': 'Return on Equity',
        'interpretation': 'Higher = more efficient use of equity, Compare to sector',
        'category': 'profitability',
    },
    'debt_to_equity': {
        'name': 'Debt/Equity',
        'description': 'Total debt divided by shareholder equity',
        'interpretation': 'Lower = less leveraged, Higher = more financial risk',
        'category': 'financial_health',
    },
}


@router.get("/indicators/descriptions")
async def get_indicator_descriptions():
    """
    Get descriptions and interpretations of available indicators.
    """
    return {
        "indicators": INDICATOR_DESCRIPTIONS,
        "categories": list(set(i['category'] for i in INDICATOR_DESCRIPTIONS.values())),
    }
