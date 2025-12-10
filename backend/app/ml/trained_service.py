"""
Trained Model Inference Service for Backend

This module loads and uses trained ML models from the ml-pipeline
for making predictions in the backend API.
"""
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from dataclasses import dataclass
import json

import numpy as np
import pandas as pd
from loguru import logger

# Try importing ML libraries
try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False
    logger.warning("joblib not available - trained RF models cannot be loaded")

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available - LSTM models cannot be loaded")


@dataclass
class TrainedPrediction:
    """Prediction from trained model"""
    symbol: str
    signal: str
    confidence: float
    probability_up: float
    probability_down: float
    model_type: str
    price: float
    price_target: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    features_used: int
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "signal": self.signal,
            "confidence": self.confidence,
            "probability_up": self.probability_up,
            "probability_down": self.probability_down,
            "model_type": self.model_type,
            "price": self.price,
            "price_target": self.price_target,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "features_used": self.features_used,
            "timestamp": self.timestamp.isoformat()
        }


class TrainedModelService:
    """
    Service to load and use trained ML models.
    """
    
    # Default paths relative to project root
    DEFAULT_MODEL_PATHS = [
        "ml-pipeline/models",
        "backend/ml_models",
        "models"
    ]
    
    def __init__(self, model_dir: Optional[str] = None):
        """Initialize the trained model service."""
        self.model_dir = self._find_model_dir(model_dir)
        self.rf_model = None
        self.rf_metadata = None
        self.lstm_model = None
        self.lstm_metadata = None
        self.feature_scaler = None
        self.is_loaded = False
        
        # Feature engineering parameters (must match training)
        self.feature_columns = None
        
        logger.info(f"TrainedModelService initialized with model_dir: {self.model_dir}")
    
    def _find_model_dir(self, model_dir: Optional[str]) -> Optional[Path]:
        """Find the model directory."""
        if model_dir:
            path = Path(model_dir)
            if path.exists():
                return path
        
        # Try default paths
        base_paths = [
            Path(__file__).parent.parent.parent.parent.parent,  # Project root from backend/app/ml/trained_service.py
            Path.cwd(),
            Path("/app"),  # Docker container
        ]
        
        for base in base_paths:
            for rel_path in self.DEFAULT_MODEL_PATHS:
                path = base / rel_path
                if path.exists():
                    logger.info(f"Found model directory: {path}")
                    return path
        
        logger.warning("No model directory found")
        return None
    
    def load_models(self) -> Dict[str, bool]:
        """Load all available trained models."""
        results = {"random_forest": False, "lstm": False}
        
        if self.model_dir is None:
            logger.warning("No model directory configured")
            return results
        
        # Load Random Forest
        results["random_forest"] = self._load_random_forest()
        
        # Load LSTM
        results["lstm"] = self._load_lstm()
        
        self.is_loaded = any(results.values())
        return results
    
    def _load_random_forest(self) -> bool:
        """Load Random Forest model."""
        if not JOBLIB_AVAILABLE or self.model_dir is None:
            return False
        
        try:
            # Try multiple file names
            possible_names = [
                "random_forest_multi",
                "stock_predictor_random_forest_model",
                "stock_predictor_random_forest"
            ]
            
            model_path = None
            metadata_path = None
            
            for name in possible_names:
                # Check with .pkl extension
                path = self.model_dir / f"{name}.pkl"
                if path.exists():
                    model_path = path
                    # Find corresponding metadata
                    for meta_suffix in ["_metadata.json", ".json"]:
                        meta_path = self.model_dir / f"{name.replace('_model', '')}{meta_suffix}"
                        if meta_path.exists():
                            metadata_path = meta_path
                            break
                    break
            
            if model_path is None:
                logger.debug(f"RF model not found in {self.model_dir}")
                return False
            
            self.rf_model = joblib.load(model_path)
            
            if metadata_path and metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    self.rf_metadata = json.load(f)
                    self.feature_columns = self.rf_metadata.get('feature_columns', [])
            
            logger.info(f"Loaded Random Forest model from {model_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading Random Forest: {e}")
            return False
    
    def _load_lstm(self) -> bool:
        """Load LSTM model."""
        if not TORCH_AVAILABLE or self.model_dir is None:
            return False
        
        try:
            model_path = self.model_dir / "lstm_multi.pt"
            metadata_path = self.model_dir / "lstm_multi_metadata.json"
            
            if not model_path.exists():
                logger.debug(f"LSTM model not found at {model_path}")
                return False
            
            # Load metadata
            if not metadata_path.exists():
                logger.warning("LSTM metadata not found")
                return False
            
            with open(metadata_path, 'r') as f:
                self.lstm_metadata = json.load(f)
            
            # We'd need to import the model class - for now skip LSTM
            # as it requires the training code to be available
            logger.info("LSTM model found but requires training code to load")
            return False
            
        except Exception as e:
            logger.error(f"Error loading LSTM: {e}")
            return False
    
    def calculate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate technical indicator features for prediction.
        Must match the feature engineering used during training.
        """
        try:
            import ta
        except ImportError:
            logger.warning("ta library not available - using basic features")
            return self._calculate_basic_features(df)
        
        features = df.copy()
        
        # Price-based features
        features['Returns'] = features['Close'].pct_change()
        features['Log_Returns'] = np.log(features['Close'] / features['Close'].shift(1))
        
        # Moving Averages
        for window in [5, 10, 20, 50]:
            features[f'SMA_{window}'] = features['Close'].rolling(window=window).mean()
            features[f'EMA_{window}'] = features['Close'].ewm(span=window, adjust=False).mean()
        
        # RSI
        features['RSI_14'] = ta.momentum.RSIIndicator(features['Close'], window=14).rsi()
        
        # MACD
        macd = ta.trend.MACD(features['Close'])
        features['MACD'] = macd.macd()
        features['MACD_Signal'] = macd.macd_signal()
        features['MACD_Hist'] = macd.macd_diff()
        
        # Bollinger Bands
        bb = ta.volatility.BollingerBands(features['Close'], window=20, window_dev=2)
        features['BB_High'] = bb.bollinger_hband()
        features['BB_Low'] = bb.bollinger_lband()
        features['BB_Mid'] = bb.bollinger_mavg()
        features['BB_Width'] = (features['BB_High'] - features['BB_Low']) / features['BB_Mid']
        
        # ATR
        features['ATR_14'] = ta.volatility.AverageTrueRange(
            features['High'], features['Low'], features['Close'], window=14
        ).average_true_range()
        
        # Volume features
        features['Volume_SMA_20'] = features['Volume'].rolling(window=20).mean()
        features['Volume_Ratio'] = features['Volume'] / features['Volume_SMA_20']
        
        # Price position
        features['Price_Position'] = (features['Close'] - features['Low']) / (features['High'] - features['Low'] + 1e-10)
        
        # Momentum
        features['ROC_5'] = features['Close'].pct_change(periods=5) * 100
        features['ROC_10'] = features['Close'].pct_change(periods=10) * 100
        
        return features.dropna()
    
    def _calculate_basic_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate basic features without ta library."""
        features = df.copy()
        
        features['Returns'] = features['Close'].pct_change()
        
        for window in [5, 10, 20]:
            features[f'SMA_{window}'] = features['Close'].rolling(window=window).mean()
        
        # Simple RSI calculation
        delta = features['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-10)
        features['RSI_14'] = 100 - (100 / (1 + rs))
        
        return features.dropna()
    
    async def predict(
        self,
        df: pd.DataFrame,
        symbol: str,
        current_price: float
    ) -> Optional[TrainedPrediction]:
        """
        Make prediction using trained model.
        
        Args:
            df: DataFrame with OHLCV data (at least 50 rows)
            symbol: Stock symbol
            current_price: Current price
            
        Returns:
            TrainedPrediction or None
        """
        if self.rf_model is None:
            logger.debug("No trained model available")
            return None
        
        try:
            # Calculate features
            features_df = self.calculate_features(df)
            
            if len(features_df) < 1:
                logger.warning(f"Not enough data to calculate features for {symbol}")
                return None
            
            # Get feature columns (exclude non-feature columns)
            exclude_cols = ['Open', 'High', 'Low', 'Close', 'Volume', 'Adj Close', 
                           'Date', 'Symbol', 'Target', 'Future_Return']
            feature_cols = [c for c in features_df.columns if c not in exclude_cols]
            
            # If we have saved feature columns, use those
            if self.feature_columns:
                feature_cols = [c for c in self.feature_columns if c in features_df.columns]
            
            # Get last row for prediction
            X = features_df[feature_cols].iloc[[-1]].fillna(0)
            
            # Make prediction
            pred = self.rf_model.predict(X)[0]
            proba = self.rf_model.predict_proba(X)[0]
            
            prob_down = proba[0]
            prob_up = proba[1] if len(proba) > 1 else 1 - proba[0]
            
            # Determine signal
            if prob_up > 0.6:
                signal = "BUY"
            elif prob_down > 0.6:
                signal = "SELL"
            else:
                signal = "HOLD"
            
            confidence = max(prob_up, prob_down)
            
            # Calculate price targets
            expected_move = (prob_up - 0.5) * 0.1  # Scale probability to expected move
            price_target = current_price * (1 + expected_move)
            
            if signal == "BUY":
                stop_loss = current_price * 0.97
                take_profit = current_price * 1.05
            elif signal == "SELL":
                stop_loss = current_price * 1.03
                take_profit = current_price * 0.95
            else:
                stop_loss = None
                take_profit = None
            
            return TrainedPrediction(
                symbol=symbol,
                signal=signal,
                confidence=round(confidence, 3),
                probability_up=round(prob_up, 3),
                probability_down=round(prob_down, 3),
                model_type="RandomForest",
                price=round(current_price, 2),
                price_target=round(price_target, 2) if price_target else None,
                stop_loss=round(stop_loss, 2) if stop_loss else None,
                take_profit=round(take_profit, 2) if take_profit else None,
                features_used=len(feature_cols),
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error making prediction for {symbol}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about loaded models."""
        return {
            "model_dir": str(self.model_dir) if self.model_dir else None,
            "is_loaded": self.is_loaded,
            "random_forest": {
                "loaded": self.rf_model is not None,
                "metadata": self.rf_metadata
            },
            "lstm": {
                "loaded": self.lstm_model is not None,
                "metadata": self.lstm_metadata
            }
        }


# Singleton instance
_trained_service: Optional[TrainedModelService] = None


def get_trained_model_service() -> TrainedModelService:
    """Get or create the trained model service singleton."""
    global _trained_service
    
    if _trained_service is None:
        _trained_service = TrainedModelService()
        results = _trained_service.load_models()
        logger.info(f"Trained model loading results: {results}")
    
    return _trained_service
