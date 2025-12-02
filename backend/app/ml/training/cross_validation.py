"""
Cross-Validation Framework

Specialized cross-validation strategies for financial time series:
- Time Series Split (no look-ahead bias)
- Walk Forward Validation
- Purged K-Fold (gap between train/test)
- Combinatorial Purged Cross-Validation
"""
import numpy as np
from typing import Iterator, Tuple, Optional, List, Dict, Any, Generator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from loguru import logger


@dataclass
class CVSplit:
    """Represents a single cross-validation split."""
    fold: int
    train_indices: np.ndarray
    test_indices: np.ndarray
    train_start: Optional[datetime] = None
    train_end: Optional[datetime] = None
    test_start: Optional[datetime] = None
    test_end: Optional[datetime] = None
    
    @property
    def train_size(self) -> int:
        return len(self.train_indices)
    
    @property
    def test_size(self) -> int:
        return len(self.test_indices)


@dataclass
class CVResult:
    """Results from cross-validation."""
    n_splits: int
    scores: List[float]
    mean_score: float
    std_score: float
    metric_name: str = "accuracy"
    fold_details: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            'n_splits': self.n_splits,
            'scores': self.scores,
            'mean_score': self.mean_score,
            'std_score': self.std_score,
            'metric_name': self.metric_name,
            'fold_details': self.fold_details
        }


class BaseCrossValidator(ABC):
    """Abstract base class for cross-validators."""
    
    @abstractmethod
    def split(self, X: np.ndarray, y: Optional[np.ndarray] = None) -> Iterator[CVSplit]:
        """Generate train/test splits."""
        pass
    
    @abstractmethod
    def get_n_splits(self) -> int:
        """Return the number of splits."""
        pass


class TimeSeriesSplit(BaseCrossValidator):
    """
    Time Series Cross-Validator with expanding or sliding window.
    
    Ensures no look-ahead bias by only using past data for training.
    """
    
    def __init__(
        self,
        n_splits: int = 5,
        test_size: Optional[int] = None,
        gap: int = 0,
        max_train_size: Optional[int] = None,
        expanding: bool = True
    ):
        """
        Args:
            n_splits: Number of CV folds
            test_size: Fixed test set size (if None, calculated automatically)
            gap: Number of samples to skip between train and test
            max_train_size: Maximum training set size (for sliding window)
            expanding: If True, training set expands; if False, slides
        """
        self.n_splits = n_splits
        self.test_size = test_size
        self.gap = gap
        self.max_train_size = max_train_size
        self.expanding = expanding
    
    def split(
        self,
        X: np.ndarray,
        y: Optional[np.ndarray] = None,
        dates: Optional[np.ndarray] = None
    ) -> Iterator[CVSplit]:
        """
        Generate time series splits.
        
        Args:
            X: Feature matrix
            y: Target array (unused but kept for sklearn compatibility)
            dates: Optional date array for each sample
            
        Yields:
            CVSplit objects
        """
        n_samples = len(X)
        
        # Calculate test size if not specified
        if self.test_size is None:
            test_size = n_samples // (self.n_splits + 1)
        else:
            test_size = self.test_size
        
        # Minimum training size
        min_train_size = test_size
        
        for fold in range(self.n_splits):
            # Calculate indices
            test_end = n_samples - (self.n_splits - 1 - fold) * test_size
            test_start = test_end - test_size
            
            train_end = test_start - self.gap
            
            if self.expanding:
                train_start = 0
            else:
                train_start = max(0, train_end - (self.max_train_size or train_end))
            
            # Skip if not enough data
            if train_end - train_start < min_train_size:
                continue
            
            train_indices = np.arange(train_start, train_end)
            test_indices = np.arange(test_start, test_end)
            
            # Get dates if available
            train_start_date = dates[train_start] if dates is not None else None
            train_end_date = dates[train_end - 1] if dates is not None else None
            test_start_date = dates[test_start] if dates is not None else None
            test_end_date = dates[test_end - 1] if dates is not None else None
            
            yield CVSplit(
                fold=fold,
                train_indices=train_indices,
                test_indices=test_indices,
                train_start=train_start_date,
                train_end=train_end_date,
                test_start=test_start_date,
                test_end=test_end_date
            )
    
    def get_n_splits(self) -> int:
        return self.n_splits


