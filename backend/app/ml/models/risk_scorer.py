"""
Risk Scorer using Gradient Boosting

Risk assessment model for stocks and portfolios:
- Individual stock risk scoring
- Risk factor decomposition
- Risk-adjusted return prediction
"""
import numpy as np
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import pickle
from pathlib import Path
from loguru import logger


class RiskLevel(str, Enum):
    """Risk level classification."""
    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


class RiskCategory(str, Enum):
    """Risk category for decomposition."""
    MARKET = "market"           # Systematic/market risk
    VOLATILITY = "volatility"   # Price volatility risk
    LIQUIDITY = "liquidity"     # Trading liquidity risk
    FUNDAMENTAL = "fundamental" # Fundamental/credit risk
    MOMENTUM = "momentum"       # Momentum/trend risk
    VALUATION = "valuation"     # Valuation risk


@dataclass
class RiskScore:
    """Comprehensive risk score for a stock."""
    symbol: str
    overall_score: float  # 0-100, higher = riskier
    risk_level: RiskLevel
    
    # Component scores (0-100)
    market_risk: float
    volatility_risk: float
    liquidity_risk: float
    fundamental_risk: float
    momentum_risk: float
    valuation_risk: float
    
    # Risk-adjusted metrics
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    var_95: Optional[float] = None  # 95% Value at Risk
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.utcnow)
    model_version: str = "1.0.0"
    confidence: float = 0.8
    
    # Feature contributions
    top_risk_factors: List[Tuple[str, float]] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            'symbol': self.symbol,
            'overall_score': self.overall_score,
            'risk_level': self.risk_level.value,
            'components': {
                'market_risk': self.market_risk,
                'volatility_risk': self.volatility_risk,
                'liquidity_risk': self.liquidity_risk,
                'fundamental_risk': self.fundamental_risk,
                'momentum_risk': self.momentum_risk,
                'valuation_risk': self.valuation_risk
            },
            'risk_adjusted_metrics': {
                'sharpe_ratio': self.sharpe_ratio,
                'sortino_ratio': self.sortino_ratio,
                'max_drawdown': self.max_drawdown,
                'var_95': self.var_95
            },
            'timestamp': self.timestamp.isoformat(),
            'model_version': self.model_version,
            'confidence': self.confidence,
            'top_risk_factors': self.top_risk_factors
        }


@dataclass
class RiskScorerConfig:
    """Configuration for risk scoring model."""
    # Model parameters
    n_estimators: int = 200
    max_depth: int = 8
    learning_rate: float = 0.1
    min_samples_split: int = 10
    min_samples_leaf: int = 5
    subsample: float = 0.8
    
    # Risk level thresholds
    very_low_threshold: float = 20
    low_threshold: float = 40
    moderate_threshold: float = 60
    high_threshold: float = 80
    
    # Feature weights for composite score
    market_weight: float = 0.20
    volatility_weight: float = 0.25
    liquidity_weight: float = 0.15
    fundamental_weight: float = 0.20
    momentum_weight: float = 0.10
    valuation_weight: float = 0.10
    
    random_state: int = 42
    
    def to_dict(self) -> dict:
        return {
            'n_estimators': self.n_estimators,
            'max_depth': self.max_depth,
            'learning_rate': self.learning_rate,
            'subsample': self.subsample,
            'thresholds': {
                'very_low': self.very_low_threshold,
                'low': self.low_threshold,
                'moderate': self.moderate_threshold,
                'high': self.high_threshold
            },
            'weights': {
                'market': self.market_weight,
                'volatility': self.volatility_weight,
                'liquidity': self.liquidity_weight,
                'fundamental': self.fundamental_weight,
                'momentum': self.momentum_weight,
                'valuation': self.valuation_weight
            }
        }


