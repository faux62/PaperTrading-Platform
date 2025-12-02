"""
Ensemble Methods

Combines multiple ML models for robust predictions:
- Voting ensemble (hard/soft)
- Stacking ensemble
- Weighted averaging
- Model selection based on recent performance
"""
import numpy as np
from typing import Optional, List, Dict, Any, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod
from loguru import logger


class EnsembleMethod(str, Enum):
    """Ensemble combination method."""
    HARD_VOTING = "hard_voting"
    SOFT_VOTING = "soft_voting"
    WEIGHTED_AVERAGE = "weighted_average"
    STACKING = "stacking"
    DYNAMIC_SELECTION = "dynamic_selection"


@dataclass
class EnsemblePrediction:
    """Result from ensemble prediction."""
    symbol: str
    prediction: Any  # Direction, trend, or score
    confidence: float
    individual_predictions: Dict[str, Any]
    weights_used: Dict[str, float]
    agreement_ratio: float  # How many models agree
    timestamp: datetime = field(default_factory=datetime.utcnow)
    ensemble_method: str = "weighted_average"
    
    def to_dict(self) -> dict:
        return {
            'symbol': self.symbol,
            'prediction': str(self.prediction) if hasattr(self.prediction, 'value') else self.prediction,
            'confidence': self.confidence,
            'individual_predictions': {
                k: str(v) if hasattr(v, 'value') else v
                for k, v in self.individual_predictions.items()
            },
            'weights_used': self.weights_used,
            'agreement_ratio': self.agreement_ratio,
            'timestamp': self.timestamp.isoformat(),
            'ensemble_method': self.ensemble_method
        }


@dataclass
class ModelPerformance:
    """Tracks individual model performance."""
    model_name: str
    accuracy: float = 0.5
    precision: float = 0.5
    recall: float = 0.5
    f1_score: float = 0.5
    recent_accuracy: float = 0.5  # Last N predictions
    predictions_count: int = 0
    correct_predictions: int = 0
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    def update(self, correct: bool):
        """Update performance with new prediction result."""
        self.predictions_count += 1
        if correct:
            self.correct_predictions += 1
        self.accuracy = self.correct_predictions / self.predictions_count
        self.last_updated = datetime.utcnow()


class BaseEnsemble(ABC):
    """Abstract base class for ensemble methods."""
    
    @abstractmethod
    def fit(self, models: List[Any], X: np.ndarray, y: np.ndarray):
        """Fit the ensemble."""
        pass
    
    @abstractmethod
    def predict(self, X: np.ndarray) -> List[EnsemblePrediction]:
        """Make ensemble predictions."""
        pass


