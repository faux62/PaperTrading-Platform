"""
Training Pipeline for ML Models

Orchestrates the full training workflow:
- Data loading and preparation
- Feature engineering
- Model training with cross-validation
- Hyperparameter optimization
- Model evaluation and selection
- Model persistence
"""
import numpy as np
from typing import Optional, List, Dict, Any, Callable, Type
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import json
from loguru import logger


class TrainingStatus(str, Enum):
    """Training job status."""
    PENDING = "pending"
    PREPARING = "preparing"
    TRAINING = "training"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DataSplit:
    """Train/validation/test data split configuration."""
    train_ratio: float = 0.7
    val_ratio: float = 0.15
    test_ratio: float = 0.15
    shuffle: bool = False  # Time series shouldn't be shuffled
    stratify: bool = True
    
    def __post_init__(self):
        total = self.train_ratio + self.val_ratio + self.test_ratio
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Split ratios must sum to 1.0, got {total}")


@dataclass
class TrainingConfig:
    """Configuration for training pipeline."""
    # Data
    symbols: List[str] = field(default_factory=lambda: ['AAPL', 'MSFT', 'GOOGL'])
    start_date: str = "2020-01-01"
    end_date: str = "2024-12-01"
    data_split: DataSplit = field(default_factory=DataSplit)
    
    # Features
    feature_groups: List[str] = field(default_factory=lambda: ['technical', 'fundamental', 'market'])
    feature_selection_k: int = 30  # Top K features to use
    
    # Training
    n_epochs: int = 100
    batch_size: int = 32
    learning_rate: float = 0.001
    early_stopping_patience: int = 10
    
    # Cross-validation
    use_cv: bool = True
    n_cv_folds: int = 5
    cv_type: str = "time_series"  # "time_series" or "kfold"
    
    # Hyperparameter optimization
    use_hpo: bool = False
    hpo_trials: int = 20
    
    # Output
    model_output_dir: str = "models/trained"
    save_checkpoints: bool = True
    
    def to_dict(self) -> dict:
        return {
            'symbols': self.symbols,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'data_split': {
                'train_ratio': self.data_split.train_ratio,
                'val_ratio': self.data_split.val_ratio,
                'test_ratio': self.data_split.test_ratio
            },
            'feature_groups': self.feature_groups,
            'feature_selection_k': self.feature_selection_k,
            'n_epochs': self.n_epochs,
            'batch_size': self.batch_size,
            'learning_rate': self.learning_rate,
            'use_cv': self.use_cv,
            'n_cv_folds': self.n_cv_folds,
            'model_output_dir': self.model_output_dir
        }


@dataclass
class TrainingMetrics:
    """Metrics collected during training."""
    train_loss: List[float] = field(default_factory=list)
    val_loss: List[float] = field(default_factory=list)
    train_accuracy: List[float] = field(default_factory=list)
    val_accuracy: List[float] = field(default_factory=list)
    
    # Final evaluation metrics
    test_accuracy: Optional[float] = None
    test_precision: Optional[float] = None
    test_recall: Optional[float] = None
    test_f1: Optional[float] = None
    test_roc_auc: Optional[float] = None
    
    # Cross-validation metrics
    cv_scores: List[float] = field(default_factory=list)
    cv_mean: Optional[float] = None
    cv_std: Optional[float] = None
    
    def to_dict(self) -> dict:
        return {
            'train_loss': self.train_loss,
            'val_loss': self.val_loss,
            'train_accuracy': self.train_accuracy,
            'val_accuracy': self.val_accuracy,
            'test_accuracy': self.test_accuracy,
            'test_precision': self.test_precision,
            'test_recall': self.test_recall,
            'test_f1': self.test_f1,
            'test_roc_auc': self.test_roc_auc,
            'cv_scores': self.cv_scores,
            'cv_mean': self.cv_mean,
            'cv_std': self.cv_std
        }


@dataclass 
class TrainingJob:
    """Represents a training job."""
    job_id: str
    model_type: str
    config: TrainingConfig
    status: TrainingStatus = TrainingStatus.PENDING
    metrics: TrainingMetrics = field(default_factory=TrainingMetrics)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    model_path: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'job_id': self.job_id,
            'model_type': self.model_type,
            'config': self.config.to_dict(),
            'status': self.status.value,
            'metrics': self.metrics.to_dict(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error_message': self.error_message,
            'model_path': self.model_path
        }


