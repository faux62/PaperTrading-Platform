"""
Model Evaluation

Comprehensive evaluation metrics for ML models:
- Classification metrics
- Regression metrics
- Trading-specific metrics
- Model comparison
"""
import numpy as np
from typing import Optional, List, Dict, Any, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from loguru import logger


class MetricType(str, Enum):
    """Type of metric."""
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    TRADING = "trading"


@dataclass
class ClassificationMetrics:
    """Classification performance metrics."""
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    specificity: float = 0.0
    balanced_accuracy: float = 0.0
    cohen_kappa: float = 0.0
    matthews_corrcoef: float = 0.0
    auc_roc: float = 0.0
    auc_pr: float = 0.0
    log_loss: float = 0.0
    
    # Per-class metrics
    class_precision: Dict[str, float] = field(default_factory=dict)
    class_recall: Dict[str, float] = field(default_factory=dict)
    class_f1: Dict[str, float] = field(default_factory=dict)
    
    # Confusion matrix
    confusion_matrix: Optional[np.ndarray] = None
    
    def to_dict(self) -> dict:
        result = {
            'accuracy': self.accuracy,
            'precision': self.precision,
            'recall': self.recall,
            'f1_score': self.f1_score,
            'specificity': self.specificity,
            'balanced_accuracy': self.balanced_accuracy,
            'cohen_kappa': self.cohen_kappa,
            'matthews_corrcoef': self.matthews_corrcoef,
            'auc_roc': self.auc_roc,
            'auc_pr': self.auc_pr,
            'log_loss': self.log_loss,
            'class_precision': self.class_precision,
            'class_recall': self.class_recall,
            'class_f1': self.class_f1
        }
        if self.confusion_matrix is not None:
            result['confusion_matrix'] = self.confusion_matrix.tolist()
        return result


@dataclass
class RegressionMetrics:
    """Regression performance metrics."""
    mse: float = 0.0
    rmse: float = 0.0
    mae: float = 0.0
    mape: float = 0.0
    smape: float = 0.0
    r2_score: float = 0.0
    adjusted_r2: float = 0.0
    explained_variance: float = 0.0
    max_error: float = 0.0
    median_ae: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            'mse': self.mse,
            'rmse': self.rmse,
            'mae': self.mae,
            'mape': self.mape,
            'smape': self.smape,
            'r2_score': self.r2_score,
            'adjusted_r2': self.adjusted_r2,
            'explained_variance': self.explained_variance,
            'max_error': self.max_error,
            'median_ae': self.median_ae
        }


@dataclass
class TradingMetrics:
    """Trading-specific performance metrics."""
    # Returns
    total_return: float = 0.0
    annualized_return: float = 0.0
    excess_return: float = 0.0
    
    # Risk
    volatility: float = 0.0
    downside_volatility: float = 0.0
    var_95: float = 0.0  # Value at Risk
    cvar_95: float = 0.0  # Conditional VaR
    max_drawdown: float = 0.0
    
    # Risk-adjusted
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    information_ratio: float = 0.0
    omega_ratio: float = 0.0
    
    # Direction accuracy
    direction_accuracy: float = 0.0
    up_accuracy: float = 0.0
    down_accuracy: float = 0.0
    
    # Timing
    hit_rate: float = 0.0
    profit_factor: float = 0.0
    payoff_ratio: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            'total_return': self.total_return,
            'annualized_return': self.annualized_return,
            'excess_return': self.excess_return,
            'volatility': self.volatility,
            'downside_volatility': self.downside_volatility,
            'var_95': self.var_95,
            'cvar_95': self.cvar_95,
            'max_drawdown': self.max_drawdown,
            'sharpe_ratio': self.sharpe_ratio,
            'sortino_ratio': self.sortino_ratio,
            'calmar_ratio': self.calmar_ratio,
            'information_ratio': self.information_ratio,
            'omega_ratio': self.omega_ratio,
            'direction_accuracy': self.direction_accuracy,
            'up_accuracy': self.up_accuracy,
            'down_accuracy': self.down_accuracy,
            'hit_rate': self.hit_rate,
            'profit_factor': self.profit_factor,
            'payoff_ratio': self.payoff_ratio
        }


