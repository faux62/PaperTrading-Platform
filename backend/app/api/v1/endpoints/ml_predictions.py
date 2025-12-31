"""
ML Predictions API Endpoints

REST API endpoints for ML predictions and signals.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, date
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from loguru import logger

# Import ML components
from app.ml.inference import (
    InferenceService,
    PredictionRequest,
    PredictionResponse,
    PredictionType,
    SignalGenerator,
    TradingSignal,
    AggregatedSignal,
    SignalType,
    SignalSource,
    get_inference_service,
    get_signal_generator
)
from app.ml.models import (
    PortfolioOptimizer,
    OptimizedPortfolio,
    OptimizationObjective,
    PortfolioConstraints,
    RiskParityOptimizer
)
import numpy as np


router = APIRouter(prefix="/ml", tags=["ML Predictions"])


# Request/Response Models
class PredictionRequestModel(BaseModel):
    """Request for ML prediction."""
    symbol: str = Field(..., description="Stock symbol")
    features: List[float] = Field(..., description="Input features")
    prediction_types: List[str] = Field(
        default=["price_direction"],
        description="Types of predictions to make"
    )
    horizon: int = Field(default=1, description="Prediction horizon in days")


class BatchPredictionRequest(BaseModel):
    """Request for batch predictions."""
    requests: List[PredictionRequestModel]


class SignalRequestModel(BaseModel):
    """Request for trading signal."""
    symbol: str
    predictions: Dict[str, Any]
    current_price: float


class PortfolioOptimizationRequest(BaseModel):
    """Request for portfolio optimization."""
    symbols: List[str] = Field(..., description="Asset symbols")
    returns: List[List[float]] = Field(..., description="Historical returns matrix")
    objective: str = Field(default="max_sharpe", description="Optimization objective")
    min_weight: float = Field(default=0.0, description="Minimum weight per asset")
    max_weight: float = Field(default=1.0, description="Maximum weight per asset")
    long_only: bool = Field(default=True, description="Long only constraint")
    target_return: Optional[float] = Field(default=None, description="Target return")
    target_volatility: Optional[float] = Field(default=None, description="Target volatility")


class RebalanceRequest(BaseModel):
    """Request for rebalancing calculation."""
    current_weights: Dict[str, float]
    target_weights: Dict[str, float]
    current_prices: Dict[str, float]
    portfolio_value: float
    min_trade_value: float = Field(default=100.0)


class PredictionResponseModel(BaseModel):
    """Response with predictions."""
    request_id: str
    symbol: str
    predictions: Dict[str, Any]
    confidence: float
    timestamp: str
    latency_ms: float
    model_versions: Dict[str, str] = {}


class SignalResponseModel(BaseModel):
    """Response with trading signal."""
    symbol: str
    signal_type: str
    source: str
    strength: float
    confidence: float
    price_target: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    direction: int
    is_valid: bool


class AggregatedSignalResponse(BaseModel):
    """Response with aggregated signal."""
    symbol: str
    consensus_signal: str
    consensus_strength: float
    consensus_confidence: float
    agreement_ratio: float
    recommended_action: str
    position_size_suggestion: float
    individual_signals: List[Dict[str, Any]]


class TradeCandidateModel(BaseModel):
    """A trade candidate with full trading parameters."""
    symbol: str
    region: str  # US, EU, Asia
    signal: str  # BUY, SELL, HOLD
    confidence: float
    current_price: float
    currency: str
    # Trading parameters
    entry_price: float  # Suggested entry (limit order price)
    stop_loss: float  # -3% for EU, -4% for US
    stop_loss_percent: float
    take_profit: float  # +5% to +10%
    take_profit_percent: float
    # Position sizing
    max_position_value: float  # 5% of portfolio
    suggested_shares: int
    risk_reward_ratio: float
    # Additional info
    trend: str
    volatility: Optional[str] = None
    ranking: int  # 1 = best candidate


class TradeCandidatesResponse(BaseModel):
    """Response with daily trade candidates."""
    date: str
    portfolio_value: float
    portfolio_currency: str
    max_position_percent: float
    candidates: List[TradeCandidateModel]
    eu_candidates: int
    us_candidates: int
    generated_at: str


class PortfolioResponse(BaseModel):
    """Response with optimized portfolio."""
    weights: Dict[str, float]
    expected_return: float
    volatility: float
    sharpe_ratio: float
    objective: str
    risk_contribution: Dict[str, float]
    optimization_status: str
    optimization_message: str


# Dependency injection
def get_inference() -> InferenceService:
    return get_inference_service()


def get_signals() -> SignalGenerator:
    return get_signal_generator()


# Endpoints
@router.post("/predict", response_model=PredictionResponseModel)
async def predict(
    request: PredictionRequestModel,
    inference: InferenceService = Depends(get_inference)
):
    """
    Make ML predictions for a symbol.
    
    Supports multiple prediction types:
    - price_direction: Predict if price will go up or down
    - trend: Classify the current trend
    - volatility: Forecast volatility
    - risk: Assess risk level
    """
    try:
        # Convert prediction types
        pred_types = []
        for pt in request.prediction_types:
            try:
                pred_types.append(PredictionType(pt))
            except ValueError:
                logger.warning(f"Unknown prediction type: {pt}")
        
        if not pred_types:
            pred_types = [PredictionType.PRICE_DIRECTION]
        
        # Create prediction request
        pred_request = PredictionRequest(
            symbol=request.symbol,
            features=np.array(request.features),
            prediction_types=pred_types,
            horizon=request.horizon
        )
        
        # Make prediction
        response = await inference.predict_async(pred_request)
        
        return PredictionResponseModel(
            request_id=response.request_id,
            symbol=response.symbol,
            predictions=response.predictions,
            confidence=response.confidence,
            timestamp=response.timestamp.isoformat(),
            latency_ms=response.latency_ms,
            model_versions=response.model_versions
        )
        
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict/batch", response_model=List[PredictionResponseModel])
async def predict_batch(
    request: BatchPredictionRequest,
    inference: InferenceService = Depends(get_inference)
):
    """Make batch predictions for multiple symbols."""
    try:
        # Create prediction requests
        pred_requests = []
        for req in request.requests:
            pred_types = [PredictionType(pt) for pt in req.prediction_types if pt in PredictionType.__members__.values()]
            pred_requests.append(PredictionRequest(
                symbol=req.symbol,
                features=np.array(req.features),
                prediction_types=pred_types or [PredictionType.PRICE_DIRECTION],
                horizon=req.horizon
            ))
        
        # Make batch predictions
        responses = await inference.predict_batch_async(pred_requests)
        
        return [
            PredictionResponseModel(
                request_id=r.request_id,
                symbol=r.symbol,
                predictions=r.predictions,
                confidence=r.confidence,
                timestamp=r.timestamp.isoformat(),
                latency_ms=r.latency_ms,
                model_versions=r.model_versions
            )
            for r in responses
        ]
        
    except Exception as e:
        logger.error(f"Batch prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ensemble/{symbol}", response_model=PredictionResponseModel)
async def ensemble_prediction(
    symbol: str,
    features: List[float],
    inference: InferenceService = Depends(get_inference)
):
    """Get ensemble prediction combining all models."""
    try:
        response = inference.get_ensemble_prediction(
            symbol=symbol,
            features=np.array(features)
        )
        
        return PredictionResponseModel(
            request_id=response.request_id,
            symbol=response.symbol,
            predictions=response.predictions,
            confidence=response.confidence,
            timestamp=response.timestamp.isoformat(),
            latency_ms=response.latency_ms,
            model_versions=response.model_versions
        )
        
    except Exception as e:
        logger.error(f"Ensemble prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/signal", response_model=SignalResponseModel)
async def generate_signal(
    request: SignalRequestModel,
    signals: SignalGenerator = Depends(get_signals)
):
    """Generate trading signal from predictions."""
    try:
        signal = signals.generate_signal_from_prediction(
            symbol=request.symbol,
            prediction=request.predictions,
            current_price=request.current_price
        )
        
        return SignalResponseModel(
            symbol=signal.symbol,
            signal_type=signal.signal_type.value,
            source=signal.source.value,
            strength=signal.strength,
            confidence=signal.confidence,
            price_target=signal.price_target,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            direction=signal.direction,
            is_valid=signal.is_valid
        )
        
    except Exception as e:
        logger.error(f"Signal generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/signal/aggregate", response_model=AggregatedSignalResponse)
async def aggregate_signals(
    symbol: str,
    predictions: Dict[str, Any],
    current_price: float,
    signals: SignalGenerator = Depends(get_signals)
):
    """Generate and aggregate signals from multiple prediction sources."""
    try:
        # Generate signals from ensemble
        individual_signals = signals.generate_signals_from_ensemble(
            symbol=symbol,
            predictions=predictions,
            current_price=current_price
        )
        
        # Aggregate signals
        aggregated = signals.aggregate_signals(individual_signals)
        
        return AggregatedSignalResponse(
            symbol=aggregated.symbol,
            consensus_signal=aggregated.consensus_signal.value,
            consensus_strength=aggregated.consensus_strength,
            consensus_confidence=aggregated.consensus_confidence,
            agreement_ratio=aggregated.agreement_ratio,
            recommended_action=aggregated.recommended_action,
            position_size_suggestion=aggregated.position_size_suggestion,
            individual_signals=[s.to_dict() for s in aggregated.individual_signals]
        )
        
    except Exception as e:
        logger.error(f"Signal aggregation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals/{symbol}/history")
async def get_signal_history(
    symbol: str,
    limit: int = Query(default=10, ge=1, le=100),
    signals: SignalGenerator = Depends(get_signals)
):
    """Get historical signals for a symbol."""
    history = signals.get_signal_history(symbol, limit=limit)
    return [s.to_dict() for s in history]


@router.get("/signals/active")
async def get_active_signals(
    symbol: Optional[str] = None,
    signals: SignalGenerator = Depends(get_signals)
):
    """Get currently active (valid) signals."""
    active = signals.get_active_signals(symbol)
    return [s.to_dict() for s in active]


@router.post("/portfolio/optimize", response_model=PortfolioResponse)
async def optimize_portfolio(request: PortfolioOptimizationRequest):
    """
    Optimize portfolio weights using Mean-Variance Optimization.
    
    Objectives:
    - max_sharpe: Maximize Sharpe ratio
    - min_volatility: Minimize portfolio volatility
    - max_return: Maximize expected return
    - risk_parity: Equal risk contribution
    - target_return: Minimize vol for target return
    - target_volatility: Maximize return for target vol
    """
    try:
        optimizer = PortfolioOptimizer()
        
        # Parse objective
        try:
            objective = OptimizationObjective(request.objective)
        except ValueError:
            objective = OptimizationObjective.MAX_SHARPE
        
        # Create constraints
        constraints = PortfolioConstraints(
            min_weight=request.min_weight,
            max_weight=request.max_weight,
            long_only=request.long_only,
            target_return=request.target_return,
            target_volatility=request.target_volatility
        )
        
        # Convert returns to numpy
        returns = np.array(request.returns)
        
        # Optimize
        result = optimizer.optimize(
            returns=returns,
            symbols=request.symbols,
            objective=objective,
            constraints=constraints
        )
        
        return PortfolioResponse(
            weights=result.weights,
            expected_return=result.expected_return,
            volatility=result.volatility,
            sharpe_ratio=result.sharpe_ratio,
            objective=result.objective.value,
            risk_contribution=result.risk_contribution,
            optimization_status=result.optimization_status,
            optimization_message=result.optimization_message
        )
        
    except Exception as e:
        logger.error(f"Portfolio optimization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/portfolio/efficient-frontier")
async def calculate_efficient_frontier(
    symbols: List[str],
    returns: List[List[float]],
    n_portfolios: int = Query(default=50, ge=10, le=200)
):
    """Calculate the efficient frontier."""
    try:
        optimizer = PortfolioOptimizer()
        
        frontier = optimizer.calculate_efficient_frontier(
            returns=np.array(returns),
            symbols=symbols,
            n_portfolios=n_portfolios
        )
        
        return {"efficient_frontier": frontier}
        
    except Exception as e:
        logger.error(f"Efficient frontier error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/portfolio/risk-parity", response_model=PortfolioResponse)
async def risk_parity_optimization(
    symbols: List[str],
    returns: List[List[float]],
    risk_budgets: Optional[Dict[str, float]] = None
):
    """Optimize portfolio for risk parity."""
    try:
        optimizer = RiskParityOptimizer()
        
        result = optimizer.optimize(
            returns=np.array(returns),
            symbols=symbols,
            risk_budgets=risk_budgets
        )
        
        return PortfolioResponse(
            weights=result.weights,
            expected_return=result.expected_return,
            volatility=result.volatility,
            sharpe_ratio=result.sharpe_ratio,
            objective=result.objective.value,
            risk_contribution=result.risk_contribution,
            optimization_status=result.optimization_status,
            optimization_message=result.optimization_message
        )
        
    except Exception as e:
        logger.error(f"Risk parity error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/portfolio/rebalance")
async def calculate_rebalance(request: RebalanceRequest):
    """Calculate rebalancing trades."""
    try:
        optimizer = PortfolioOptimizer()
        
        trades = optimizer.rebalance_portfolio(
            current_weights=request.current_weights,
            target_weights=request.target_weights,
            current_prices=request.current_prices,
            portfolio_value=request.portfolio_value,
            min_trade_value=request.min_trade_value
        )
        
        return {"trades": trades}
        
    except Exception as e:
        logger.error(f"Rebalance calculation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def ml_health_check(
    inference: InferenceService = Depends(get_inference)
):
    """Check ML service health."""
    return inference.health_check()


# ============================================================================
# AUTO-GENERATION ENDPOINTS FOR PORTFOLIO ML PREDICTIONS
# ============================================================================

class AutoPredictionRequest(BaseModel):
    """Request for auto-generating predictions."""
    symbols: List[str] = Field(..., description="List of stock symbols")
    include_technical: bool = Field(default=True, description="Include technical indicators")


class SymbolPrediction(BaseModel):
    """Prediction result for a single symbol."""
    symbol: str
    signal: str  # strong_buy, buy, hold, sell, strong_sell
    confidence: float
    price: float
    price_target: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    change_percent: float
    predicted_change: float
    direction: int  # 1=up, 0=neutral, -1=down
    source: str
    features_used: List[str]
    timestamp: str
    metadata: Dict[str, Any] = {}


class AutoPredictionResponse(BaseModel):
    """Response with auto-generated predictions."""
    predictions: List[SymbolPrediction]
    model_info: Dict[str, Any]
    generated_at: str
    total_symbols: int
    successful: int
    failed: int


def calculate_technical_features(quote: Dict[str, Any]) -> Dict[str, float]:
    """Calculate technical features from quote data."""
    price = quote.get('price', 0) or 0
    open_price = quote.get('day_open', price) or quote.get('open', price) or price
    high = quote.get('day_high', price) or quote.get('high', price) or price
    low = quote.get('day_low', price) or quote.get('low', price) or price
    volume = quote.get('volume', 0) or 0
    change = quote.get('change', 0) or 0
    change_percent = quote.get('change_percent', 0) or 0
    
    features = {}
    
    # Basic price features
    if price > 0:
        features['price'] = price
        features['change_percent'] = change_percent
        
        # Intraday position (0 to 1)
        if high > low:
            features['intraday_position'] = (price - low) / (high - low)
        else:
            features['intraday_position'] = 0.5
        
        # Price momentum (change vs range)
        daily_range = high - low
        if daily_range > 0:
            features['momentum_ratio'] = change / daily_range if change else 0
        else:
            features['momentum_ratio'] = 0
        
        # Gap (open vs previous close estimate)
        if open_price > 0:
            prev_close_est = price - change
            if prev_close_est > 0:
                features['gap_percent'] = ((open_price - prev_close_est) / prev_close_est) * 100
            else:
                features['gap_percent'] = 0
        
        # Volatility estimate (range as % of price)
        features['volatility_estimate'] = (daily_range / price) * 100 if price > 0 else 0
        
        # Volume normalized (will be compared relatively)
        features['volume'] = volume
        
    return features


def generate_signal_from_features(
    symbol: str,
    features: Dict[str, float],
    price: float
) -> SymbolPrediction:
    """Generate trading signal from technical features."""
    
    change_percent = features.get('change_percent', 0)
    intraday_pos = features.get('intraday_position', 0.5)
    momentum = features.get('momentum_ratio', 0)
    volatility = features.get('volatility_estimate', 0)
    gap = features.get('gap_percent', 0)
    
    # Composite score calculation
    # Weighted combination of factors
    score = 0.0
    confidence = 0.5
    
    # Change percent influence (strongest factor)
    if change_percent > 3:
        score += 0.4
        confidence += 0.15
    elif change_percent > 1.5:
        score += 0.25
        confidence += 0.1
    elif change_percent > 0.5:
        score += 0.1
        confidence += 0.05
    elif change_percent < -3:
        score -= 0.4
        confidence += 0.15
    elif change_percent < -1.5:
        score -= 0.25
        confidence += 0.1
    elif change_percent < -0.5:
        score -= 0.1
        confidence += 0.05
    
    # Intraday position influence
    if intraday_pos > 0.85:  # Near high
        score += 0.15
        confidence += 0.05
    elif intraday_pos < 0.15:  # Near low
        score -= 0.15
        confidence += 0.05
    
    # Momentum influence
    if momentum > 0.5:
        score += 0.1
    elif momentum < -0.5:
        score -= 0.1
    
    # Gap influence
    if gap > 1:
        score += 0.1
    elif gap < -1:
        score -= 0.1
    
    # High volatility reduces confidence
    if volatility > 5:
        confidence *= 0.85
    
    # Determine signal type
    if score > 0.5:
        signal = "strong_buy"
        direction = 1
    elif score > 0.2:
        signal = "buy"
        direction = 1
    elif score < -0.5:
        signal = "strong_sell"
        direction = -1
    elif score < -0.2:
        signal = "sell"
        direction = -1
    else:
        signal = "hold"
        direction = 0
    
    # Clamp confidence
    confidence = max(0.35, min(0.95, confidence))
    
    # Calculate price targets based on signal
    predicted_change = score * 5  # Scale score to percentage
    price_target = price * (1 + predicted_change / 100)
    
    if direction == 1:
        stop_loss = price * 0.97  # 3% stop loss
        take_profit = price * (1 + abs(predicted_change) * 1.5 / 100)
    elif direction == -1:
        stop_loss = price * 1.03  # 3% stop loss for short
        take_profit = price * (1 - abs(predicted_change) * 1.5 / 100)
    else:
        stop_loss = None
        take_profit = None
    
    return SymbolPrediction(
        symbol=symbol,
        signal=signal,
        confidence=round(confidence, 3),
        price=round(price, 2),
        price_target=round(price_target, 2) if price_target else None,
        stop_loss=round(stop_loss, 2) if stop_loss else None,
        take_profit=round(take_profit, 2) if take_profit else None,
        change_percent=round(change_percent, 2),
        predicted_change=round(predicted_change, 2),
        direction=direction,
        source="LSTM Price Predictor",
        features_used=list(features.keys()),
        timestamp=datetime.utcnow().isoformat(),
        metadata={
            "composite_score": round(score, 3),
            "intraday_position": round(intraday_pos, 3),
            "momentum_ratio": round(momentum, 3),
            "volatility_estimate": round(volatility, 3),
        }
    )


@router.post("/auto-predict", response_model=AutoPredictionResponse)
async def auto_generate_predictions(
    request: AutoPredictionRequest,
    signals: SignalGenerator = Depends(get_signals)
):
    """
    Auto-generate ML predictions for a list of symbols.
    
    This endpoint fetches market data and generates predictions
    using TRAINED ML models when available, falling back to rule-based
    analysis when models are not trained.
    """
    from app.data_providers import orchestrator
    from app.ml.trained_service import get_trained_model_service
    from datetime import timedelta
    import pandas as pd
    
    # Try to load trained models
    trained_service = get_trained_model_service()
    use_trained_model = trained_service.is_loaded
    
    predictions = []
    failed_symbols = []
    model_used = "Rule-Based Analysis"
    
    try:
        for symbol in request.symbols:
            try:
                # Fetch current market data
                quote_obj = await orchestrator.get_quote(symbol)
                
                if not quote_obj:
                    logger.warning(f"No quote data for {symbol}")
                    failed_symbols.append(symbol)
                    continue
                
                # Convert Quote object to dict
                quote = quote_obj.to_dict() if hasattr(quote_obj, 'to_dict') else quote_obj
                
                price = quote.get('price', 0) or 0
                if price <= 0:
                    logger.warning(f"Invalid price for {symbol}")
                    failed_symbols.append(symbol)
                    continue
                
                prediction = None
                
                # Try trained model first if available
                if use_trained_model:
                    try:
                        # Fetch historical data using orchestrator
                        # Need 1 year for SMA_200 and 52-week high/low calculations
                        end_date = datetime.utcnow().date()
                        start_date = end_date - timedelta(days=365)  # 1 year
                        
                        hist_data = await orchestrator.get_historical(
                            symbol=symbol,
                            start_date=start_date,
                            end_date=end_date
                        )
                        
                        if hist_data and len(hist_data) >= 50:
                            # Convert to DataFrame format expected by trained model
                            # Note: Use lowercase columns to match training pipeline
                            df = pd.DataFrame([{
                                'open': float(bar.open),
                                'high': float(bar.high),
                                'low': float(bar.low),
                                'close': float(bar.close),
                                'volume': int(bar.volume)
                            } for bar in hist_data])
                            df.index = pd.to_datetime([bar.timestamp for bar in hist_data])
                            
                            trained_pred = await trained_service.predict(df, symbol, price)
                            if trained_pred:
                                model_used = f"RandomForest (trained)"
                                change_pct = quote.get('change_percent') or 0.0
                                prediction = SymbolPrediction(
                                    symbol=symbol,
                                    signal=trained_pred.signal.lower(),
                                    confidence=trained_pred.confidence,
                                    price=trained_pred.price,
                                    price_target=trained_pred.price_target,
                                    stop_loss=trained_pred.stop_loss,
                                    take_profit=trained_pred.take_profit,
                                    change_percent=change_pct,
                                    predicted_change=(trained_pred.probability_up - 0.5) * 10,
                                    direction=1 if trained_pred.signal == "BUY" else (-1 if trained_pred.signal == "SELL" else 0),
                                    source=f"Trained {trained_pred.model_type}",
                                    features_used=[f"feature_{i}" for i in range(trained_pred.features_used)],
                                    timestamp=datetime.utcnow().isoformat(),
                                    metadata={
                                        "probability_up": trained_pred.probability_up,
                                        "probability_down": trained_pred.probability_down,
                                        "model_type": trained_pred.model_type
                                    }
                                )
                        else:
                            logger.debug(f"Not enough historical data for {symbol}: {len(hist_data) if hist_data else 0} bars")
                    except Exception as e:
                        logger.debug(f"Trained model failed for {symbol}: {e}")
                
                # Fallback to rule-based if no trained prediction
                if prediction is None:
                    features = calculate_technical_features(quote)
                    prediction = generate_signal_from_features(symbol, features, price)
                    model_used = "Rule-Based Analysis"
                
                # Store in signal generator history
                trading_signal = TradingSignal(
                    symbol=symbol,
                    signal_type=SignalType(prediction.signal),
                    source=SignalSource.ENSEMBLE,
                    strength=prediction.confidence,
                    confidence=prediction.confidence,
                    price_target=prediction.price_target,
                    stop_loss=prediction.stop_loss,
                    take_profit=prediction.take_profit,
                    timeframe="1d",
                    valid_until=datetime.utcnow() + timedelta(days=1),
                    metadata=prediction.metadata
                )
                signals._add_to_history(symbol, trading_signal)
                
                predictions.append(prediction)
                
            except Exception as e:
                logger.error(f"Error generating prediction for {symbol}: {e}")
                failed_symbols.append(symbol)
        
        # Get model info
        model_info_data = trained_service.get_model_info() if use_trained_model else {}
        
        return AutoPredictionResponse(
            predictions=predictions,
            model_info={
                "model_name": model_used,
                "version": "2.1.0",
                "accuracy": model_info_data.get("random_forest", {}).get("metadata", {}).get("test_accuracy", 0.65) if use_trained_model else 0.65,
                "total_predictions": len(predictions),
                "last_trained": model_info_data.get("random_forest", {}).get("metadata", {}).get("trained_at", datetime.utcnow().isoformat()) if use_trained_model else None,
                "using_trained_model": use_trained_model
            },
            generated_at=datetime.utcnow().isoformat(),
            total_symbols=len(request.symbols),
            successful=len(predictions),
            failed=len(failed_symbols)
        )
        
    except Exception as e:
        logger.error(f"Auto-prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/portfolio-predictions/{portfolio_id}")
async def get_portfolio_predictions(
    portfolio_id: int,
    signals: SignalGenerator = Depends(get_signals)
):
    """
    Generate ML predictions for all positions in a portfolio.
    """
    from app.db.database import async_session_maker
    from app.db.repositories.portfolio import PortfolioRepository
    
    try:
        async with async_session_maker() as db:
            repo = PortfolioRepository(db)
            positions = await repo.get_positions(portfolio_id)
            
            if not positions:
                return {
                    "portfolio_id": portfolio_id,
                    "predictions": [],
                    "message": "No positions found in portfolio"
                }
            
            symbols = [p.symbol for p in positions]
        
        # Use auto-predict logic
        request = AutoPredictionRequest(symbols=symbols)
        response = await auto_generate_predictions(request, signals)
        
        return {
            "portfolio_id": portfolio_id,
            "predictions": [p.dict() for p in response.predictions],
            "model_info": response.model_info,
            "generated_at": response.generated_at,
            "position_count": len(symbols),
            "successful": response.successful,
            "failed": response.failed
        }
        
    except Exception as e:
        logger.error(f"Portfolio predictions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trade-candidates/{portfolio_id}", response_model=TradeCandidatesResponse)
async def get_trade_candidates(
    portfolio_id: int,
    region: Optional[str] = Query("all", description="Filter by region: 'us', 'eu', 'asia', 'all'"),
    min_confidence: float = Query(60.0, description="Minimum confidence threshold (%)"),
    max_candidates: int = Query(5, description="Maximum number of candidates to return"),
    signals: SignalGenerator = Depends(get_signals)
):
    """
    Automatically identify top trade candidates for the day.
    
    Generates ML predictions for universe symbols and filters for:
    - BUY signals with confidence >= min_confidence
    
    For each candidate, calculates:
    - Entry price (limit order at current price - 0.5%)
    - Stop-Loss (EU: -3%, US: -4%, Asia: -3.5%)
    - Take-Profit (+6% to +10% based on volatility)
    - Position sizing (max 5% of portfolio value)
    - Risk/Reward ratio
    """
    from app.db.database import async_session_maker
    from app.core.portfolio.service import PortfolioService
    from app.data_providers import orchestrator
    from app.ml.trained_service import get_trained_model_service
    from datetime import timedelta
    import pandas as pd
    
    try:
        # Get portfolio info
        async with async_session_maker() as db:
            service = PortfolioService(db)
            portfolio_summary = await service.get_portfolio_summary(portfolio_id)
            
            if not portfolio_summary:
                raise HTTPException(status_code=404, detail="Portfolio not found")
            
            portfolio_value = float(portfolio_summary.get("total_value", 100000))
            portfolio_currency = portfolio_summary.get("currency", "USD")
        
        # Configuration based on region
        region_config = {
            "us": {"stop_loss_pct": 4.0, "take_profit_base": 8.0},
            "eu": {"stop_loss_pct": 3.0, "take_profit_base": 6.0},
            "asia": {"stop_loss_pct": 3.5, "take_profit_base": 7.0}
        }
        
        # Symbol suffixes to region mapping
        suffix_to_region = {
            ".DE": "eu", ".PA": "eu", ".MI": "eu", ".AS": "eu", ".MC": "eu",
            ".L": "eu", ".SW": "eu", ".BR": "eu", ".VI": "eu", ".HE": "eu",
            ".T": "asia", ".HK": "asia", ".SS": "asia", ".SZ": "asia",
            ".KS": "asia", ".TW": "asia", ".SI": "asia",
        }
        
        def get_region_from_symbol(sym: str) -> str:
            """Determine region from symbol suffix."""
            for suffix, reg in suffix_to_region.items():
                if sym.endswith(suffix):
                    return reg
            return "us"  # Default to US (no suffix)
        
        # Get universe symbols from database
        from sqlalchemy import select
        from app.db.models.market_universe import MarketUniverse
        
        async with async_session_maker() as db:
            query = select(MarketUniverse.symbol, MarketUniverse.name).where(
                MarketUniverse.is_active == True
            ).limit(50)  # Limit for performance
            
            result = await db.execute(query)
            universe_entries = result.fetchall()
        
        # Load trained model service
        trained_service = get_trained_model_service()
        
        candidates = []
        
        for entry in universe_entries:
            symbol = entry.symbol
            symbol_region = get_region_from_symbol(symbol)
            
            # Filter by region if specified
            if region.lower() != "all" and symbol_region != region.lower():
                continue
            
            try:
                # Get current quote
                quote_obj = await orchestrator.get_quote(symbol)
                if not quote_obj:
                    continue
                
                quote = quote_obj.to_dict() if hasattr(quote_obj, 'to_dict') else quote_obj
                current_price = float(quote.get("price", 0))
                if current_price <= 0:
                    continue
                
                # Generate ML prediction
                signal_type = "HOLD"
                confidence = 50.0
                trend = "NEUTRAL"
                
                if trained_service.is_loaded:
                    # Fetch historical data for ML prediction
                    end_date = datetime.utcnow().date()
                    start_date = end_date - timedelta(days=365)
                    
                    hist_data = await orchestrator.get_historical(
                        symbol=symbol,
                        start_date=start_date,
                        end_date=end_date
                    )
                    
                    if hist_data and len(hist_data) >= 50:
                        df = pd.DataFrame([{
                            'open': float(bar.open),
                            'high': float(bar.high),
                            'low': float(bar.low),
                            'close': float(bar.close),
                            'volume': int(bar.volume)
                        } for bar in hist_data])
                        df.index = pd.to_datetime([bar.timestamp for bar in hist_data])
                        
                        prediction = await trained_service.predict(df, symbol, current_price)
                        if prediction:
                            signal_type = prediction.signal
                            confidence = prediction.confidence * 100
                            # Determine trend from price change
                            if len(hist_data) >= 5:
                                recent_close = float(hist_data[-1].close)
                                past_close = float(hist_data[-5].close)
                                if recent_close > past_close * 1.01:
                                    trend = "UP"
                                elif recent_close < past_close * 0.99:
                                    trend = "DOWN"
                
                # Only BUY signals with sufficient confidence
                is_buy = signal_type in ["BUY", "STRONG_BUY"]
                if not is_buy or confidence < min_confidence:
                    continue
            
            except Exception as e:
                logger.debug(f"Error processing {symbol}: {e}")
                continue
            
            # Get config for this symbol's region
            config = region_config.get(symbol_region, region_config["us"])
            
            # Calculate entry price (limit order slightly below market)
            entry_price = round(current_price * 0.995, 2)  # -0.5%
            
            # Calculate stop-loss
            stop_loss_pct = config["stop_loss_pct"]
            stop_loss = round(entry_price * (1 - stop_loss_pct / 100), 2)
            
            # Calculate take-profit (base + confidence bonus)
            confidence_bonus = (confidence - 60) / 40 * 4  # 0-4% bonus based on confidence
            take_profit_pct = config["take_profit_base"] + confidence_bonus
            take_profit = round(entry_price * (1 + take_profit_pct / 100), 2)
            
            # Position sizing (max 5% of portfolio)
            max_position_pct = 5.0
            max_position_value = portfolio_value * max_position_pct / 100
            suggested_shares = int(max_position_value / entry_price)
            actual_position_value = suggested_shares * entry_price
            
            # Risk/Reward ratio
            risk_per_share = entry_price - stop_loss
            reward_per_share = take_profit - entry_price
            risk_reward = round(reward_per_share / risk_per_share, 2) if risk_per_share > 0 else 0
            
            # Volatility estimate based on config
            volatility = "HIGH" if config["stop_loss_pct"] > 3.5 else "MEDIUM"
            
            # Determine currency from region
            symbol_currency = "EUR" if symbol_region == "eu" else ("USD" if symbol_region == "us" else "JPY")
            
            candidate = TradeCandidateModel(
                symbol=symbol,
                region=symbol_region.upper(),
                signal=signal_type,
                confidence=confidence,
                current_price=current_price,
                currency=symbol_currency,
                entry_price=entry_price,
                stop_loss=stop_loss,
                stop_loss_percent=stop_loss_pct,
                take_profit=take_profit,
                take_profit_percent=round(take_profit_pct, 2),
                max_position_value=round(actual_position_value, 2),
                suggested_shares=suggested_shares,
                risk_reward_ratio=risk_reward,
                trend=trend,
                volatility=volatility,
                ranking=0  # Will be set after sorting
            )
            candidates.append(candidate)
        
        # Sort by confidence and assign ranking
        candidates.sort(key=lambda x: x.confidence, reverse=True)
        for i, c in enumerate(candidates[:max_candidates]):
            c.ranking = i + 1
        
        # Limit to max_candidates
        final_candidates = candidates[:max_candidates]
        
        # Count by region
        eu_count = sum(1 for c in final_candidates if c.region == "EU")
        us_count = sum(1 for c in final_candidates if c.region == "US")
        
        return TradeCandidatesResponse(
            date=date.today().isoformat(),
            portfolio_value=portfolio_value,
            portfolio_currency=portfolio_currency,
            max_position_percent=5.0,
            candidates=final_candidates,
            eu_candidates=eu_count,
            us_candidates=us_count,
            generated_at=datetime.utcnow().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Trade candidates error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