class WalkForwardCV(BaseCrossValidator):
    """
    Walk-Forward Cross-Validation.
    
    Simulates real trading by training on past data and testing on
    subsequent period, then moving forward in time.
    """
    
    def __init__(
        self,
        n_splits: int = 10,
        train_period: int = 252,  # ~1 year trading days
        test_period: int = 63,    # ~3 months
        step_size: Optional[int] = None,  # How much to advance each fold
        min_train_samples: int = 100
    ):
        """
        Args:
            n_splits: Number of walk-forward periods
            train_period: Number of samples in training window
            test_period: Number of samples in test window
            step_size: How many samples to advance (default: test_period)
            min_train_samples: Minimum training samples required
        """
        self.n_splits = n_splits
        self.train_period = train_period
        self.test_period = test_period
        self.step_size = step_size or test_period
        self.min_train_samples = min_train_samples
    
    def split(
        self,
        X: np.ndarray,
        y: Optional[np.ndarray] = None,
        dates: Optional[np.ndarray] = None
    ) -> Iterator[CVSplit]:
        """Generate walk-forward splits."""
        n_samples = len(X)
        
        for fold in range(self.n_splits):
            # Calculate window positions
            train_start = fold * self.step_size
            train_end = train_start + self.train_period
            
            test_start = train_end
            test_end = min(test_start + self.test_period, n_samples)
            
            # Check if we have enough data
            if train_end > n_samples or test_end > n_samples:
                break
            
            if train_end - train_start < self.min_train_samples:
                continue
            
            train_indices = np.arange(train_start, train_end)
            test_indices = np.arange(test_start, test_end)
            
            yield CVSplit(
                fold=fold,
                train_indices=train_indices,
                test_indices=test_indices,
                train_start=dates[train_start] if dates is not None else None,
                train_end=dates[train_end - 1] if dates is not None else None,
                test_start=dates[test_start] if dates is not None else None,
                test_end=dates[test_end - 1] if dates is not None else None
            )
    
    def get_n_splits(self) -> int:
        return self.n_splits


class PurgedKFold(BaseCrossValidator):
    """
    Purged K-Fold Cross-Validation.
    
    Standard K-Fold with a purge period (gap) between train and test
    to prevent information leakage in overlapping features.
    """
    
    def __init__(
        self,
        n_splits: int = 5,
        purge_gap: int = 5,
        embargo_pct: float = 0.01
    ):
        """
        Args:
            n_splits: Number of folds
            purge_gap: Number of samples to purge around test set
            embargo_pct: Percentage of test samples to embargo after test
        """
        self.n_splits = n_splits
        self.purge_gap = purge_gap
        self.embargo_pct = embargo_pct
    
    def split(
        self,
        X: np.ndarray,
        y: Optional[np.ndarray] = None,
        dates: Optional[np.ndarray] = None
    ) -> Iterator[CVSplit]:
        """Generate purged K-Fold splits."""
        n_samples = len(X)
        indices = np.arange(n_samples)
        
        # Calculate fold size
        fold_size = n_samples // self.n_splits
        embargo_size = int(fold_size * self.embargo_pct)
        
        for fold in range(self.n_splits):
            # Test indices for this fold
            test_start = fold * fold_size
            test_end = test_start + fold_size if fold < self.n_splits - 1 else n_samples
            
            test_indices = indices[test_start:test_end]
            
            # Training indices with purge
            train_mask = np.ones(n_samples, dtype=bool)
            
            # Exclude test set
            train_mask[test_start:test_end] = False
            
            # Purge before test
            purge_start = max(0, test_start - self.purge_gap)
            train_mask[purge_start:test_start] = False
            
            # Embargo after test
            embargo_end = min(n_samples, test_end + embargo_size)
            train_mask[test_end:embargo_end] = False
            
            train_indices = indices[train_mask]
            
            yield CVSplit(
                fold=fold,
                train_indices=train_indices,
                test_indices=test_indices,
                train_start=dates[train_indices[0]] if dates is not None and len(train_indices) > 0 else None,
                train_end=dates[train_indices[-1]] if dates is not None and len(train_indices) > 0 else None,
                test_start=dates[test_start] if dates is not None else None,
                test_end=dates[test_end - 1] if dates is not None else None
            )
    
    def get_n_splits(self) -> int:
        return self.n_splits


