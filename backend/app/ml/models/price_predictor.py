"""
Price Direction Predictor using LSTM

Deep learning model for predicting stock price direction (up/down)
using technical, fundamental, and market features.
"""
import numpy as np
from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import pickle
from pathlib import Path
from loguru import logger


class PredictionDirection(str, Enum):
    """Price direction prediction."""
    UP = "up"
    DOWN = "down"
    NEUTRAL = "neutral"


@dataclass
class PredictionResult:
    """Result of a price direction prediction."""
    symbol: str
    direction: PredictionDirection
    confidence: float  # 0-1
    probability_up: float
    probability_down: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    horizon_days: int = 5
    model_version: str = "1.0.0"
    features_used: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            'symbol': self.symbol,
            'direction': self.direction.value,
            'confidence': self.confidence,
            'probability_up': self.probability_up,
            'probability_down': self.probability_down,
            'timestamp': self.timestamp.isoformat(),
            'horizon_days': self.horizon_days,
            'model_version': self.model_version,
            'features_used': self.features_used
        }


@dataclass
class ModelConfig:
    """LSTM model configuration."""
    # Architecture
    sequence_length: int = 60  # Days of history
    lstm_units: List[int] = field(default_factory=lambda: [128, 64, 32])
    dense_units: List[int] = field(default_factory=lambda: [64, 32])
    dropout_rate: float = 0.3
    recurrent_dropout: float = 0.2
    
    # Training
    batch_size: int = 32
    epochs: int = 100
    learning_rate: float = 0.001
    early_stopping_patience: int = 10
    reduce_lr_patience: int = 5
    
    # Features
    n_features: int = 50
    prediction_horizon: int = 5  # Days ahead
    
    # Classification thresholds
    neutral_threshold: float = 0.02  # 2% move considered neutral
    
    def to_dict(self) -> dict:
        return {
            'sequence_length': self.sequence_length,
            'lstm_units': self.lstm_units,
            'dense_units': self.dense_units,
            'dropout_rate': self.dropout_rate,
            'recurrent_dropout': self.recurrent_dropout,
            'batch_size': self.batch_size,
            'epochs': self.epochs,
            'learning_rate': self.learning_rate,
            'early_stopping_patience': self.early_stopping_patience,
            'reduce_lr_patience': self.reduce_lr_patience,
            'n_features': self.n_features,
            'prediction_horizon': self.prediction_horizon,
            'neutral_threshold': self.neutral_threshold
        }


