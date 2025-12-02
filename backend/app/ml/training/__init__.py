"""
ML Training Package

Contains training infrastructure:
- Training pipeline orchestration
- Cross-validation framework
- Hyperparameter optimization
- Model persistence
"""
from .pipeline import (
    TrainingPipeline,
    TrainingConfig,
    TrainingJob,
    TrainingStatus,
    TrainingMetrics,
    DataSplit,
    TimeSeriesCrossValidator,
    HyperparameterOptimizer,
    train_price_predictor
)
from .cross_validation import (
    CrossValidator,
    CVResult,
    CVSplit,
    BaseCrossValidator,
    TimeSeriesSplit,
    WalkForwardCV,
    PurgedKFold,
    CombinatorialPurgedCV,
    create_cv_strategy
)

__all__ = [
    # Pipeline
    'TrainingPipeline',
    'TrainingConfig',
    'TrainingJob',
    'TrainingStatus',
    'TrainingMetrics',
    'DataSplit',
    'TimeSeriesCrossValidator',
    'HyperparameterOptimizer',
    'train_price_predictor',
    # Cross-validation
    'CrossValidator',
    'CVResult',
    'CVSplit',
    'BaseCrossValidator',
    'TimeSeriesSplit',
    'WalkForwardCV',
    'PurgedKFold',
    'CombinatorialPurgedCV',
    'create_cv_strategy'
]
