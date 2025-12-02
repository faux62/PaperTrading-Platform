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
from .volatility_model import (
    GARCHVolatilityModel,
    VolatilityForecast,
    VolatilityRegime,
    GARCHConfig,
    RealizedVolatilityEstimator,
    VolatilitySurfaceModel
)
from .risk_scorer import (
    GradientBoostingRiskScorer,
    RiskScore,
    RiskLevel,
    RiskCategory,
    RiskScorerConfig
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
    'TrendClassifierConfig',
    # Volatility Model
    'GARCHVolatilityModel',
    'VolatilityForecast',
    'VolatilityRegime',
    'GARCHConfig',
    'RealizedVolatilityEstimator',
    'VolatilitySurfaceModel',
    # Risk Scorer
    'GradientBoostingRiskScorer',
    'RiskScore',
    'RiskLevel',
    'RiskCategory',
    'RiskScorerConfig'
]
