"""
ML Predictions API Endpoints

REST API endpoints for ML predictions and signals.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
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
    """
    Get currently active (valid) signals.
    
    First checks Redis for cached predictions from ML job,
    then falls back to in-memory signal history.
    """
    import json
    from app.db.redis_client import redis_client
    
    try:
        # Get active signals from Redis
        active_signals_raw = await redis_client.client.get("ml:active_signals")
        
        if active_signals_raw:
            active_signals = json.loads(active_signals_raw)
            
            # Filter by symbol if specified
            if symbol:
                active_signals = [s for s in active_signals if s.get('symbol') == symbol]
            
            return active_signals
            
    except Exception as e:
        logger.warning(f"Redis lookup failed, falling back to in-memory: {e}")
    
    # Fallback to in-memory signals
    active = signals.get_active_signals(symbol)
    return [s.to_dict() for s in active]


@router.get("/predictions/{symbol}")
async def get_prediction(symbol: str):
    """Get the latest ML prediction for a symbol."""
    import json
    from app.db.redis_client import redis_client
    
    try:
        # Get prediction from Redis
        prediction_raw = await redis_client.client.get(f"ml:predictions:{symbol}")
        
        if prediction_raw:
            return json.loads(prediction_raw)
        
        raise HTTPException(
            status_code=404,
            detail=f"No prediction found for {symbol}. Run the ML job first."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching prediction for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/predictions")
async def get_all_predictions(
    symbols: Optional[str] = Query(default=None, description="Comma-separated symbols")
):
    """Get ML predictions for multiple symbols."""
    import json
    from app.db.redis_client import redis_client
    
    try:
        predictions = []
        
        if symbols:
            symbol_list = [s.strip().upper() for s in symbols.split(',')]
        else:
            # Get all predictions from active signals
            active_raw = await redis_client.client.get("ml:active_signals")
            if active_raw:
                active = json.loads(active_raw)
                symbol_list = [s['symbol'] for s in active]
            else:
                return []
        
        # Fetch each prediction
        for symbol in symbol_list:
            pred_raw = await redis_client.client.get(f"ml:predictions:{symbol}")
            if pred_raw:
                predictions.append(json.loads(pred_raw))
        
        return predictions
        
    except Exception as e:
        logger.error(f"Error fetching predictions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/job/run")
async def run_ml_job(force: bool = Query(default=False)):
    """
    Manually trigger the ML predictions job.
    
    This will generate predictions for all portfolio symbols,
    watchlist symbols, and popular stocks.
    """
    from app.scheduler.jobs import run_ml_predictions_job
    
    try:
        result = await run_ml_predictions_job(force=force)
        return result
    except Exception as e:
        logger.error(f"ML job error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/job/status")
async def get_ml_job_status():
    """Get the status of the ML predictions job."""
    from app.scheduler.jobs import get_ml_predictions_job
    import json
    from app.db.redis_client import redis_client
    
    try:
        job = get_ml_predictions_job()
        
        # Get active signals count
        active_raw = await redis_client.client.get("ml:active_signals")
        active_count = len(json.loads(active_raw)) if active_raw else 0
        
        return {
            'last_run': job._last_run.isoformat() if job._last_run else None,
            'is_running': job._running,
            'active_predictions': active_count
        }
        
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