class GradientBoostingRiskScorer:
    """
    Gradient Boosting model for risk scoring.
    
    Uses XGBoost/LightGBM-style gradient boosting to predict
    risk scores based on multiple feature categories.
    """
    
    def __init__(self, config: Optional[RiskScorerConfig] = None):
        self.config = config or RiskScorerConfig()
        self.model = None
        self.component_models: Dict[str, Any] = {}
        self.scaler = None
        self.feature_names: List[str] = []
        self.feature_importances_: Dict[str, float] = {}
        self.is_trained = False
        self.model_version = "1.0.0"
        
    def build_model(self):
        """Build the Gradient Boosting model."""
        try:
            from sklearn.ensemble import GradientBoostingRegressor
            
            self.model = GradientBoostingRegressor(
                n_estimators=self.config.n_estimators,
                max_depth=self.config.max_depth,
                learning_rate=self.config.learning_rate,
                min_samples_split=self.config.min_samples_split,
                min_samples_leaf=self.config.min_samples_leaf,
                subsample=self.config.subsample,
                random_state=self.config.random_state
            )
            
            # Component models for each risk category
            for category in RiskCategory:
                self.component_models[category.value] = GradientBoostingRegressor(
                    n_estimators=self.config.n_estimators // 2,
                    max_depth=self.config.max_depth - 2,
                    learning_rate=self.config.learning_rate,
                    random_state=self.config.random_state
                )
            
        except ImportError:
            logger.warning("sklearn not available, using mock model")
            self._build_mock_model()
        
        return self.model
    
    def _build_mock_model(self):
        """Build mock model for testing."""
        class MockModel:
            def fit(self, X, y):
                self.feature_importances_ = np.ones(X.shape[1]) / X.shape[1]
                return self
            
            def predict(self, X):
                return np.random.uniform(20, 80, len(X))
        
        self.model = MockModel()
        for category in RiskCategory:
            self.component_models[category.value] = MockModel()
    
    def prepare_targets(
        self,
        returns: np.ndarray,
        volatility: np.ndarray,
        drawdowns: np.ndarray
    ) -> np.ndarray:
        """
        Calculate risk score targets from historical data.
        
        Risk score is based on:
        - Volatility (higher = riskier)
        - Drawdown magnitude (larger = riskier)
        - Return distribution (negative skew = riskier)
        """
        # Normalize components to 0-100
        vol_score = np.clip(volatility / 0.5 * 100, 0, 100)  # 50% vol = 100 score
        dd_score = np.clip(np.abs(drawdowns) / 0.5 * 100, 0, 100)  # 50% DD = 100 score
        
        # Calculate skewness penalty
        skew_penalty = np.zeros(len(returns))
        for i in range(20, len(returns)):
            window_returns = returns[i-20:i]
            skew = np.mean((window_returns - np.mean(window_returns))**3) / (np.std(window_returns)**3 + 1e-10)
            skew_penalty[i] = max(0, -skew * 10)  # Negative skew adds to risk
        
        # Combine into overall risk score
        risk_score = (0.4 * vol_score + 0.4 * dd_score + 0.2 * skew_penalty)
        risk_score = np.clip(risk_score, 0, 100)
        
        return risk_score
    
    def _categorize_features(
        self,
        feature_names: List[str]
    ) -> Dict[str, List[int]]:
        """Categorize features by risk category."""
        categories = {
            RiskCategory.MARKET.value: ['spy', 'beta', 'correlation', 'market'],
            RiskCategory.VOLATILITY.value: ['volatility', 'atr', 'bb_', 'std'],
            RiskCategory.LIQUIDITY.value: ['volume', 'spread', 'liquidity', 'turnover'],
            RiskCategory.FUNDAMENTAL.value: ['debt', 'current_ratio', 'interest_coverage', 'margin'],
            RiskCategory.MOMENTUM.value: ['rsi', 'macd', 'momentum', 'roc'],
            RiskCategory.VALUATION.value: ['pe_', 'pb_', 'ps_', 'ev_', 'peg']
        }
        
        feature_indices = {cat: [] for cat in categories}
        
        for i, name in enumerate(feature_names):
            name_lower = name.lower()
            for category, keywords in categories.items():
                if any(kw in name_lower for kw in keywords):
                    feature_indices[category].append(i)
                    break
        
        return feature_indices
    
    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        feature_names: Optional[List[str]] = None,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """
        Train the risk scoring model.
        
        Args:
            X_train: Training features
            y_train: Risk score targets (0-100)
            feature_names: Names of features
            X_val: Validation features
            y_val: Validation targets
            
        Returns:
            Training results
        """
        try:
            from sklearn.preprocessing import StandardScaler
        except ImportError:
            self.is_trained = True
            return {'mse': 100}
        
        logger.info(f"Training Risk Scorer with {len(X_train)} samples")
        
        # Scale features
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        
        # Store feature names
        self.feature_names = feature_names or [f'feature_{i}' for i in range(X_train.shape[1])]
        
        # Build models
        if self.model is None:
            self.build_model()
        
        # Train main model
        self.model.fit(X_train_scaled, y_train)
        
        # Store feature importances
        self.feature_importances_ = dict(zip(
            self.feature_names,
            self.model.feature_importances_
        ))
        
        # Train component models
        feature_indices = self._categorize_features(self.feature_names)
        
        for category, indices in feature_indices.items():
            if indices and category in self.component_models:
                X_category = X_train_scaled[:, indices]
                if X_category.shape[1] > 0:
                    self.component_models[category].fit(X_category, y_train)
        
        self.is_trained = True
        
        # Calculate metrics
        y_pred = self.model.predict(X_train_scaled)
        mse = float(np.mean((y_train - y_pred) ** 2))
        
        results = {
            'mse': mse,
            'rmse': np.sqrt(mse),
            'r2': float(1 - mse / np.var(y_train)),
            'n_features': X_train.shape[1]
        }
        
        if X_val is not None and y_val is not None:
            X_val_scaled = self.scaler.transform(X_val)
            y_val_pred = self.model.predict(X_val_scaled)
            val_mse = float(np.mean((y_val - y_val_pred) ** 2))
            results['val_mse'] = val_mse
            results['val_rmse'] = np.sqrt(val_mse)
        
        logger.info(f"Training complete. RMSE: {results['rmse']:.4f}")
        
        return results
    
    def predict(self, features: np.ndarray) -> List[RiskScore]:
        """
        Predict risk scores.
        
        Args:
            features: Feature matrix
            
        Returns:
            List of RiskScore objects
        """
        if not self.is_trained:
            raise ValueError("Model not trained yet")
        
        # Scale features
        if self.scaler is not None:
            features_scaled = self.scaler.transform(features)
        else:
            features_scaled = features
        
        # Predict overall score
        overall_scores = self.model.predict(features_scaled)
        overall_scores = np.clip(overall_scores, 0, 100)
        
        # Predict component scores
        feature_indices = self._categorize_features(self.feature_names)
        component_scores = {}
        
        for category, indices in feature_indices.items():
            if indices and category in self.component_models:
                X_category = features_scaled[:, indices]
                if X_category.shape[1] > 0:
                    try:
                        scores = self.component_models[category].predict(X_category)
                        component_scores[category] = np.clip(scores, 0, 100)
                    except:
                        component_scores[category] = overall_scores
                else:
                    component_scores[category] = overall_scores
            else:
                component_scores[category] = overall_scores
        
        # Get top risk factors
        sorted_features = sorted(
            self.feature_importances_.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        # Create results
        results = []
        for i in range(len(features)):
            score = float(overall_scores[i])
            
            # Determine risk level
            if score < self.config.very_low_threshold:
                risk_level = RiskLevel.VERY_LOW
            elif score < self.config.low_threshold:
                risk_level = RiskLevel.LOW
            elif score < self.config.moderate_threshold:
                risk_level = RiskLevel.MODERATE
            elif score < self.config.high_threshold:
                risk_level = RiskLevel.HIGH
            else:
                risk_level = RiskLevel.VERY_HIGH
            
            results.append(RiskScore(
                symbol="",  # Set by caller
                overall_score=score,
                risk_level=risk_level,
                market_risk=float(component_scores.get(RiskCategory.MARKET.value, [score])[i] if isinstance(component_scores.get(RiskCategory.MARKET.value), np.ndarray) else score),
                volatility_risk=float(component_scores.get(RiskCategory.VOLATILITY.value, [score])[i] if isinstance(component_scores.get(RiskCategory.VOLATILITY.value), np.ndarray) else score),
                liquidity_risk=float(component_scores.get(RiskCategory.LIQUIDITY.value, [score])[i] if isinstance(component_scores.get(RiskCategory.LIQUIDITY.value), np.ndarray) else score),
                fundamental_risk=float(component_scores.get(RiskCategory.FUNDAMENTAL.value, [score])[i] if isinstance(component_scores.get(RiskCategory.FUNDAMENTAL.value), np.ndarray) else score),
                momentum_risk=float(component_scores.get(RiskCategory.MOMENTUM.value, [score])[i] if isinstance(component_scores.get(RiskCategory.MOMENTUM.value), np.ndarray) else score),
                valuation_risk=float(component_scores.get(RiskCategory.VALUATION.value, [score])[i] if isinstance(component_scores.get(RiskCategory.VALUATION.value), np.ndarray) else score),
                model_version=self.model_version,
                top_risk_factors=sorted_features
            ))
        
        return results
    
    def predict_single(
        self,
        symbol: str,
        features: np.ndarray
    ) -> RiskScore:
        """Predict risk score for a single symbol."""
        if features.ndim == 1:
            features = features.reshape(1, -1)
        
        results = self.predict(features)
        if results:
            result = results[0]
            result.symbol = symbol
            return result
        raise ValueError("No prediction generated")
    
    def explain_risk(
        self,
        features: np.ndarray,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Explain risk score in terms of feature contributions.
        
        Returns breakdown of which features contribute most to risk.
        """
        if not self.is_trained:
            raise ValueError("Model not trained")
        
        # Get feature importances
        sorted_features = sorted(
            self.feature_importances_.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]
        
        # Categorize by risk type
        category_importance = {}
        feature_indices = self._categorize_features(self.feature_names)
        
        for category, indices in feature_indices.items():
            total_importance = sum(
                self.feature_importances_.get(self.feature_names[i], 0)
                for i in indices
            )
            category_importance[category] = total_importance
        
        return {
            'top_features': sorted_features,
            'category_breakdown': category_importance,
            'recommendations': self._generate_recommendations(category_importance)
        }
    
    def _generate_recommendations(
        self,
        category_importance: Dict[str, float]
    ) -> List[str]:
        """Generate risk mitigation recommendations."""
        recommendations = []
        
        # Sort categories by importance
        sorted_cats = sorted(category_importance.items(), key=lambda x: x[1], reverse=True)
        
        for category, importance in sorted_cats[:3]:
            if importance > 0.1:  # Significant contribution
                if category == RiskCategory.VOLATILITY.value:
                    recommendations.append("Consider hedging with options or reducing position size due to high volatility risk")
                elif category == RiskCategory.MARKET.value:
                    recommendations.append("High market correlation - consider diversifying across sectors")
                elif category == RiskCategory.LIQUIDITY.value:
                    recommendations.append("Low liquidity risk - use limit orders and avoid large trades")
                elif category == RiskCategory.FUNDAMENTAL.value:
                    recommendations.append("Fundamental risk elevated - review balance sheet and earnings")
                elif category == RiskCategory.MOMENTUM.value:
                    recommendations.append("Momentum indicators suggest trend exhaustion - watch for reversals")
                elif category == RiskCategory.VALUATION.value:
                    recommendations.append("Valuation risk high - stock may be overvalued relative to fundamentals")
        
        return recommendations
    
    def get_feature_importance(self, top_k: int = 20) -> List[Tuple[str, float]]:
        """Get top K most important features."""
        return sorted(
            self.feature_importances_.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]
    
    def save(self, path: str):
        """Save model to disk."""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        
        # Save main model
        if self.model is not None:
            with open(path / "model.pkl", 'wb') as f:
                pickle.dump(self.model, f)
        
        # Save component models
        for category, model in self.component_models.items():
            with open(path / f"model_{category}.pkl", 'wb') as f:
                pickle.dump(model, f)
        
        # Save scaler
        if self.scaler is not None:
            with open(path / "scaler.pkl", 'wb') as f:
                pickle.dump(self.scaler, f)
        
        # Save metadata
        metadata = {
            'config': self.config.to_dict(),
            'feature_names': self.feature_names,
            'feature_importances': self.feature_importances_,
            'model_version': self.model_version,
            'is_trained': self.is_trained,
            'saved_at': datetime.utcnow().isoformat()
        }
        
        with open(path / "metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Model saved to {path}")
    
    @classmethod
    def load(cls, path: str) -> 'GradientBoostingRiskScorer':
        """Load model from disk."""
        path = Path(path)
        
        with open(path / "metadata.json", 'r') as f:
            metadata = json.load(f)
        
        config = RiskScorerConfig(**{
            k: v for k, v in metadata['config'].items()
            if k not in ['thresholds', 'weights']
        })
        
        scorer = cls(config)
        scorer.feature_names = metadata['feature_names']
        scorer.feature_importances_ = metadata['feature_importances']
        scorer.model_version = metadata['model_version']
        scorer.is_trained = metadata['is_trained']
        
        # Load main model
        model_path = path / "model.pkl"
        if model_path.exists():
            with open(model_path, 'rb') as f:
                scorer.model = pickle.load(f)
        
        # Load component models
        for category in RiskCategory:
            comp_path = path / f"model_{category.value}.pkl"
            if comp_path.exists():
                with open(comp_path, 'rb') as f:
                    scorer.component_models[category.value] = pickle.load(f)
        
        # Load scaler
        scaler_path = path / "scaler.pkl"
        if scaler_path.exists():
            with open(scaler_path, 'rb') as f:
                scorer.scaler = pickle.load(f)
        
        return scorer
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""
        return {
            'model_type': 'Gradient Boosting Risk Scorer',
            'version': self.model_version,
            'is_trained': self.is_trained,
            'config': self.config.to_dict(),
            'n_features': len(self.feature_names),
            'top_features': self.get_feature_importance(10),
            'risk_categories': [c.value for c in RiskCategory]
        }