class LSTMPricePredictor:
    """
    LSTM-based price direction predictor.
    
    Architecture:
    - Stacked LSTM layers with dropout
    - Dense layers for classification
    - Binary output (up/down) with confidence
    """
    
    def __init__(self, config: Optional[ModelConfig] = None):
        self.config = config or ModelConfig()
        self.model = None
        self.scaler = None
        self.feature_names: List[str] = []
        self.is_trained = False
        self.training_history: Dict[str, List[float]] = {}
        self.model_version = "1.0.0"
        
    def build_model(self) -> Any:
        """Build the LSTM model architecture."""
        try:
            import tensorflow as tf
            from tensorflow.keras.models import Sequential
            from tensorflow.keras.layers import (
                LSTM, Dense, Dropout, BatchNormalization,
                Bidirectional, Input
            )
            from tensorflow.keras.optimizers import Adam
            from tensorflow.keras.regularizers import l2
        except ImportError:
            logger.warning("TensorFlow not available, using mock model")
            return self._build_mock_model()
        
        model = Sequential([
            Input(shape=(self.config.sequence_length, self.config.n_features))
        ])
        
        # Stacked LSTM layers
        for i, units in enumerate(self.config.lstm_units):
            return_sequences = i < len(self.config.lstm_units) - 1
            
            model.add(Bidirectional(
                LSTM(
                    units,
                    return_sequences=return_sequences,
                    dropout=self.config.dropout_rate,
                    recurrent_dropout=self.config.recurrent_dropout,
                    kernel_regularizer=l2(0.01)
                )
            ))
            model.add(BatchNormalization())
        
        # Dense layers
        for units in self.config.dense_units:
            model.add(Dense(units, activation='relu', kernel_regularizer=l2(0.01)))
            model.add(Dropout(self.config.dropout_rate))
            model.add(BatchNormalization())
        
        # Output layer (binary classification)
        model.add(Dense(1, activation='sigmoid'))
        
        # Compile
        optimizer = Adam(learning_rate=self.config.learning_rate)
        model.compile(
            optimizer=optimizer,
            loss='binary_crossentropy',
            metrics=['accuracy', 'AUC', 'Precision', 'Recall']
        )
        
        self.model = model
        logger.info(f"Built LSTM model with {model.count_params():,} parameters")
        return model
    
    def _build_mock_model(self):
        """Build a mock model for testing without TensorFlow."""
        class MockModel:
            def __init__(self, config):
                self.config = config
                
            def fit(self, X, y, **kwargs):
                return {'loss': [0.5], 'accuracy': [0.6]}
            
            def predict(self, X):
                return np.random.random((len(X), 1))
            
            def save(self, path):
                pass
                
            def summary(self):
                print("Mock LSTM Model")
        
        self.model = MockModel(self.config)
        return self.model
    
    def prepare_sequences(
        self,
        features: np.ndarray,
        targets: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Prepare sequential data for LSTM.
        
        Args:
            features: Shape (n_samples, n_features)
            targets: Shape (n_samples,) - optional for inference
            
        Returns:
            X: Shape (n_sequences, sequence_length, n_features)
            y: Shape (n_sequences,) or None
        """
        n_samples = len(features)
        seq_len = self.config.sequence_length
        
        if n_samples <= seq_len:
            raise ValueError(f"Need at least {seq_len + 1} samples, got {n_samples}")
        
        # Create sequences
        X = []
        y = [] if targets is not None else None
        
        for i in range(seq_len, n_samples):
            X.append(features[i - seq_len:i])
            if targets is not None:
                y.append(targets[i])
        
        X = np.array(X)
        if y is not None:
            y = np.array(y)
            
        return X, y
    
    def prepare_targets(
        self,
        prices: np.ndarray,
        horizon: Optional[int] = None
    ) -> np.ndarray:
        """
        Prepare binary targets for price direction.
        
        Args:
            prices: Array of closing prices
            horizon: Prediction horizon in days
            
        Returns:
            Binary targets: 1 for up, 0 for down
        """
        horizon = horizon or self.config.prediction_horizon
        
        # Calculate future returns
        future_returns = np.zeros(len(prices))
        for i in range(len(prices) - horizon):
            future_returns[i] = (prices[i + horizon] - prices[i]) / prices[i]
        
        # Binary classification
        # Returns above neutral_threshold = 1 (up)
        # Returns below -neutral_threshold = 0 (down)
        # Neutral returns are labeled based on sign
        targets = (future_returns > 0).astype(int)
        
        return targets
    
    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
        verbose: int = 1
    ) -> Dict[str, List[float]]:
        """
        Train the LSTM model.
        
        Args:
            X_train: Training features (n_samples, n_features)
            y_train: Training targets
            X_val: Validation features
            y_val: Validation targets
            verbose: Verbosity level
            
        Returns:
            Training history
        """
        try:
            from tensorflow.keras.callbacks import (
                EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
            )
            from sklearn.preprocessing import StandardScaler
            from sklearn.utils.class_weight import compute_class_weight
        except ImportError:
            logger.warning("Required libraries not available")
            self.is_trained = True
            return {'loss': [0.5], 'accuracy': [0.6]}
        
        logger.info(f"Training LSTM model with {len(X_train)} samples")
        
        # Scale features
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        
        if X_val is not None:
            X_val_scaled = self.scaler.transform(X_val)
        
        # Prepare sequences
        X_train_seq, y_train_seq = self.prepare_sequences(X_train_scaled, y_train)
        
        if X_val is not None and y_val is not None:
            X_val_seq, y_val_seq = self.prepare_sequences(X_val_scaled, y_val)
            validation_data = (X_val_seq, y_val_seq)
        else:
            validation_data = None
        
        # Update config with actual feature count
        self.config.n_features = X_train.shape[1]
        
        # Build model
        if self.model is None:
            self.build_model()
        
        # Handle class imbalance
        class_weights = compute_class_weight(
            'balanced',
            classes=np.unique(y_train_seq),
            y=y_train_seq
        )
        class_weight_dict = dict(enumerate(class_weights))
        
        # Callbacks
        callbacks = [
            EarlyStopping(
                monitor='val_loss' if validation_data else 'loss',
                patience=self.config.early_stopping_patience,
                restore_best_weights=True,
                verbose=1
            ),
            ReduceLROnPlateau(
                monitor='val_loss' if validation_data else 'loss',
                factor=0.5,
                patience=self.config.reduce_lr_patience,
                min_lr=1e-7,
                verbose=1
            )
        ]
        
        # Train
        history = self.model.fit(
            X_train_seq, y_train_seq,
            batch_size=self.config.batch_size,
            epochs=self.config.epochs,
            validation_data=validation_data,
            class_weight=class_weight_dict,
            callbacks=callbacks,
            verbose=verbose
        )
        
        self.training_history = history.history
        self.is_trained = True
        
        logger.info(f"Training complete. Final accuracy: {history.history['accuracy'][-1]:.4f}")
        
        return history.history
    
    def predict(
        self,
        features: np.ndarray,
        return_proba: bool = True
    ) -> List[PredictionResult]:
        """
        Make predictions on new data.
        
        Args:
            features: Shape (n_samples, n_features) or (sequence_length, n_features)
            return_proba: Whether to return probabilities
            
        Returns:
            List of PredictionResult objects
        """
        if not self.is_trained:
            raise ValueError("Model not trained yet")
        
        # Scale features
        if self.scaler is not None:
            features_scaled = self.scaler.transform(features)
        else:
            features_scaled = features
        
        # Prepare sequences if needed
        if len(features_scaled.shape) == 2:
            if len(features_scaled) >= self.config.sequence_length:
                X_seq, _ = self.prepare_sequences(features_scaled)
            else:
                # Pad if not enough history
                padding = np.zeros((
                    self.config.sequence_length - len(features_scaled),
                    features_scaled.shape[1]
                ))
                features_padded = np.vstack([padding, features_scaled])
                X_seq = features_padded.reshape(1, self.config.sequence_length, -1)
        else:
            X_seq = features_scaled
        
        # Predict
        probabilities = self.model.predict(X_seq, verbose=0)
        
        # Create results
        results = []
        for i, prob in enumerate(probabilities):
            prob_up = float(prob[0])
            prob_down = 1 - prob_up
            
            # Determine direction
            if prob_up > 0.5 + self.config.neutral_threshold / 2:
                direction = PredictionDirection.UP
            elif prob_up < 0.5 - self.config.neutral_threshold / 2:
                direction = PredictionDirection.DOWN
            else:
                direction = PredictionDirection.NEUTRAL
            
            # Confidence is distance from 0.5
            confidence = abs(prob_up - 0.5) * 2
            
            results.append(PredictionResult(
                symbol="",  # Will be set by caller
                direction=direction,
                confidence=confidence,
                probability_up=prob_up,
                probability_down=prob_down,
                horizon_days=self.config.prediction_horizon,
                model_version=self.model_version,
                features_used=self.feature_names
            ))
        
        return results
    
    def predict_single(
        self,
        symbol: str,
        features: np.ndarray
    ) -> PredictionResult:
        """
        Make a single prediction for a symbol.
        
        Args:
            symbol: Stock symbol
            features: Feature matrix with history
            
        Returns:
            PredictionResult
        """
        results = self.predict(features)
        if results:
            result = results[-1]  # Get last prediction
            result.symbol = symbol
            return result
        raise ValueError("No predictions generated")
    
    def evaluate(
        self,
        X_test: np.ndarray,
        y_test: np.ndarray
    ) -> Dict[str, float]:
        """
        Evaluate model performance.
        
        Args:
            X_test: Test features
            y_test: Test targets
            
        Returns:
            Dictionary of metrics
        """
        try:
            from sklearn.metrics import (
                accuracy_score, precision_score, recall_score,
                f1_score, roc_auc_score, confusion_matrix
            )
        except ImportError:
            return {'accuracy': 0.5}
        
        # Scale and prepare sequences
        if self.scaler is not None:
            X_test_scaled = self.scaler.transform(X_test)
        else:
            X_test_scaled = X_test
            
        X_test_seq, y_test_seq = self.prepare_sequences(X_test_scaled, y_test)
        
        # Predict
        y_proba = self.model.predict(X_test_seq, verbose=0)
        y_pred = (y_proba > 0.5).astype(int).flatten()
        
        # Calculate metrics
        metrics = {
            'accuracy': float(accuracy_score(y_test_seq, y_pred)),
            'precision': float(precision_score(y_test_seq, y_pred, zero_division=0)),
            'recall': float(recall_score(y_test_seq, y_pred, zero_division=0)),
            'f1_score': float(f1_score(y_test_seq, y_pred, zero_division=0)),
            'roc_auc': float(roc_auc_score(y_test_seq, y_proba)),
        }
        
        # Confusion matrix
        cm = confusion_matrix(y_test_seq, y_pred)
        metrics['true_negatives'] = int(cm[0, 0])
        metrics['false_positives'] = int(cm[0, 1])
        metrics['false_negatives'] = int(cm[1, 0])
        metrics['true_positives'] = int(cm[1, 1])
        
        return metrics
    
    def save(self, path: str):
        """Save model and configuration."""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        
        # Save model
        if self.model is not None:
            try:
                self.model.save(path / "model.keras")
            except:
                # Fallback for mock model
                pass
        
        # Save scaler
        if self.scaler is not None:
            with open(path / "scaler.pkl", 'wb') as f:
                pickle.dump(self.scaler, f)
        
        # Save config and metadata
        metadata = {
            'config': self.config.to_dict(),
            'feature_names': self.feature_names,
            'model_version': self.model_version,
            'is_trained': self.is_trained,
            'training_history': self.training_history,
            'saved_at': datetime.utcnow().isoformat()
        }
        
        with open(path / "metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Model saved to {path}")
    
    @classmethod
    def load(cls, path: str) -> 'LSTMPricePredictor':
        """Load model from path."""
        path = Path(path)
        
        # Load metadata
        with open(path / "metadata.json", 'r') as f:
            metadata = json.load(f)
        
        # Create instance
        config = ModelConfig(**metadata['config'])
        predictor = cls(config)
        predictor.feature_names = metadata['feature_names']
        predictor.model_version = metadata['model_version']
        predictor.is_trained = metadata['is_trained']
        predictor.training_history = metadata.get('training_history', {})
        
        # Load model
        try:
            from tensorflow.keras.models import load_model
            predictor.model = load_model(path / "model.keras")
        except:
            predictor._build_mock_model()
        
        # Load scaler
        scaler_path = path / "scaler.pkl"
        if scaler_path.exists():
            with open(scaler_path, 'rb') as f:
                predictor.scaler = pickle.load(f)
        
        logger.info(f"Model loaded from {path}")
        return predictor
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information and configuration."""
        return {
            'model_type': 'LSTM Price Direction Predictor',
            'version': self.model_version,
            'is_trained': self.is_trained,
            'config': self.config.to_dict(),
            'feature_count': len(self.feature_names),
            'feature_names': self.feature_names,
            'training_history': self.training_history
        }


class EnsemblePricePredictor:
    """
    Ensemble of multiple LSTM models for robust predictions.
    """
    
    def __init__(self, n_models: int = 3):
        self.n_models = n_models
        self.models: List[LSTMPricePredictor] = []
        self.weights: List[float] = []
        
    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None
    ):
        """Train ensemble of models with different initializations."""
        from sklearn.model_selection import KFold
        
        self.models = []
        self.weights = []
        
        # Train multiple models
        for i in range(self.n_models):
            logger.info(f"Training ensemble model {i + 1}/{self.n_models}")
            
            # Create model with slightly different config
            config = ModelConfig()
            config.dropout_rate = 0.2 + 0.1 * i  # Vary dropout
            
            model = LSTMPricePredictor(config)
            model.fit(X_train, y_train, X_val, y_val, verbose=0)
            
            # Evaluate and set weight based on validation performance
            if X_val is not None and y_val is not None:
                metrics = model.evaluate(X_val, y_val)
                weight = metrics.get('roc_auc', 0.5)
            else:
                weight = 1.0 / self.n_models
            
            self.models.append(model)
            self.weights.append(weight)
        
        # Normalize weights
        total_weight = sum(self.weights)
        self.weights = [w / total_weight for w in self.weights]
        
        logger.info(f"Ensemble training complete. Model weights: {self.weights}")
    
    def predict(self, features: np.ndarray) -> List[PredictionResult]:
        """Make weighted ensemble predictions."""
        if not self.models:
            raise ValueError("Ensemble not trained")
        
        # Collect predictions from all models
        all_probs = []
        for model in self.models:
            results = model.predict(features)
            probs = [r.probability_up for r in results]
            all_probs.append(probs)
        
        # Weighted average
        all_probs = np.array(all_probs)
        weights = np.array(self.weights).reshape(-1, 1)
        ensemble_probs = np.sum(all_probs * weights, axis=0)
        
        # Create results
        results = []
        for prob_up in ensemble_probs:
            prob_down = 1 - prob_up
            
            if prob_up > 0.55:
                direction = PredictionDirection.UP
            elif prob_up < 0.45:
                direction = PredictionDirection.DOWN
            else:
                direction = PredictionDirection.NEUTRAL
            
            confidence = abs(prob_up - 0.5) * 2
            
            results.append(PredictionResult(
                symbol="",
                direction=direction,
                confidence=confidence,
                probability_up=float(prob_up),
                probability_down=float(prob_down),
                model_version=f"ensemble-{self.n_models}"
            ))
        
        return results