class TimeSeriesCrossValidator:
    """
    Time series cross-validation with expanding or sliding window.
    """
    
    def __init__(
        self,
        n_splits: int = 5,
        test_size: Optional[int] = None,
        gap: int = 0,
        expanding: bool = True
    ):
        """
        Args:
            n_splits: Number of CV folds
            test_size: Size of test set in each fold
            gap: Gap between train and test (to avoid look-ahead bias)
            expanding: If True, use expanding window; if False, use sliding window
        """
        self.n_splits = n_splits
        self.test_size = test_size
        self.gap = gap
        self.expanding = expanding
    
    def split(self, X: np.ndarray):
        """
        Generate train/test indices for time series CV.
        
        Yields:
            Tuple of (train_indices, test_indices)
        """
        n_samples = len(X)
        
        if self.test_size is None:
            test_size = n_samples // (self.n_splits + 1)
        else:
            test_size = self.test_size
        
        # Calculate minimum training size
        min_train_size = n_samples // (self.n_splits + 1)
        
        for fold in range(self.n_splits):
            if self.expanding:
                # Expanding window: training set grows with each fold
                train_end = min_train_size + fold * test_size
            else:
                # Sliding window: fixed training size
                train_start = fold * test_size
                train_end = train_start + min_train_size
            
            test_start = train_end + self.gap
            test_end = min(test_start + test_size, n_samples)
            
            if test_end <= test_start:
                break
            
            if self.expanding:
                train_indices = np.arange(0, train_end)
            else:
                train_indices = np.arange(train_start, train_end)
            
            test_indices = np.arange(test_start, test_end)
            
            yield train_indices, test_indices


