"""
ML Inference Service

Production inference system for ML models:
- Model loading and caching
- Batch and streaming predictions
- Feature preparation
- Prediction aggregation
"""
import numpy as np
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import asyncio
from abc import ABC, abstractmethod
from loguru import logger

# Import models
try:
    from ..models import (
        LSTMPricePredictor,
        RandomForestTrendClassifier,
        GARCHVolatilityModel,
        GradientBoostingRiskScorer,
        VotingEnsemble,
        ModelRegistry,
        get_registry,
        ModelStage
    )
except ImportError:
    LSTMPricePredictor = None
    RandomForestTrendClassifier = None
    GARCHVolatilityModel = None
    GradientBoostingRiskScorer = None


class PredictionType(str, Enum):
    """Type of prediction."""
    PRICE_DIRECTION = "price_direction"
    TREND = "trend"
    VOLATILITY = "volatility"
    RISK = "risk"
    ENSEMBLE = "ensemble"


@dataclass
class PredictionRequest:
    """Request for predictions."""
    symbol: str
    features: np.ndarray
    prediction_types: List[PredictionType] = field(default_factory=lambda: [PredictionType.PRICE_DIRECTION])
    horizon: int = 1  # Prediction horizon in days
    timestamp: datetime = field(default_factory=datetime.utcnow)
    request_id: str = ""
    
    def __post_init__(self):
        if not self.request_id:
            self.request_id = f"{self.symbol}_{self.timestamp.strftime('%Y%m%d%H%M%S')}"


@dataclass
class PredictionResponse:
    """Response with predictions."""
    request_id: str
    symbol: str
    predictions: Dict[str, Any]
    confidence: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    latency_ms: float = 0.0
    model_versions: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            'request_id': self.request_id,
            'symbol': self.symbol,
            'predictions': self.predictions,
            'confidence': self.confidence,
            'timestamp': self.timestamp.isoformat(),
            'latency_ms': self.latency_ms,
            'model_versions': self.model_versions
        }


