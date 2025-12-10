"""
ML Model Training

Trains Random Forest and LSTM models for stock prediction.
"""
import os
import json
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass, asdict
import logging

# Scikit-learn
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    classification_report, confusion_matrix
)

# Local imports
from data_collector import load_data, get_symbol_data, DEFAULT_SYMBOLS
from feature_engineering import (
    calculate_technical_features, 
    create_labels, 
    prepare_training_data
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Model directory
MODEL_DIR = Path(__file__).parent.parent / "models"
MODEL_DIR.mkdir(exist_ok=True)


@dataclass
class ModelMetrics:
    """Model performance metrics."""
    accuracy: float
    precision: float
    recall: float
    f1: float
    train_accuracy: float
    val_accuracy: float
    test_accuracy: float
    confusion_matrix: List[List[int]]
    classification_report: str
    feature_importance: Dict[str, float]
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TrainedModel:
    """Container for a trained model with metadata."""
    model_name: str
    model_type: str
    version: str
    trained_at: str
    symbols_used: List[str]
    feature_names: List[str]
    metrics: ModelMetrics
    hyperparameters: Dict[str, Any]
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['metrics'] = self.metrics.to_dict()
        return d


class StockPredictor:
    """
    Stock price direction predictor using ensemble methods.
    """
    
    def __init__(self, model_type: str = "random_forest"):
        self.model_type = model_type
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names: List[str] = []
        self.is_trained = False
        self.metadata: Optional[TrainedModel] = None
        
    def _create_model(self, **kwargs) -> Any:
        """Create the ML model."""
        if self.model_type == "random_forest":
            default_params = {
                'n_estimators': 100,
                'max_depth': 5,  # Reduced to prevent overfitting
                'min_samples_split': 50,  # Increased
                'min_samples_leaf': 20,  # Increased
                'max_features': 'sqrt',
                'n_jobs': -1,
                'random_state': 42,
                'class_weight': 'balanced',
                'bootstrap': True,
                'oob_score': True  # Out-of-bag score for validation
            }
            default_params.update(kwargs)
            return RandomForestClassifier(**default_params)
        
        elif self.model_type == "gradient_boosting":
            default_params = {
                'n_estimators': 100,
                'max_depth': 3,  # Very shallow trees
                'learning_rate': 0.05,  # Slower learning
                'min_samples_split': 50,
                'min_samples_leaf': 20,
                'subsample': 0.8,  # Add subsampling
                'random_state': 42
            }
            default_params.update(kwargs)
            return GradientBoostingClassifier(**default_params)
        
        else:
            raise ValueError(f"Unknown model type: {self.model_type}")
    
    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        feature_names: List[str],
        **model_params
    ) -> ModelMetrics:
        """
        Train the model.
        
        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Validation features
            y_val: Validation labels
            feature_names: Names of features
            **model_params: Additional model parameters
            
        Returns:
            ModelMetrics with performance data
        """
        self.feature_names = feature_names
        
        # Scale features
        logger.info("Scaling features...")
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)
        
        # Create and train model
        logger.info(f"Training {self.model_type} model...")
        self.model = self._create_model(**model_params)
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate
        train_pred = self.model.predict(X_train_scaled)
        val_pred = self.model.predict(X_val_scaled)
        
        train_acc = accuracy_score(y_train, train_pred)
        val_acc = accuracy_score(y_val, val_pred)
        
        logger.info(f"Train accuracy: {train_acc:.4f}")
        logger.info(f"Validation accuracy: {val_acc:.4f}")
        
        # Get feature importance
        if hasattr(self.model, 'feature_importances_'):
            importance = dict(zip(
                feature_names,
                [float(x) for x in self.model.feature_importances_]
            ))
            # Sort by importance
            importance = dict(sorted(
                importance.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:20])  # Top 20
        else:
            importance = {}
        
        self.is_trained = True
        
        return ModelMetrics(
            accuracy=val_acc,
            precision=precision_score(y_val, val_pred, average='weighted', zero_division=0),
            recall=recall_score(y_val, val_pred, average='weighted', zero_division=0),
            f1=f1_score(y_val, val_pred, average='weighted', zero_division=0),
            train_accuracy=train_acc,
            val_accuracy=val_acc,
            test_accuracy=0.0,  # Will be set after test evaluation
            confusion_matrix=confusion_matrix(y_val, val_pred).tolist(),
            classification_report=classification_report(y_val, val_pred),
            feature_importance=importance
        )
    
    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> float:
        """Evaluate on test set."""
        if not self.is_trained:
            raise ValueError("Model not trained")
        
        X_test_scaled = self.scaler.transform(X_test)
        y_pred = self.model.predict(X_test_scaled)
        
        acc = accuracy_score(y_test, y_pred)
        logger.info(f"Test accuracy: {acc:.4f}")
        
        return acc
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions."""
        if not self.is_trained:
            raise ValueError("Model not trained")
        
        X_scaled = self.scaler.transform(X)
        return self.model.predict(X_scaled)
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Get prediction probabilities."""
        if not self.is_trained:
            raise ValueError("Model not trained")
        
        X_scaled = self.scaler.transform(X)
        return self.model.predict_proba(X_scaled)
    
    def save(self, name: str, symbols: List[str], metrics: ModelMetrics, hyperparams: Dict[str, Any]):
        """Save model and metadata."""
        version = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create metadata
        self.metadata = TrainedModel(
            model_name=name,
            model_type=self.model_type,
            version=version,
            trained_at=datetime.now().isoformat(),
            symbols_used=symbols,
            feature_names=self.feature_names,
            metrics=metrics,
            hyperparameters=hyperparams
        )
        
        # Save model
        model_path = MODEL_DIR / f"{name}_model.pkl"
        with open(model_path, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'scaler': self.scaler,
                'feature_names': self.feature_names
            }, f)
        
        # Save metadata
        metadata_path = MODEL_DIR / f"{name}_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(self.metadata.to_dict(), f, indent=2)
        
        logger.info(f"Model saved to {model_path}")
        logger.info(f"Metadata saved to {metadata_path}")
        
        return model_path, metadata_path
    
    def load(self, name: str):
        """Load model and metadata."""
        model_path = MODEL_DIR / f"{name}_model.pkl"
        metadata_path = MODEL_DIR / f"{name}_metadata.json"
        
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")
        
        # Load model
        with open(model_path, 'rb') as f:
            data = pickle.load(f)
            self.model = data['model']
            self.scaler = data['scaler']
            self.feature_names = data['feature_names']
        
        # Load metadata
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                metadata_dict = json.load(f)
                # Reconstruct metadata (simplified)
                self.metadata = metadata_dict
        
        self.is_trained = True
        logger.info(f"Model loaded from {model_path}")


