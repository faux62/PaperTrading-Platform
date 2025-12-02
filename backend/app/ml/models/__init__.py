"""
ML Models Package

Contains machine learning models for:
- Price direction prediction (LSTM)
- Trend classification (Random Forest)
- Volatility modeling (GARCH/Prophet)
- Risk scoring (Gradient Boosting)
"""
from .price_predictor import (
    LSTMPricePredictor,
    EnsemblePricePredictor,
    PredictionResult,
    PredictionDirection,
    ModelConfig
)
from .trend_classifier import (
    RandomForestTrendClassifier,
    GradientBoostingTrendClassifier,
    TrendPrediction,
    TrendType,
    TrendClassifierConfig
)

__all__ = [
    # Price Predictor
    'LSTMPricePredictor',
    'EnsemblePricePredictor',
    'PredictionResult',
    'PredictionDirection',
    'ModelConfig',
    # Trend Classifier
    'RandomForestTrendClassifier',
    'GradientBoostingTrendClassifier',
    'TrendPrediction',
    'TrendType',
    'TrendClassifierConfig'
]