@dataclass
class EvaluationResult:
    """Complete model evaluation result."""
    model_name: str
    model_version: str = ""
    evaluated_at: datetime = field(default_factory=datetime.utcnow)
    
    classification: Optional[ClassificationMetrics] = None
    regression: Optional[RegressionMetrics] = None
    trading: Optional[TradingMetrics] = None
    
    # Dataset info
    n_samples: int = 0
    n_features: int = 0
    dataset_name: str = ""
    
    # Custom metrics
    custom_metrics: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            'model_name': self.model_name,
            'model_version': self.model_version,
            'evaluated_at': self.evaluated_at.isoformat(),
            'classification': self.classification.to_dict() if self.classification else None,
            'regression': self.regression.to_dict() if self.regression else None,
            'trading': self.trading.to_dict() if self.trading else None,
            'n_samples': self.n_samples,
            'n_features': self.n_features,
            'dataset_name': self.dataset_name,
            'custom_metrics': self.custom_metrics
        }


class ModelEvaluator:
    """
    Comprehensive model evaluation.
    
    Computes classification, regression, and trading metrics.
    """
    
    def __init__(
        self,
        risk_free_rate: float = 0.02,
        trading_days_per_year: int = 252
    ):
        self.risk_free_rate = risk_free_rate
        self.trading_days = trading_days_per_year
    
    def evaluate_classification(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_proba: Optional[np.ndarray] = None,
        labels: Optional[List[Any]] = None
    ) -> ClassificationMetrics:
        """
        Evaluate classification model.
        
        Args:
            y_true: True labels
            y_pred: Predicted labels
            y_proba: Prediction probabilities
            labels: Class labels
            
        Returns:
            ClassificationMetrics
        """
        metrics = ClassificationMetrics()
        
        y_true = np.asarray(y_true)
        y_pred = np.asarray(y_pred)
        
        # Basic accuracy
        metrics.accuracy = np.mean(y_true == y_pred)
        
        # For binary classification
        unique_classes = np.unique(y_true)
        is_binary = len(unique_classes) == 2
        
        if is_binary:
            pos_label = unique_classes[1]
            
            tp = np.sum((y_true == pos_label) & (y_pred == pos_label))
            tn = np.sum((y_true != pos_label) & (y_pred != pos_label))
            fp = np.sum((y_true != pos_label) & (y_pred == pos_label))
            fn = np.sum((y_true == pos_label) & (y_pred != pos_label))
            
            # Precision, Recall, F1
            metrics.precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            metrics.recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            metrics.specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
            
            if metrics.precision + metrics.recall > 0:
                metrics.f1_score = 2 * metrics.precision * metrics.recall / (metrics.precision + metrics.recall)
            
            # Balanced accuracy
            metrics.balanced_accuracy = (metrics.recall + metrics.specificity) / 2
            
            # Matthews Correlation Coefficient
            denom = np.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
            metrics.matthews_corrcoef = (tp * tn - fp * fn) / denom if denom > 0 else 0
            
            # Confusion matrix
            metrics.confusion_matrix = np.array([[tn, fp], [fn, tp]])
            
            # AUC-ROC if probabilities available
            if y_proba is not None:
                if y_proba.ndim > 1:
                    proba = y_proba[:, 1]
                else:
                    proba = y_proba
                metrics.auc_roc = self._calculate_auc_roc(y_true, proba, pos_label)
        else:
            # Multiclass
            for cls in unique_classes:
                cls_mask_true = y_true == cls
                cls_mask_pred = y_pred == cls
                
                tp = np.sum(cls_mask_true & cls_mask_pred)
                fp = np.sum(~cls_mask_true & cls_mask_pred)
                fn = np.sum(cls_mask_true & ~cls_mask_pred)
                
                prec = tp / (tp + fp) if (tp + fp) > 0 else 0
                rec = tp / (tp + fn) if (tp + fn) > 0 else 0
                f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
                
                cls_str = str(cls)
                metrics.class_precision[cls_str] = prec
                metrics.class_recall[cls_str] = rec
                metrics.class_f1[cls_str] = f1
            
            # Macro averages
            if metrics.class_precision:
                metrics.precision = np.mean(list(metrics.class_precision.values()))
                metrics.recall = np.mean(list(metrics.class_recall.values()))
                metrics.f1_score = np.mean(list(metrics.class_f1.values()))
        
        # Cohen's Kappa
        metrics.cohen_kappa = self._calculate_cohens_kappa(y_true, y_pred)
        
        # Log loss if probabilities available
        if y_proba is not None:
            metrics.log_loss = self._calculate_log_loss(y_true, y_proba)
        
        return metrics
    
    def evaluate_regression(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        n_features: int = 1
    ) -> RegressionMetrics:
        """
        Evaluate regression model.
        
        Args:
            y_true: True values
            y_pred: Predicted values
            n_features: Number of features (for adjusted R²)
            
        Returns:
            RegressionMetrics
        """
        metrics = RegressionMetrics()
        
        y_true = np.asarray(y_true)
        y_pred = np.asarray(y_pred)
        
        errors = y_true - y_pred
        
        # MSE, RMSE
        metrics.mse = np.mean(errors ** 2)
        metrics.rmse = np.sqrt(metrics.mse)
        
        # MAE
        metrics.mae = np.mean(np.abs(errors))
        
        # Median Absolute Error
        metrics.median_ae = np.median(np.abs(errors))
        
        # Max Error
        metrics.max_error = np.max(np.abs(errors))
        
        # MAPE
        non_zero_mask = y_true != 0
        if np.any(non_zero_mask):
            metrics.mape = np.mean(np.abs(errors[non_zero_mask] / y_true[non_zero_mask])) * 100
        
        # SMAPE
        denominator = np.abs(y_true) + np.abs(y_pred)
        non_zero_denom = denominator != 0
        if np.any(non_zero_denom):
            metrics.smape = np.mean(2 * np.abs(errors[non_zero_denom]) / denominator[non_zero_denom]) * 100
        
        # R² Score
        ss_res = np.sum(errors ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        metrics.r2_score = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        # Adjusted R²
        n = len(y_true)
        if n > n_features + 1:
            metrics.adjusted_r2 = 1 - (1 - metrics.r2_score) * (n - 1) / (n - n_features - 1)
        
        # Explained Variance
        metrics.explained_variance = 1 - np.var(errors) / np.var(y_true) if np.var(y_true) > 0 else 0
        
        return metrics
    
    def evaluate_trading(
        self,
        returns: np.ndarray,
        predictions: np.ndarray,
        actual_directions: np.ndarray,
        benchmark_returns: Optional[np.ndarray] = None
    ) -> TradingMetrics:
        """
        Evaluate trading model.
        
        Args:
            returns: Strategy returns
            predictions: Predicted directions (1=up, -1=down, 0=flat)
            actual_directions: Actual price directions
            benchmark_returns: Optional benchmark returns
            
        Returns:
            TradingMetrics
        """
        metrics = TradingMetrics()
        
        returns = np.asarray(returns)
        predictions = np.asarray(predictions)
        actual_directions = np.asarray(actual_directions)
        
        # Total and annualized return
        cumulative = np.prod(1 + returns) - 1
        metrics.total_return = cumulative
        
        n_periods = len(returns)
        if n_periods > 0:
            metrics.annualized_return = (1 + cumulative) ** (self.trading_days / n_periods) - 1
        
        # Excess return
        if benchmark_returns is not None:
            benchmark_cumulative = np.prod(1 + benchmark_returns) - 1
            metrics.excess_return = cumulative - benchmark_cumulative
        
        # Volatility
        metrics.volatility = np.std(returns) * np.sqrt(self.trading_days) if len(returns) > 1 else 0
        
        # Downside volatility
        negative_returns = returns[returns < 0]
        if len(negative_returns) > 0:
            metrics.downside_volatility = np.std(negative_returns) * np.sqrt(self.trading_days)
        
        # VaR and CVaR (95%)
        if len(returns) > 0:
            metrics.var_95 = np.percentile(returns, 5)
            metrics.cvar_95 = np.mean(returns[returns <= metrics.var_95]) if np.any(returns <= metrics.var_95) else 0
        
        # Max Drawdown
        cumulative_returns = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = (cumulative_returns - running_max) / running_max
        metrics.max_drawdown = np.min(drawdowns) if len(drawdowns) > 0 else 0
        
        # Sharpe Ratio
        if metrics.volatility > 0:
            excess = metrics.annualized_return - self.risk_free_rate
            metrics.sharpe_ratio = excess / metrics.volatility
        
        # Sortino Ratio
        if metrics.downside_volatility > 0:
            excess = metrics.annualized_return - self.risk_free_rate
            metrics.sortino_ratio = excess / metrics.downside_volatility
        
        # Calmar Ratio
        if metrics.max_drawdown < 0:
            metrics.calmar_ratio = metrics.annualized_return / abs(metrics.max_drawdown)
        
        # Information Ratio
        if benchmark_returns is not None and len(benchmark_returns) > 0:
            tracking_error = np.std(returns - benchmark_returns) * np.sqrt(self.trading_days)
            if tracking_error > 0:
                metrics.information_ratio = metrics.excess_return / tracking_error
        
        # Omega Ratio
        threshold = self.risk_free_rate / self.trading_days  # Daily threshold
        gains = np.sum(np.maximum(returns - threshold, 0))
        losses = np.sum(np.maximum(threshold - returns, 0))
        metrics.omega_ratio = gains / losses if losses > 0 else float('inf')
        
        # Direction accuracy
        direction_mask = predictions != 0
        if np.any(direction_mask):
            metrics.direction_accuracy = np.mean(
                np.sign(predictions[direction_mask]) == np.sign(actual_directions[direction_mask])
            )
        
        # Up/Down accuracy
        up_mask = actual_directions > 0
        down_mask = actual_directions < 0
        
        if np.any(up_mask):
            metrics.up_accuracy = np.mean(predictions[up_mask] > 0)
        if np.any(down_mask):
            metrics.down_accuracy = np.mean(predictions[down_mask] < 0)
        
        # Hit rate
        winning_trades = returns > 0
        metrics.hit_rate = np.mean(winning_trades) if len(returns) > 0 else 0
        
        # Profit factor
        gains = np.sum(returns[returns > 0]) if np.any(returns > 0) else 0
        losses = np.abs(np.sum(returns[returns < 0])) if np.any(returns < 0) else 1
        metrics.profit_factor = gains / losses if losses > 0 else float('inf')
        
        # Payoff ratio (avg win / avg loss)
        avg_win = np.mean(returns[returns > 0]) if np.any(returns > 0) else 0
        avg_loss = np.abs(np.mean(returns[returns < 0])) if np.any(returns < 0) else 1
        metrics.payoff_ratio = avg_win / avg_loss if avg_loss > 0 else float('inf')
        
        return metrics
    
    def evaluate(
        self,
        model_name: str,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        metric_type: MetricType = MetricType.CLASSIFICATION,
        y_proba: Optional[np.ndarray] = None,
        returns: Optional[np.ndarray] = None,
        **kwargs
    ) -> EvaluationResult:
        """
        Full model evaluation.
        
        Args:
            model_name: Name of the model
            y_true: True values
            y_pred: Predicted values
            metric_type: Type of metrics to compute
            y_proba: Prediction probabilities
            returns: Trading returns
            **kwargs: Additional parameters
            
        Returns:
            EvaluationResult
        """
        result = EvaluationResult(
            model_name=model_name,
            n_samples=len(y_true),
            n_features=kwargs.get('n_features', 0),
            dataset_name=kwargs.get('dataset_name', '')
        )
        
        if metric_type == MetricType.CLASSIFICATION:
            result.classification = self.evaluate_classification(
                y_true, y_pred, y_proba,
                labels=kwargs.get('labels')
            )
        elif metric_type == MetricType.REGRESSION:
            result.regression = self.evaluate_regression(
                y_true, y_pred,
                n_features=kwargs.get('n_features', 1)
            )
        
        # Trading metrics if returns provided
        if returns is not None:
            actual_directions = np.sign(y_true) if metric_type != MetricType.REGRESSION else y_true
            result.trading = self.evaluate_trading(
                returns,
                y_pred,
                actual_directions,
                benchmark_returns=kwargs.get('benchmark_returns')
            )
        
        return result
    
    def _calculate_auc_roc(
        self,
        y_true: np.ndarray,
        y_score: np.ndarray,
        pos_label: Any
    ) -> float:
        """Calculate AUC-ROC score."""
        # Convert to binary
        y_binary = (y_true == pos_label).astype(int)
        
        # Sort by score
        sorted_indices = np.argsort(y_score)[::-1]
        y_sorted = y_binary[sorted_indices]
        
        # Calculate TPR and FPR at each threshold
        n_pos = np.sum(y_binary)
        n_neg = len(y_binary) - n_pos
        
        if n_pos == 0 or n_neg == 0:
            return 0.5
        
        tpr = np.cumsum(y_sorted) / n_pos
        fpr = np.cumsum(1 - y_sorted) / n_neg
        
        # Calculate AUC using trapezoidal rule
        auc = np.trapz(tpr, fpr)
        
        return float(auc)
    
    def _calculate_cohens_kappa(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray
    ) -> float:
        """Calculate Cohen's Kappa coefficient."""
        observed_agreement = np.mean(y_true == y_pred)
        
        unique = np.unique(np.concatenate([y_true, y_pred]))
        expected_agreement = 0
        
        for cls in unique:
            expected_agreement += (np.mean(y_true == cls) * np.mean(y_pred == cls))
        
        if expected_agreement == 1:
            return 1.0
        
        kappa = (observed_agreement - expected_agreement) / (1 - expected_agreement)
        return float(kappa)
    
    def _calculate_log_loss(
        self,
        y_true: np.ndarray,
        y_proba: np.ndarray
    ) -> float:
        """Calculate log loss."""
        eps = 1e-15
        
        if y_proba.ndim == 1:
            # Binary
            y_proba = np.clip(y_proba, eps, 1 - eps)
            unique = np.unique(y_true)
            y_binary = (y_true == unique[-1]).astype(int)
            loss = -np.mean(y_binary * np.log(y_proba) + (1 - y_binary) * np.log(1 - y_proba))
        else:
            # Multiclass
            y_proba = np.clip(y_proba, eps, 1 - eps)
            y_proba = y_proba / y_proba.sum(axis=1, keepdims=True)
            n_samples = len(y_true)
            loss = -np.sum(np.log(y_proba[np.arange(n_samples), y_true.astype(int)])) / n_samples
        
        return float(loss)


def compare_models(
    evaluations: List[EvaluationResult],
    primary_metric: str = "f1_score"
) -> Dict[str, Any]:
    """
    Compare multiple model evaluations.
    
    Args:
        evaluations: List of evaluation results
        primary_metric: Main metric for ranking
        
    Returns:
        Comparison summary
    """
    comparison = {
        'models': [],
        'ranking': [],
        'best_model': None,
        'metrics_summary': {}
    }
    
    metric_values = {}
    
    for eval_result in evaluations:
        model_summary = {
            'name': eval_result.model_name,
            'version': eval_result.model_version,
            'metrics': {}
        }
        
        # Collect metrics
        if eval_result.classification:
            model_summary['metrics'].update(eval_result.classification.to_dict())
        if eval_result.regression:
            model_summary['metrics'].update(eval_result.regression.to_dict())
        if eval_result.trading:
            model_summary['metrics'].update(eval_result.trading.to_dict())
        
        comparison['models'].append(model_summary)
        
        # Track metric values
        for metric_name, value in model_summary['metrics'].items():
            if isinstance(value, (int, float)) and not np.isnan(value) and not np.isinf(value):
                if metric_name not in metric_values:
                    metric_values[metric_name] = []
                metric_values[metric_name].append((eval_result.model_name, value))
    
    # Compute summary statistics
    for metric_name, values in metric_values.items():
        vals = [v[1] for v in values]
        comparison['metrics_summary'][metric_name] = {
            'mean': np.mean(vals),
            'std': np.std(vals),
            'min': np.min(vals),
            'max': np.max(vals),
            'best_model': max(values, key=lambda x: x[1])[0]
        }
    
    # Rank by primary metric
    if primary_metric in metric_values:
        ranking = sorted(metric_values[primary_metric], key=lambda x: x[1], reverse=True)
        comparison['ranking'] = [r[0] for r in ranking]
        comparison['best_model'] = ranking[0][0] if ranking else None
    
    return comparison
