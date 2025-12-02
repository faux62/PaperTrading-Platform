"""
ML Training Package

Contains training infrastructure:
- Training pipeline orchestration
- Cross-validation framework
- Hyperparameter optimization
- Backtesting framework
- Model evaluation
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
from .backtester import (
    Backtester,
    WalkForwardBacktester,
    BacktestConfig,
    BacktestMetrics,
    BaseStrategy,
    MLStrategy,
    Order,
    OrderSide,
    OrderType,
    Position,
    Trade,
    run_backtest
)
from .evaluation import (
    ModelEvaluator,
    EvaluationResult,
    ClassificationMetrics,
    RegressionMetrics,
    TradingMetrics,
    MetricType,
    compare_models
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
    'create_cv_strategy',
    # Backtesting
    'Backtester',
    'WalkForwardBacktester',
    'BacktestConfig',
    'BacktestMetrics',
    'BaseStrategy',
    'MLStrategy',
    'Order',
    'OrderSide',
    'OrderType',
    'Position',
    'Trade',
    'run_backtest',
    # Evaluation
    'ModelEvaluator',
    'EvaluationResult',
    'ClassificationMetrics',
    'RegressionMetrics',
    'TradingMetrics',
    'MetricType',
    'compare_models'
]
