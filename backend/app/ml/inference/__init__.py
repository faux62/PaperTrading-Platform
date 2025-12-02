"""
ML Inference Package

Contains inference and signal generation:
- Prediction service
- Signal generator
- Model serving
"""
from .predictor import (
    InferenceService,
    PredictionRequest,
    PredictionResponse,
    PredictionType,
    ModelCache,
    get_inference_service
)
from .signal_generator import (
    SignalGenerator,
    TradingSignal,
    AggregatedSignal,
    SignalType,
    SignalSource,
    get_signal_generator
)

__all__ = [
    # Inference Service
    'InferenceService',
    'PredictionRequest',
    'PredictionResponse',
    'PredictionType',
    'ModelCache',
    'get_inference_service',
    # Signal Generator
    'SignalGenerator',
    'TradingSignal',
    'AggregatedSignal',
    'SignalType',
    'SignalSource',
    'get_signal_generator'
]