def train_multi_symbol_model(
    symbols: List[str] = None,
    model_type: str = "random_forest",
    horizon: int = 5,
    threshold: float = 0.02
) -> Tuple[StockPredictor, ModelMetrics]:
    """
    Train a model on multiple symbols.
    
    Args:
        symbols: List of symbols to train on
        model_type: Type of model (random_forest, gradient_boosting)
        horizon: Prediction horizon in days
        threshold: Threshold for buy/sell classification
        
    Returns:
        Trained model and metrics
    """
    if symbols is None:
        symbols = DEFAULT_SYMBOLS
    
    logger.info(f"Training {model_type} model on {len(symbols)} symbols")
    logger.info(f"Horizon: {horizon} days, Threshold: {threshold*100}%")
    
    # Load data
    df = load_data()
    
    # Process each symbol
    all_data = []
    
    for symbol in symbols:
        try:
            symbol_df = get_symbol_data(df, symbol)
            if len(symbol_df) < 500:  # Need sufficient data
                logger.warning(f"Skipping {symbol}: insufficient data ({len(symbol_df)} rows)")
                continue
            
            # Calculate features
            df_features = calculate_technical_features(symbol_df)
            
            # Create labels
            df_labels = create_labels(df_features, horizon=horizon, threshold=threshold)
            
            all_data.append(df_labels)
            logger.info(f"  {symbol}: {len(df_labels)} samples")
            
        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}")
    
    if not all_data:
        raise ValueError("No data available for training")
    
    # Combine all data
    combined_df = pd.concat(all_data, axis=0)
    logger.info(f"Total samples: {len(combined_df)}")
    
    # Prepare training data
    X_train, X_val, X_test, y_train, y_val, y_test, feature_names = prepare_training_data(
        combined_df,
        target_column='target_binary'
    )
    
    # Train model
    predictor = StockPredictor(model_type=model_type)
    metrics = predictor.train(X_train, y_train, X_val, y_val, feature_names)
    
    # Evaluate on test set
    test_acc = predictor.evaluate(X_test, y_test)
    metrics.test_accuracy = test_acc
    
    # Save model
    model_name = f"stock_predictor_{model_type}"
    predictor.save(
        name=model_name,
        symbols=symbols,
        metrics=metrics,
        hyperparams={
            'horizon': horizon,
            'threshold': threshold,
            'model_type': model_type
        }
    )
    
    return predictor, metrics


if __name__ == "__main__":
    print("=" * 60)
    print("ML Model Training")
    print("=" * 60)
    
    # Train Random Forest model
    print("\n🌲 Training Random Forest model...")
    try:
        predictor, metrics = train_multi_symbol_model(
            model_type="random_forest",
            horizon=5,
            threshold=0.02
        )
        
        print("\n" + "=" * 60)
        print("✅ Training Complete!")
        print("=" * 60)
        print(f"\n📊 Model Performance:")
        print(f"   Train Accuracy:      {metrics.train_accuracy:.2%}")
        print(f"   Validation Accuracy: {metrics.val_accuracy:.2%}")
        print(f"   Test Accuracy:       {metrics.test_accuracy:.2%}")
        print(f"   Precision:           {metrics.precision:.2%}")
        print(f"   Recall:              {metrics.recall:.2%}")
        print(f"   F1 Score:            {metrics.f1:.2%}")
        
        print(f"\n🔑 Top 10 Important Features:")
        for i, (feat, imp) in enumerate(list(metrics.feature_importance.items())[:10], 1):
            print(f"   {i:2}. {feat}: {imp:.4f}")
        
        print(f"\n📁 Model saved to: ml-pipeline/models/")
        
    except FileNotFoundError:
        print("\n❌ No data file found!")
        print("   Run data_collector.py first to download historical data.")
    except Exception as e:
        print(f"\n❌ Training failed: {e}")
        raise