class CombinatorialPurgedCV(BaseCrossValidator):
    """
    Combinatorial Purged Cross-Validation (CPCV).
    
    Tests on all possible combinations of test folds for more
    robust performance estimation.
    """
    
    def __init__(
        self,
        n_splits: int = 5,
        n_test_splits: int = 2,
        purge_gap: int = 5
    ):
        """
        Args:
            n_splits: Total number of splits
            n_test_splits: Number of splits to use for testing in each iteration
            purge_gap: Gap between train and test
        """
        self.n_splits = n_splits
        self.n_test_splits = n_test_splits
        self.purge_gap = purge_gap
        
    def split(
        self,
        X: np.ndarray,
        y: Optional[np.ndarray] = None,
        dates: Optional[np.ndarray] = None
    ) -> Iterator[CVSplit]:
        """Generate combinatorial splits."""
        from itertools import combinations
        
        n_samples = len(X)
        indices = np.arange(n_samples)
        fold_size = n_samples // self.n_splits
        
        # Generate all combinations of test folds
        fold_indices = list(range(self.n_splits))
        test_combinations = list(combinations(fold_indices, self.n_test_splits))
        
        for combo_idx, test_folds in enumerate(test_combinations):
            # Build test mask
            test_mask = np.zeros(n_samples, dtype=bool)
            for fold in test_folds:
                start = fold * fold_size
                end = start + fold_size if fold < self.n_splits - 1 else n_samples
                test_mask[start:end] = True
            
            test_indices = indices[test_mask]
            
            # Build train mask with purge
            train_mask = ~test_mask.copy()
            
            # Purge around test boundaries
            for fold in test_folds:
                start = fold * fold_size
                end = start + fold_size if fold < self.n_splits - 1 else n_samples
                
                purge_start = max(0, start - self.purge_gap)
                purge_end = min(n_samples, end + self.purge_gap)
                
                train_mask[purge_start:start] = False
                train_mask[end:purge_end] = False
            
            train_indices = indices[train_mask]
            
            yield CVSplit(
                fold=combo_idx,
                train_indices=train_indices,
                test_indices=test_indices
            )
    
    def get_n_splits(self) -> int:
        from math import comb
        return comb(self.n_splits, self.n_test_splits)