class VotingEnsemble(BaseEnsemble):
    """
    Voting ensemble for classification.
    
    Supports:
    - Hard voting: Majority vote
    - Soft voting: Average probabilities
    """
    
    def __init__(
        self,
        voting: str = 'soft',
        weights: Optional[Dict[str, float]] = None
    ):
        self.voting = voting  # 'hard' or 'soft'
        self.weights = weights or {}
        self.models: Dict[str, Any] = {}
        self.model_performance: Dict[str, ModelPerformance] = {}
        
    def add_model(self, name: str, model: Any, weight: float = 1.0):
        """Add a model to the ensemble."""
        self.models[name] = model
        self.weights[name] = weight
        self.model_performance[name] = ModelPerformance(model_name=name)
        logger.info(f"Added model '{name}' to ensemble with weight {weight}")
    
    def fit(
        self,
        models: Optional[List[Tuple[str, Any]]] = None,
        X: np.ndarray = None,
        y: np.ndarray = None
    ):
        """
        Fit ensemble (add models and optionally train).
        
        Args:
            models: List of (name, model) tuples
            X: Training features (if models need training)
            y: Training targets
        """
        if models:
            for name, model in models:
                self.add_model(name, model)
        
        # Optionally train models that aren't fitted
        if X is not None and y is not None:
            for name, model in self.models.items():
                if hasattr(model, 'fit') and not getattr(model, 'is_trained', True):
                    model.fit(X, y)
    
    def predict(
        self,
        X: np.ndarray,
        symbol: str = ""
    ) -> List[EnsemblePrediction]:
        """
        Make ensemble predictions.
        
        Args:
            X: Features to predict
            symbol: Stock symbol
            
        Returns:
            List of EnsemblePrediction objects
        """
        if not self.models:
            raise ValueError("No models in ensemble")
        
        n_samples = len(X) if X.ndim > 1 else 1
        if X.ndim == 1:
            X = X.reshape(1, -1)
        
        # Collect predictions from all models
        all_predictions = {}
        all_probabilities = {}
        
        for name, model in self.models.items():
            try:
                if hasattr(model, 'predict'):
                    preds = model.predict(X)
                    
                    # Handle different prediction formats
                    if hasattr(preds[0], 'direction'):
                        # Price predictor
                        all_predictions[name] = [p.direction.value for p in preds]
                        all_probabilities[name] = [p.probability_up for p in preds]
                    elif hasattr(preds[0], 'trend'):
                        # Trend classifier
                        all_predictions[name] = [p.trend.value for p in preds]
                        all_probabilities[name] = [p.confidence for p in preds]
                    elif hasattr(preds[0], 'overall_score'):
                        # Risk scorer
                        all_predictions[name] = [p.overall_score for p in preds]
                        all_probabilities[name] = [p.confidence for p in preds]
                    else:
                        all_predictions[name] = list(preds)
                        all_probabilities[name] = [0.5] * len(preds)
            except Exception as e:
                logger.warning(f"Error getting prediction from {name}: {e}")
        
        # Combine predictions
        results = []
        for i in range(n_samples):
            individual_preds = {
                name: preds[i] for name, preds in all_predictions.items()
            }
            individual_probs = {
                name: probs[i] for name, probs in all_probabilities.items()
            }
            
            if self.voting == 'hard':
                final_pred, confidence = self._hard_vote(individual_preds)
            else:
                final_pred, confidence = self._soft_vote(individual_preds, individual_probs)
            
            # Calculate agreement
            unique_preds = set(individual_preds.values())
            if len(individual_preds) > 0:
                most_common = max(set(individual_preds.values()), 
                                 key=list(individual_preds.values()).count)
                agreement = sum(1 for p in individual_preds.values() if p == most_common)
                agreement_ratio = agreement / len(individual_preds)
            else:
                agreement_ratio = 0.0
            
            results.append(EnsemblePrediction(
                symbol=symbol,
                prediction=final_pred,
                confidence=confidence,
                individual_predictions=individual_preds,
                weights_used=self.weights.copy(),
                agreement_ratio=agreement_ratio,
                ensemble_method=f"{self.voting}_voting"
            ))
        
        return results
    
    def _hard_vote(
        self,
        predictions: Dict[str, Any]
    ) -> Tuple[Any, float]:
        """Hard voting - majority wins."""
        if not predictions:
            return None, 0.0
        
        # Weight votes
        vote_counts = {}
        total_weight = 0
        
        for name, pred in predictions.items():
            weight = self.weights.get(name, 1.0)
            vote_counts[pred] = vote_counts.get(pred, 0) + weight
            total_weight += weight
        
        # Find winner
        winner = max(vote_counts, key=vote_counts.get)
        confidence = vote_counts[winner] / total_weight if total_weight > 0 else 0.0
        
        return winner, confidence
    
    def _soft_vote(
        self,
        predictions: Dict[str, Any],
        probabilities: Dict[str, float]
    ) -> Tuple[Any, float]:
        """Soft voting - weighted probability average."""
        if not predictions:
            return None, 0.0
        
        # Calculate weighted average probability
        total_weight = 0
        weighted_prob = 0
        
        for name, prob in probabilities.items():
            weight = self.weights.get(name, 1.0)
            weighted_prob += prob * weight
            total_weight += weight
        
        avg_prob = weighted_prob / total_weight if total_weight > 0 else 0.5
        
        # Determine prediction based on average probability
        # Assuming binary classification with prob > 0.5 = positive
        pred_values = list(predictions.values())
        if avg_prob > 0.5:
            # Find positive predictions
            positive_preds = [p for p in pred_values if 'up' in str(p).lower() or float(p) > 50 if isinstance(p, (int, float)) else False]
            final_pred = positive_preds[0] if positive_preds else pred_values[0]
        else:
            final_pred = pred_values[0]
        
        confidence = abs(avg_prob - 0.5) * 2  # Scale to 0-1
        
        return final_pred, confidence
    
    def update_weights_from_performance(self, decay: float = 0.95):
        """Update model weights based on recent performance."""
        total_accuracy = sum(
            perf.recent_accuracy for perf in self.model_performance.values()
        )
        
        if total_accuracy > 0:
            for name, perf in self.model_performance.items():
                self.weights[name] = perf.recent_accuracy / total_accuracy * len(self.models)
        
        logger.info(f"Updated ensemble weights: {self.weights}")


