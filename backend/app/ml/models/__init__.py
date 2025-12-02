"""
ML Models Package

Contains machine learning models for:
- Price direction prediction (LSTM)
- Trend classification (Random Forest)
- Volatility modeling (GARCH/Prophet)
- Risk scoring (Gradient Boosting)
- Ensemble methods
- Model registry
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
from .ensemble import (
    VotingEnsemble,
    StackingEnsemble,
    DynamicEnsemble,
    EnsemblePrediction,
    EnsembleMethod,
    ModelPerformance,
    create_ensemble
)
from .registry import (
    ModelRegistry,
    ModelVersion,
    RegisteredModel,
    ModelStage,
    ModelStatus,
    ModelMetrics,
    LocalArtifactStore,
    get_registry
)
from .portfolio_optimizer import (
    PortfolioOptimizer,
    RiskParityOptimizer,
    OptimizedPortfolio,
    OptimizationObjective,
    PortfolioConstraints
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
    'RiskScorerConfig',
    # Ensemble Methods
    'VotingEnsemble',
    'StackingEnsemble',
    'DynamicEnsemble',
    'EnsemblePrediction',
    'EnsembleMethod',
    'ModelPerformance',
    'create_ensemble',
    # Model Registry
    'ModelRegistry',
    'ModelVersion',
    'RegisteredModel',
    'ModelStage',
    'ModelStatus',
    'ModelMetrics',
    'LocalArtifactStore',
    'get_registry',
    # Portfolio Optimizer
    'PortfolioOptimizer',
    'RiskParityOptimizer',
    'OptimizedPortfolio',
    'OptimizationObjective',
    'PortfolioConstraints'
]