class CrossValidator:
    """
    Main cross-validation executor.
    
    Handles the full CV workflow including training, evaluation,
    and result aggregation.
    """
    
    def __init__(
        self,
        cv_strategy: BaseCrossValidator,
        scoring: str = 'accuracy'
    ):
        """
        Args:
            cv_strategy: Cross-validation strategy to use
            scoring: Metric to optimize ('accuracy', 'f1', 'roc_auc', etc.)
        """
        self.cv_strategy = cv_strategy
        self.scoring = scoring
        self.results_: Optional[CVResult] = None
        
    def cross_validate(
        self,
        model_class: type,
        X: np.ndarray,
        y: np.ndarray,
        model_kwargs: Optional[Dict] = None,
        fit_kwargs: Optional[Dict] = None,
        dates: Optional[np.ndarray] = None,
        verbose: bool = True
    ) -> CVResult:
        """
        Perform cross-validation.
        
        Args:
            model_class: Model class to instantiate for each fold
            X: Feature matrix
            y: Target array
            model_kwargs: Arguments for model constructor
            fit_kwargs: Arguments for model.fit()
            dates: Optional date array
            verbose: Whether to log progress
            
        Returns:
            CVResult with all scores and statistics
        """
        model_kwargs = model_kwargs or {}
        fit_kwargs = fit_kwargs or {}
        
        scores = []
        fold_details = []
        
        for split in self.cv_strategy.split(X, y, dates):
            if verbose:
                logger.info(
                    f"Fold {split.fold + 1}/{self.cv_strategy.get_n_splits()}: "
                    f"train={split.train_size}, test={split.test_size}"
                )
            
            # Get data for this fold
            X_train = X[split.train_indices]
            y_train = y[split.train_indices]
            X_test = X[split.test_indices]
            y_test = y[split.test_indices]
            
            # Train model
            model = model_class(**model_kwargs)
            model.fit(X_train, y_train, **fit_kwargs)
            
            # Evaluate
            score = self._evaluate_fold(model, X_test, y_test)
            scores.append(score)
            
            # Store details
            fold_details.append({
                'fold': split.fold,
                'train_size': split.train_size,
                'test_size': split.test_size,
                'score': score,
                'train_start': split.train_start.isoformat() if split.train_start else None,
                'train_end': split.train_end.isoformat() if split.train_end else None,
                'test_start': split.test_start.isoformat() if split.test_start else None,
                'test_end': split.test_end.isoformat() if split.test_end else None
            })
            
            if verbose:
                logger.info(f"  Score: {score:.4f}")
        
        # Aggregate results
        self.results_ = CVResult(
            n_splits=len(scores),
            scores=scores,
            mean_score=float(np.mean(scores)),
            std_score=float(np.std(scores)),
            metric_name=self.scoring,
            fold_details=fold_details
        )
        
        if verbose:
            logger.info(
                f"CV Complete: {self.results_.mean_score:.4f} "
                f"(+/- {self.results_.std_score:.4f})"
            )
        
        return self.results_
    
    def _evaluate_fold(
        self,
        model: Any,
        X_test: np.ndarray,
        y_test: np.ndarray
    ) -> float:
        """Evaluate a single fold."""
        try:
            if hasattr(model, 'evaluate'):
                # Our custom models
                metrics = model.evaluate(X_test, y_test)
                return metrics.get(self.scoring, metrics.get('accuracy', 0.5))
            
            elif hasattr(model, 'score'):
                # sklearn models
                return model.score(X_test, y_test)
            
            elif hasattr(model, 'predict_proba'):
                # Calculate metric manually
                from sklearn.metrics import accuracy_score, roc_auc_score, f1_score
                
                y_pred = model.predict(X_test)
                
                if self.scoring == 'accuracy':
                    return accuracy_score(y_test, y_pred)
                elif self.scoring == 'roc_auc':
                    y_proba = model.predict_proba(X_test)
                    if y_proba.shape[1] == 2:
                        return roc_auc_score(y_test, y_proba[:, 1])
                    return roc_auc_score(y_test, y_proba, multi_class='ovr')
                elif self.scoring == 'f1':
                    return f1_score(y_test, y_pred, average='weighted')
                else:
                    return accuracy_score(y_test, y_pred)
            
            else:
                return 0.5
                
        except Exception as e:
            logger.warning(f"Error evaluating fold: {e}")
            return 0.5


def create_cv_strategy(
    strategy: str = 'time_series',
    n_splits: int = 5,
    **kwargs
) -> BaseCrossValidator:
    """
    Factory function to create cross-validation strategy.
    
    Args:
        strategy: One of 'time_series', 'walk_forward', 'purged_kfold', 'combinatorial'
        n_splits: Number of splits
        **kwargs: Additional arguments for the strategy
        
    Returns:
        Cross-validator instance
    """
    strategies = {
        'time_series': TimeSeriesSplit,
        'walk_forward': WalkForwardCV,
        'purged_kfold': PurgedKFold,
        'combinatorial': CombinatorialPurgedCV
    }
    
    if strategy not in strategies:
        raise ValueError(f"Unknown strategy: {strategy}. Choose from {list(strategies.keys())}")
    
    return strategies[strategy](n_splits=n_splits, **kwargs)