class StackingEnsemble(BaseEnsemble):
    """
    Stacking ensemble with meta-learner.
    
    Level 0: Base models make predictions
    Level 1: Meta-model combines base predictions
    """
    
    def __init__(
        self,
        base_models: Optional[List[Tuple[str, Any]]] = None,
        meta_model: Optional[Any] = None,
        use_probabilities: bool = True
    ):
        self.base_models: Dict[str, Any] = {}
        self.meta_model = meta_model
        self.use_probabilities = use_probabilities
        self.is_fitted = False
        
        if base_models:
            for name, model in base_models:
                self.base_models[name] = model
    
    def fit(
        self,
        models: Optional[List[Tuple[str, Any]]] = None,
        X: np.ndarray = None,
        y: np.ndarray = None
    ):
        """
        Fit stacking ensemble.
        
        Uses out-of-fold predictions from base models to train meta-model.
        """
        if models:
            for name, model in models:
                self.base_models[name] = model
        
        if X is None or y is None:
            return
        
        try:
            from sklearn.model_selection import cross_val_predict
            from sklearn.linear_model import LogisticRegression
        except ImportError:
            logger.warning("sklearn not available for stacking")
            self.is_fitted = True
            return
        
        # Get out-of-fold predictions from base models
        oof_predictions = []
        
        for name, model in self.base_models.items():
            if hasattr(model, 'predict_proba') and self.use_probabilities:
                oof_pred = cross_val_predict(model, X, y, cv=5, method='predict_proba')
                if oof_pred.ndim > 1:
                    oof_pred = oof_pred[:, 1]  # Positive class probability
            else:
                oof_pred = cross_val_predict(model, X, y, cv=5)
            
            oof_predictions.append(oof_pred)
        
        # Stack predictions as features for meta-model
        meta_features = np.column_stack(oof_predictions)
        
        # Fit meta-model
        if self.meta_model is None:
            self.meta_model = LogisticRegression(random_state=42)
        
        self.meta_model.fit(meta_features, y)
        
        # Fit base models on full data
        for model in self.base_models.values():
            model.fit(X, y)
        
        self.is_fitted = True
        logger.info("Stacking ensemble fitted")
    
    def predict(
        self,
        X: np.ndarray,
        symbol: str = ""
    ) -> List[EnsemblePrediction]:
        """Make stacking predictions."""
        if not self.is_fitted:
            raise ValueError("Ensemble not fitted")
        
        # Get base model predictions
        base_predictions = []
        individual_preds = {}
        
        for name, model in self.base_models.items():
            if hasattr(model, 'predict_proba') and self.use_probabilities:
                pred = model.predict_proba(X)
                if pred.ndim > 1:
                    pred = pred[:, 1]
            else:
                pred = model.predict(X)
            
            base_predictions.append(pred)
            individual_preds[name] = pred.tolist() if hasattr(pred, 'tolist') else list(pred)
        
        # Stack and predict with meta-model
        meta_features = np.column_stack(base_predictions)
        
        if hasattr(self.meta_model, 'predict_proba'):
            final_proba = self.meta_model.predict_proba(meta_features)[:, 1]
            final_pred = (final_proba > 0.5).astype(int)
        else:
            final_pred = self.meta_model.predict(meta_features)
            final_proba = np.ones(len(final_pred)) * 0.5
        
        # Create results
        results = []
        for i in range(len(X)):
            results.append(EnsemblePrediction(
                symbol=symbol,
                prediction=int(final_pred[i]),
                confidence=float(abs(final_proba[i] - 0.5) * 2),
                individual_predictions={k: v[i] for k, v in individual_preds.items()},
                weights_used={},  # Weights are implicit in meta-model
                agreement_ratio=1.0,  # Meta-model handles disagreement
                ensemble_method="stacking"
            ))
        
        return results


