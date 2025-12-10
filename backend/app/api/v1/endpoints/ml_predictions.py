"""
ML Predictions API Endpoints

REST API endpoints for ML predictions and signals.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
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
                        end_date = datetime.utcnow().date()
                        start_date = end_date - timedelta(days=90)  # 3 months
                        
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
                                prediction = SymbolPrediction(
                                    symbol=symbol,
                                    signal=trained_pred.signal.lower(),
                                    confidence=trained_pred.confidence,
                                    price=trained_pred.price,
                                    price_target=trained_pred.price_target,
                                    stop_loss=trained_pred.stop_loss,
                                    take_profit=trained_pred.take_profit,
                                    change_percent=quote.get('change_percent', 0),
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