class ModelCache:
    """Cache for loaded models."""
    
    def __init__(self, max_size: int = 10, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl = timedelta(seconds=ttl_seconds)
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_times: Dict[str, datetime] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get model from cache."""
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        if datetime.utcnow() - entry['loaded_at'] > self.ttl:
            # Expired
            del self._cache[key]
            return None
        
        self._access_times[key] = datetime.utcnow()
        return entry['model']
    
    def put(self, key: str, model: Any, version: str = ""):
        """Add model to cache."""
        # Evict if needed
        if len(self._cache) >= self.max_size:
            self._evict_oldest()
        
        self._cache[key] = {
            'model': model,
            'version': version,
            'loaded_at': datetime.utcnow()
        }
        self._access_times[key] = datetime.utcnow()
    
    def _evict_oldest(self):
        """Evict least recently used model."""
        if not self._access_times:
            return
        
        oldest_key = min(self._access_times, key=self._access_times.get)
        del self._cache[oldest_key]
        del self._access_times[oldest_key]
    
    def clear(self):
        """Clear cache."""
        self._cache.clear()
        self._access_times.clear()


class InferenceService:
    """
    Production inference service.
    
    Features:
    - Lazy model loading with caching
    - Batch predictions
    - Multiple model types
    - Ensemble predictions
    """
    
    def __init__(
        self,
        registry: Optional[ModelRegistry] = None,
        cache_size: int = 10,
        cache_ttl: int = 3600
    ):
        self.registry = registry
        self.cache = ModelCache(max_size=cache_size, ttl_seconds=cache_ttl)
        
        # Model configurations
        self.model_configs = {
            PredictionType.PRICE_DIRECTION: {
                'name': 'price_predictor',
                'class': LSTMPricePredictor
            },
            PredictionType.TREND: {
                'name': 'trend_classifier',
                'class': RandomForestTrendClassifier
            },
            PredictionType.VOLATILITY: {
                'name': 'volatility_model',
                'class': GARCHVolatilityModel
            },
            PredictionType.RISK: {
                'name': 'risk_scorer',
                'class': GradientBoostingRiskScorer
            }
        }
        
        # Track loaded versions
        self.loaded_versions: Dict[str, str] = {}
    
    def _get_model(
        self,
        prediction_type: PredictionType,
        stage: ModelStage = ModelStage.PRODUCTION
    ) -> Optional[Any]:
        """Load model from registry or cache."""
        config = self.model_configs.get(prediction_type)
        if not config:
            return None
        
        cache_key = f"{config['name']}_{stage.value}"
        
        # Check cache
        model = self.cache.get(cache_key)
        if model:
            return model
        
        # Load from registry
        if self.registry:
            try:
                model = self.registry.load_model(config['name'], stage=stage)
                version = self.registry.get_model_version(config['name'])
                self.cache.put(cache_key, model, version.version if version else "")
                self.loaded_versions[config['name']] = version.version if version else ""
                logger.info(f"Loaded {config['name']} from registry")
                return model
            except Exception as e:
                logger.warning(f"Could not load {config['name']} from registry: {e}")
        
        # Create new instance as fallback
        if config['class']:
            try:
                model = config['class']()
                self.cache.put(cache_key, model, "default")
                logger.info(f"Created new {config['name']} instance")
                return model
            except Exception as e:
                logger.error(f"Could not create {config['name']}: {e}")
        
        return None
    
    def predict(
        self,
        request: PredictionRequest
    ) -> PredictionResponse:
        """
        Make predictions for a single request.
        
        Args:
            request: Prediction request
            
        Returns:
            PredictionResponse with results
        """
        start_time = datetime.utcnow()
        predictions = {}
        confidences = []
        model_versions = {}
        
        for pred_type in request.prediction_types:
            model = self._get_model(pred_type)
            
            if model is None:
                predictions[pred_type.value] = None
                continue
            
            try:
                # Make prediction
                features = request.features
                if features.ndim == 1:
                    features = features.reshape(1, -1)
                
                if hasattr(model, 'predict'):
                    result = model.predict(features)
                    
                    # Handle different result formats
                    if isinstance(result, list) and len(result) > 0:
                        pred = result[0]
                    else:
                        pred = result
                    
                    # Extract prediction value and confidence
                    if hasattr(pred, 'to_dict'):
                        predictions[pred_type.value] = pred.to_dict()
                        if hasattr(pred, 'confidence'):
                            confidences.append(pred.confidence)
                    elif hasattr(pred, '__dict__'):
                        predictions[pred_type.value] = vars(pred)
                        if hasattr(pred, 'confidence'):
                            confidences.append(pred.confidence)
                    else:
                        predictions[pred_type.value] = pred
                        confidences.append(0.5)
                
                # Track version
                config = self.model_configs.get(pred_type)
                if config and config['name'] in self.loaded_versions:
                    model_versions[pred_type.value] = self.loaded_versions[config['name']]
                    
            except Exception as e:
                logger.error(f"Prediction error for {pred_type.value}: {e}")
                predictions[pred_type.value] = {'error': str(e)}
        
        # Calculate overall confidence
        overall_confidence = np.mean(confidences) if confidences else 0.5
        
        # Calculate latency
        latency = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return PredictionResponse(
            request_id=request.request_id,
            symbol=request.symbol,
            predictions=predictions,
            confidence=overall_confidence,
            latency_ms=latency,
            model_versions=model_versions
        )
    
    def predict_batch(
        self,
        requests: List[PredictionRequest]
    ) -> List[PredictionResponse]:
        """
        Make predictions for multiple requests.
        
        Args:
            requests: List of prediction requests
            
        Returns:
            List of prediction responses
        """
        return [self.predict(req) for req in requests]
    
    async def predict_async(
        self,
        request: PredictionRequest
    ) -> PredictionResponse:
        """Async prediction."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.predict, request)
    
    async def predict_batch_async(
        self,
        requests: List[PredictionRequest]
    ) -> List[PredictionResponse]:
        """Async batch predictions."""
        tasks = [self.predict_async(req) for req in requests]
        return await asyncio.gather(*tasks)
    
    def get_ensemble_prediction(
        self,
        symbol: str,
        features: np.ndarray
    ) -> PredictionResponse:
        """
        Get ensemble prediction combining all models.
        
        Args:
            symbol: Stock symbol
            features: Input features
            
        Returns:
            Combined prediction
        """
        # Get all individual predictions
        request = PredictionRequest(
            symbol=symbol,
            features=features,
            prediction_types=[
                PredictionType.PRICE_DIRECTION,
                PredictionType.TREND,
                PredictionType.VOLATILITY,
                PredictionType.RISK
            ]
        )
        
        response = self.predict(request)
        
        # Create ensemble summary
        ensemble_result = {
            'individual_predictions': response.predictions,
            'recommendation': self._generate_recommendation(response.predictions),
            'combined_confidence': response.confidence
        }
        
        response.predictions['ensemble'] = ensemble_result
        
        return response
    
    def _generate_recommendation(
        self,
        predictions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate trading recommendation from predictions."""
        scores = {
            'bullish': 0,
            'bearish': 0,
            'neutral': 0
        }
        
        # Price direction
        price_pred = predictions.get('price_direction', {})
        if isinstance(price_pred, dict):
            direction = price_pred.get('direction', '')
            if 'up' in str(direction).lower():
                scores['bullish'] += 2
            elif 'down' in str(direction).lower():
                scores['bearish'] += 2
            else:
                scores['neutral'] += 1
        
        # Trend
        trend_pred = predictions.get('trend', {})
        if isinstance(trend_pred, dict):
            trend = trend_pred.get('trend', '')
            if 'up' in str(trend).lower():
                scores['bullish'] += 1.5 if 'strong' in str(trend).lower() else 1
            elif 'down' in str(trend).lower():
                scores['bearish'] += 1.5 if 'strong' in str(trend).lower() else 1
            else:
                scores['neutral'] += 1
        
        # Risk
        risk_pred = predictions.get('risk', {})
        if isinstance(risk_pred, dict):
            risk_level = risk_pred.get('risk_level', '')
            if 'low' in str(risk_level).lower():
                scores['bullish'] += 0.5
            elif 'high' in str(risk_level).lower() or 'extreme' in str(risk_level).lower():
                scores['bearish'] += 0.5
        
        # Determine recommendation
        max_score = max(scores.values())
        if scores['bullish'] == max_score and scores['bullish'] > scores['neutral']:
            action = 'BUY'
            strength = 'strong' if scores['bullish'] >= 3 else 'moderate'
        elif scores['bearish'] == max_score and scores['bearish'] > scores['neutral']:
            action = 'SELL'
            strength = 'strong' if scores['bearish'] >= 3 else 'moderate'
        else:
            action = 'HOLD'
            strength = 'neutral'
        
        return {
            'action': action,
            'strength': strength,
            'scores': scores,
            'reasoning': self._generate_reasoning(predictions, action)
        }
    
    def _generate_reasoning(
        self,
        predictions: Dict[str, Any],
        action: str
    ) -> List[str]:
        """Generate reasoning for recommendation."""
        reasons = []
        
        price_pred = predictions.get('price_direction', {})
        if isinstance(price_pred, dict) and 'direction' in price_pred:
            reasons.append(f"Price predicted to move {price_pred['direction']}")
        
        trend_pred = predictions.get('trend', {})
        if isinstance(trend_pred, dict) and 'trend' in trend_pred:
            reasons.append(f"Current trend: {trend_pred['trend']}")
        
        risk_pred = predictions.get('risk', {})
        if isinstance(risk_pred, dict) and 'risk_level' in risk_pred:
            reasons.append(f"Risk level: {risk_pred['risk_level']}")
        
        vol_pred = predictions.get('volatility', {})
        if isinstance(vol_pred, dict) and 'forecast' in vol_pred:
            reasons.append(f"Expected volatility: {vol_pred.get('forecast', 'N/A')}")
        
        return reasons
    
    def health_check(self) -> Dict[str, Any]:
        """Check service health."""
        status = {
            'status': 'healthy',
            'models_loaded': len(self.cache._cache),
            'models': {}
        }
        
        for pred_type in PredictionType:
            if pred_type == PredictionType.ENSEMBLE:
                continue
            
            model = self._get_model(pred_type)
            config = self.model_configs.get(pred_type, {})
            status['models'][pred_type.value] = {
                'loaded': model is not None,
                'name': config.get('name', ''),
                'version': self.loaded_versions.get(config.get('name', ''), 'N/A')
            }
        
        return status


# Global inference service instance
_inference_service: Optional[InferenceService] = None


def get_inference_service() -> InferenceService:
    """Get or create global inference service."""
    global _inference_service
    if _inference_service is None:
        _inference_service = InferenceService()
    return _inference_service