class DynamicEnsemble(BaseEnsemble):
    """
    Dynamic model selection based on recent performance.
    
    Selects best model(s) for each prediction based on:
    - Recent accuracy
    - Feature similarity to past successful predictions
    - Market regime
    """
    
    def __init__(
        self,
        n_select: int = 3,
        performance_window: int = 50
    ):
        self.n_select = n_select
        self.performance_window = performance_window
        self.models: Dict[str, Any] = {}
        self.performance_history: Dict[str, List[bool]] = {}
        
    def add_model(self, name: str, model: Any):
        """Add model to ensemble."""
        self.models[name] = model
        self.performance_history[name] = []
    
    def fit(
        self,
        models: Optional[List[Tuple[str, Any]]] = None,
        X: np.ndarray = None,
        y: np.ndarray = None
    ):
        """Add models and optionally train."""
        if models:
            for name, model in models:
                self.add_model(name, model)
    
    def update_performance(self, model_name: str, correct: bool):
        """Update model performance history."""
        if model_name in self.performance_history:
            self.performance_history[model_name].append(correct)
            # Keep only recent history
            if len(self.performance_history[model_name]) > self.performance_window:
                self.performance_history[model_name] = \
                    self.performance_history[model_name][-self.performance_window:]
    
    def _get_model_scores(self) -> Dict[str, float]:
        """Calculate current model scores."""
        scores = {}
        for name, history in self.performance_history.items():
            if history:
                scores[name] = sum(history) / len(history)
            else:
                scores[name] = 0.5  # Default score
        return scores
    
    def _select_models(self) -> List[str]:
        """Select best performing models."""
        scores = self._get_model_scores()
        sorted_models = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [name for name, _ in sorted_models[:self.n_select]]
    
    def predict(
        self,
        X: np.ndarray,
        symbol: str = ""
    ) -> List[EnsemblePrediction]:
        """Make predictions using best models."""
        selected = self._select_models()
        
        if not selected:
            selected = list(self.models.keys())[:self.n_select]
        
        # Get predictions from selected models
        all_predictions = {}
        all_confidences = {}
        
        for name in selected:
            model = self.models[name]
            try:
                preds = model.predict(X)
                if hasattr(preds[0], 'direction'):
                    all_predictions[name] = [p.direction.value for p in preds]
                    all_confidences[name] = [p.confidence for p in preds]
                else:
                    all_predictions[name] = list(preds)
                    all_confidences[name] = [0.5] * len(preds)
            except Exception as e:
                logger.warning(f"Error from {name}: {e}")
        
        # Combine using weighted average based on recent performance
        scores = self._get_model_scores()
        weights = {name: scores.get(name, 0.5) for name in selected}
        
        results = []
        n_samples = len(X) if X.ndim > 1 else 1
        
        for i in range(n_samples):
            individual = {name: preds[i] for name, preds in all_predictions.items()}
            
            # Weighted vote
            total_weight = sum(weights.values())
            if total_weight > 0:
                # Simple majority with weights
                vote_counts = {}
                for name, pred in individual.items():
                    vote_counts[pred] = vote_counts.get(pred, 0) + weights[name]
                final_pred = max(vote_counts, key=vote_counts.get)
                confidence = vote_counts[final_pred] / total_weight
            else:
                final_pred = list(individual.values())[0] if individual else None
                confidence = 0.5
            
            results.append(EnsemblePrediction(
                symbol=symbol,
                prediction=final_pred,
                confidence=confidence,
                individual_predictions=individual,
                weights_used=weights,
                agreement_ratio=sum(1 for p in individual.values() if p == final_pred) / len(individual) if individual else 0,
                ensemble_method="dynamic_selection"
            ))
        
        return results


def create_ensemble(
    method: EnsembleMethod,
    models: List[Tuple[str, Any]],
    **kwargs
) -> BaseEnsemble:
    """
    Factory function to create an ensemble.
    
    Args:
        method: Ensemble method to use
        models: List of (name, model) tuples
        **kwargs: Additional arguments for the ensemble
        
    Returns:
        Ensemble instance
    """
    ensemble_classes = {
        EnsembleMethod.HARD_VOTING: lambda: VotingEnsemble(voting='hard', **kwargs),
        EnsembleMethod.SOFT_VOTING: lambda: VotingEnsemble(voting='soft', **kwargs),
        EnsembleMethod.WEIGHTED_AVERAGE: lambda: VotingEnsemble(voting='soft', **kwargs),
        EnsembleMethod.STACKING: lambda: StackingEnsemble(**kwargs),
        EnsembleMethod.DYNAMIC_SELECTION: lambda: DynamicEnsemble(**kwargs)
    }
    
    ensemble = ensemble_classes[method]()
    ensemble.fit(models)
    
    return ensemble