class TrainingPipeline:
    """
    Main training pipeline orchestrator.
    """
    
    def __init__(self, config: Optional[TrainingConfig] = None):
        self.config = config or TrainingConfig()
        self.jobs: Dict[str, TrainingJob] = {}
        self.current_job: Optional[TrainingJob] = None
        
        # Callbacks for progress reporting
        self.on_epoch_end: Optional[Callable] = None
        self.on_fold_end: Optional[Callable] = None
        self.on_training_complete: Optional[Callable] = None
    
    def create_job(self, model_type: str) -> TrainingJob:
        """Create a new training job."""
        import uuid
        
        job_id = str(uuid.uuid4())[:8]
        job = TrainingJob(
            job_id=job_id,
            model_type=model_type,
            config=self.config
        )
        self.jobs[job_id] = job
        
        logger.info(f"Created training job {job_id} for {model_type}")
        return job
    
    def load_data(
        self,
        symbols: Optional[List[str]] = None
    ) -> tuple[np.ndarray, np.ndarray, List[str]]:
        """
        Load and prepare data for training.
        
        Returns:
            Tuple of (features, targets, feature_names)
        """
        symbols = symbols or self.config.symbols
        
        logger.info(f"Loading data for {len(symbols)} symbols")
        
        # In production, this would use FeatureStore
        # For now, generate synthetic data
        n_samples_per_symbol = 500
        n_features = 50
        
        all_features = []
        all_targets = []
        
        np.random.seed(42)
        
        for symbol in symbols:
            # Generate synthetic features
            features = np.random.randn(n_samples_per_symbol, n_features)
            
            # Generate targets with some feature correlation
            signal = 0.1 * features[:, 0] + 0.05 * features[:, 1] + np.random.randn(n_samples_per_symbol) * 0.5
            targets = (signal > 0).astype(int)
            
            all_features.append(features)
            all_targets.append(targets)
        
        X = np.vstack(all_features)
        y = np.concatenate(all_targets)
        
        # Feature names
        feature_names = [
            'rsi_14', 'macd_histogram', 'bb_percent_b', 'atr_percent', 'adx_14',
            'momentum_10', 'volume_ratio', 'mfi_14', 'price_vs_sma_20', 'price_vs_sma_50',
            'stochastic_k', 'williams_r', 'cci_20', 'roc_10', 'obv_trend',
            'pe_ratio', 'pb_ratio', 'roe', 'debt_to_equity', 'revenue_growth',
            'earnings_growth', 'profit_margin', 'current_ratio', 'dividend_yield', 'peg_ratio',
            'spy_correlation', 'spy_beta', 'sector_rs', 'vix_level', 'market_regime',
        ] + [f'feature_{i}' for i in range(30, 50)]
        
        logger.info(f"Loaded data: {X.shape[0]} samples, {X.shape[1]} features")
        
        return X, y, feature_names[:n_features]
    
    def select_features(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: List[str],
        k: Optional[int] = None
    ) -> tuple[np.ndarray, List[str]]:
        """
        Select top K features using mutual information.
        
        Returns:
            Tuple of (selected_features, selected_feature_names)
        """
        k = k or self.config.feature_selection_k
        
        try:
            from sklearn.feature_selection import mutual_info_classif, SelectKBest
            
            selector = SelectKBest(mutual_info_classif, k=min(k, X.shape[1]))
            X_selected = selector.fit_transform(X, y)
            
            # Get selected feature names
            selected_mask = selector.get_support()
            selected_names = [name for name, selected in zip(feature_names, selected_mask) if selected]
            
            logger.info(f"Selected {len(selected_names)} features")
            
            return X_selected, selected_names
        except ImportError:
            logger.warning("sklearn not available, using all features")
            return X, feature_names
    
    def split_data(
        self,
        X: np.ndarray,
        y: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Split data into train/validation/test sets.
        
        Returns:
            Tuple of (X_train, X_val, X_test, y_train, y_val, y_test)
        """
        split = self.config.data_split
        n_samples = len(X)
        
        train_end = int(n_samples * split.train_ratio)
        val_end = train_end + int(n_samples * split.val_ratio)
        
        X_train = X[:train_end]
        y_train = y[:train_end]
        
        X_val = X[train_end:val_end]
        y_val = y[train_end:val_end]
        
        X_test = X[val_end:]
        y_test = y[val_end:]
        
        logger.info(f"Data split: train={len(X_train)}, val={len(X_val)}, test={len(X_test)}")
        
        return X_train, X_val, X_test, y_train, y_val, y_test
    
    def cross_validate(
        self,
        model_class: Type,
        X: np.ndarray,
        y: np.ndarray,
        model_kwargs: Optional[Dict] = None
    ) -> List[float]:
        """
        Perform time series cross-validation.
        
        Returns:
            List of scores for each fold
        """
        model_kwargs = model_kwargs or {}
        cv = TimeSeriesCrossValidator(
            n_splits=self.config.n_cv_folds,
            gap=5  # 5-day gap to avoid look-ahead
        )
        
        scores = []
        
        for fold, (train_idx, test_idx) in enumerate(cv.split(X)):
            logger.info(f"CV Fold {fold + 1}/{self.config.n_cv_folds}")
            
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]
            
            # Create and train model
            model = model_class(**model_kwargs)
            model.fit(X_train, y_train, verbose=0)
            
            # Evaluate
            metrics = model.evaluate(X_test, y_test)
            score = metrics.get('roc_auc', metrics.get('accuracy', 0.5))
            scores.append(score)
            
            logger.info(f"Fold {fold + 1} score: {score:.4f}")
            
            if self.on_fold_end:
                self.on_fold_end(fold, score)
        
        return scores
    
    def train_model(
        self,
        model_class: Type,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        model_kwargs: Optional[Dict] = None
    ) -> Any:
        """
        Train a single model.
        
        Returns:
            Trained model instance
        """
        model_kwargs = model_kwargs or {}
        model = model_class(**model_kwargs)
        
        # Train
        history = model.fit(X_train, y_train, X_val, y_val)
        
        # Store training history in metrics
        if self.current_job:
            self.current_job.metrics.train_loss = history.get('loss', [])
            self.current_job.metrics.val_loss = history.get('val_loss', [])
            self.current_job.metrics.train_accuracy = history.get('accuracy', [])
            self.current_job.metrics.val_accuracy = history.get('val_accuracy', [])
        
        return model
    
    def evaluate_model(
        self,
        model: Any,
        X_test: np.ndarray,
        y_test: np.ndarray
    ) -> Dict[str, float]:
        """
        Evaluate model on test set.
        
        Returns:
            Dictionary of metrics
        """
        metrics = model.evaluate(X_test, y_test)
        
        # Store in job metrics
        if self.current_job:
            self.current_job.metrics.test_accuracy = metrics.get('accuracy')
            self.current_job.metrics.test_precision = metrics.get('precision')
            self.current_job.metrics.test_recall = metrics.get('recall')
            self.current_job.metrics.test_f1 = metrics.get('f1_score')
            self.current_job.metrics.test_roc_auc = metrics.get('roc_auc')
        
        return metrics
    
    def save_model(
        self,
        model: Any,
        job: TrainingJob,
        feature_names: List[str]
    ) -> str:
        """
        Save trained model to disk.
        
        Returns:
            Path to saved model
        """
        # Create output directory
        output_dir = Path(self.config.model_output_dir)
        model_dir = output_dir / f"{job.model_type}_{job.job_id}"
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # Save model
        model.feature_names = feature_names
        model.save(str(model_dir))
        
        # Save job metadata
        job_metadata = job.to_dict()
        with open(model_dir / "job_metadata.json", 'w') as f:
            json.dump(job_metadata, f, indent=2)
        
        logger.info(f"Model saved to {model_dir}")
        
        return str(model_dir)
    
    def run(
        self,
        model_class: Type,
        model_kwargs: Optional[Dict] = None
    ) -> TrainingJob:
        """
        Run the full training pipeline.
        
        Args:
            model_class: Model class to train
            model_kwargs: Arguments to pass to model constructor
            
        Returns:
            Completed TrainingJob
        """
        # Create job
        model_type = model_class.__name__
        job = self.create_job(model_type)
        self.current_job = job
        
        try:
            job.status = TrainingStatus.PREPARING
            job.started_at = datetime.utcnow()
            
            # Load data
            X, y, feature_names = self.load_data()
            
            # Feature selection
            X_selected, selected_features = self.select_features(X, y, feature_names)
            
            # Split data
            X_train, X_val, X_test, y_train, y_val, y_test = self.split_data(X_selected, y)
            
            # Cross-validation (optional)
            if self.config.use_cv:
                job.status = TrainingStatus.VALIDATING
                cv_scores = self.cross_validate(model_class, X_selected, y, model_kwargs)
                job.metrics.cv_scores = cv_scores
                job.metrics.cv_mean = float(np.mean(cv_scores))
                job.metrics.cv_std = float(np.std(cv_scores))
                logger.info(f"CV Score: {job.metrics.cv_mean:.4f} (+/- {job.metrics.cv_std:.4f})")
            
            # Train final model
            job.status = TrainingStatus.TRAINING
            model = self.train_model(model_class, X_train, y_train, X_val, y_val, model_kwargs)
            
            # Evaluate
            job.status = TrainingStatus.VALIDATING
            metrics = self.evaluate_model(model, X_test, y_test)
            logger.info(f"Test metrics: {metrics}")
            
            # Save model
            model_path = self.save_model(model, job, selected_features)
            job.model_path = model_path
            
            # Complete
            job.status = TrainingStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            
            if self.on_training_complete:
                self.on_training_complete(job)
            
            logger.info(f"Training job {job.job_id} completed successfully")
            
        except Exception as e:
            job.status = TrainingStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            logger.error(f"Training job {job.job_id} failed: {e}")
            raise
        
        finally:
            self.current_job = None
        
        return job
    
    def get_job_status(self, job_id: str) -> Optional[TrainingJob]:
        """Get status of a training job."""
        return self.jobs.get(job_id)
    
    def list_jobs(self) -> List[TrainingJob]:
        """List all training jobs."""
        return list(self.jobs.values())


class HyperparameterOptimizer:
    """
    Hyperparameter optimization using Optuna or random search.
    """
    
    def __init__(self, pipeline: TrainingPipeline):
        self.pipeline = pipeline
    
    def get_search_space(self, model_type: str) -> Dict[str, Any]:
        """Define hyperparameter search space."""
        if model_type == "LSTMPricePredictor":
            return {
                'lstm_units_1': [64, 128, 256],
                'lstm_units_2': [32, 64, 128],
                'dropout_rate': [0.2, 0.3, 0.4, 0.5],
                'learning_rate': [0.0001, 0.001, 0.01],
                'batch_size': [16, 32, 64],
                'sequence_length': [30, 60, 90]
            }
        return {}
    
    def random_search(
        self,
        model_class: Type,
        n_trials: int = 10
    ) -> Dict[str, Any]:
        """
        Perform random search for hyperparameters.
        
        Returns:
            Best hyperparameters found
        """
        search_space = self.get_search_space(model_class.__name__)
        
        best_score = 0
        best_params = {}
        
        for trial in range(n_trials):
            # Sample random parameters
            params = {
                key: np.random.choice(values)
                for key, values in search_space.items()
            }
            
            logger.info(f"HPO Trial {trial + 1}/{n_trials}: {params}")
            
            # Create model config from params
            # This would need to be customized per model type
            
            # For now, use default and track score
            try:
                job = self.pipeline.run(model_class)
                score = job.metrics.cv_mean or job.metrics.test_roc_auc or 0
                
                if score > best_score:
                    best_score = score
                    best_params = params
                    logger.info(f"New best score: {best_score:.4f}")
                    
            except Exception as e:
                logger.warning(f"Trial {trial + 1} failed: {e}")
        
        logger.info(f"Best parameters: {best_params} (score: {best_score:.4f})")
        return best_params


# Convenience function
def train_price_predictor(
    symbols: Optional[List[str]] = None,
    use_cv: bool = True
) -> TrainingJob:
    """
    Train a price direction predictor.
    
    Args:
        symbols: List of stock symbols to train on
        use_cv: Whether to use cross-validation
        
    Returns:
        Completed TrainingJob
    """
    from .price_predictor import LSTMPricePredictor
    
    config = TrainingConfig(
        symbols=symbols or ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA'],
        use_cv=use_cv
    )
    
    pipeline = TrainingPipeline(config)
    return pipeline.run(LSTMPricePredictor)
