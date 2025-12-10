"""
ML Inference Service

Service to load trained models and make predictions
for use in the backend API.
"""
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass

import numpy as np
import pandas as pd
import joblib

# Try to import torch, but don't fail if not available
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


@dataclass
class Prediction:
    """Single prediction result"""
    symbol: str
    signal: str  # "BUY", "SELL", "HOLD"
    confidence: float
    probability_up: float
    probability_down: float
    model_type: str
    model_version: str
    timestamp: datetime
    features_used: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "signal": self.signal,
            "confidence": self.confidence,
            "probability_up": self.probability_up,
            "probability_down": self.probability_down,
            "model_type": self.model_type,
            "model_version": self.model_version,
            "timestamp": self.timestamp.isoformat(),
            "features_used": self.features_used
        }


class InferenceService:
    """
    Service to load trained models and make predictions.
    Supports both Random Forest and LSTM models.
    """
    
    def __init__(self, models_dir: str = "models"):
        """
        Initialize the inference service.
        
        Args:
            models_dir: Directory containing trained models
        """
        self.models_dir = Path(models_dir)
        self.rf_model = None
        self.rf_metadata = None
        self.lstm_model = None
        self.lstm_metadata = None
        self.feature_scaler = None
        
    def load_random_forest(self, model_name: str = "random_forest_multi") -> bool:
        """Load a trained Random Forest model."""
        try:
            model_path = self.models_dir / f"{model_name}.pkl"
            metadata_path = self.models_dir / f"{model_name}_metadata.json"
            
            if not model_path.exists():
                print(f"Model not found: {model_path}")
                return False
            
            self.rf_model = joblib.load(model_path)
            
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    self.rf_metadata = json.load(f)
            else:
                self.rf_metadata = {"model_type": "random_forest", "version": "unknown"}
                
            print(f"✅ Loaded Random Forest model: {model_name}")
            return True
            
        except Exception as e:
            print(f"Error loading Random Forest model: {e}")
            return False
    
    def load_lstm(self, model_name: str = "lstm_multi") -> bool:
        """Load a trained LSTM model."""
        if not TORCH_AVAILABLE:
            print("PyTorch not available. Cannot load LSTM model.")
            return False
            
        try:
            model_path = self.models_dir / f"{model_name}.pt"
            metadata_path = self.models_dir / f"{model_name}_metadata.json"
            
            if not model_path.exists():
                print(f"Model not found: {model_path}")
                return False
            
            # Load metadata first to get model config
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    self.lstm_metadata = json.load(f)
            else:
                print("LSTM metadata not found, cannot load model architecture")
                return False
            
            # Import LSTM model class
            from train_lstm import LSTMModel
            
            # Recreate model architecture
            config = self.lstm_metadata
            self.lstm_model = LSTMModel(
                input_size=config['input_size'],
                hidden_size=config.get('hidden_size', 128),
                num_layers=config.get('num_layers', 2),
                num_classes=2,
                dropout=config.get('dropout', 0.2)
            )
            
            # Load weights
            checkpoint = torch.load(model_path, map_location='cpu')
            self.lstm_model.load_state_dict(checkpoint['model_state_dict'])
            self.lstm_model.eval()
            
            # Load scaler if available
            scaler_path = self.models_dir / f"{model_name}_scaler.pkl"
            if scaler_path.exists():
                self.feature_scaler = joblib.load(scaler_path)
            
            print(f"✅ Loaded LSTM model: {model_name}")
            return True
            
        except Exception as e:
            print(f"Error loading LSTM model: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def load_all_models(self) -> Dict[str, bool]:
        """Load all available models."""
        results = {}
        results['random_forest'] = self.load_random_forest()
        results['lstm'] = self.load_lstm()
        return results
    
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare features for prediction.
        Uses the same feature engineering as training.
        """
        from feature_engineering import FeatureEngineer
        
        engineer = FeatureEngineer()
        features_df = engineer.add_all_features(df)
        
        # Drop rows with NaN
        features_df = features_df.dropna()
        
        return features_df
    
    def predict_rf(
        self, 
        features: pd.DataFrame,
        symbol: str = "UNKNOWN"
    ) -> Optional[Prediction]:
        """Make prediction using Random Forest model."""
        if self.rf_model is None:
            return None
        
        try:
            # Get feature columns (exclude date, symbol, target columns)
            exclude_cols = ['Date', 'Symbol', 'Target', 'Future_Return', 'Open', 'High', 'Low', 'Close', 'Volume', 'Adj Close']
            feature_cols = [c for c in features.columns if c not in exclude_cols]
            
            # Use last row for prediction
            X = features[feature_cols].iloc[[-1]]
            
            # Handle any remaining NaN
            X = X.fillna(0)
            
            # Make prediction
            pred = self.rf_model.predict(X)[0]
            proba = self.rf_model.predict_proba(X)[0]
            
            # Determine signal
            prob_up = proba[1] if len(proba) > 1 else proba[0]
            prob_down = proba[0] if len(proba) > 1 else 1 - proba[0]
            
            if prob_up > 0.6:
                signal = "BUY"
            elif prob_down > 0.6:
                signal = "SELL"
            else:
                signal = "HOLD"
            
            confidence = max(prob_up, prob_down)
            
            return Prediction(
                symbol=symbol,
                signal=signal,
                confidence=confidence,
                probability_up=prob_up,
                probability_down=prob_down,
                model_type="random_forest",
                model_version=self.rf_metadata.get('version', 'v1'),
                timestamp=datetime.now(),
                features_used=len(feature_cols)
            )
            
        except Exception as e:
            print(f"Error in RF prediction: {e}")
            return None
    
    def predict_lstm(
        self,
        features: pd.DataFrame,
        symbol: str = "UNKNOWN",
        seq_length: int = 20
    ) -> Optional[Prediction]:
        """Make prediction using LSTM model."""
        if self.lstm_model is None or not TORCH_AVAILABLE:
            return None
        
        try:
            # Get feature columns
            exclude_cols = ['Date', 'Symbol', 'Target', 'Future_Return', 'Open', 'High', 'Low', 'Close', 'Volume', 'Adj Close']
            feature_cols = [c for c in features.columns if c not in exclude_cols]
            
            # Need seq_length rows for LSTM
            if len(features) < seq_length:
                print(f"Not enough data for LSTM (need {seq_length}, have {len(features)})")
                return None
            
            # Get last seq_length rows
            X = features[feature_cols].iloc[-seq_length:].values
            
            # Scale if scaler available
            if self.feature_scaler is not None:
                X = self.feature_scaler.transform(X)
            
            # Convert to tensor
            X_tensor = torch.FloatTensor(X).unsqueeze(0)  # (1, seq_length, features)
            
            # Predict
            with torch.no_grad():
                output = self.lstm_model(X_tensor)
                proba = torch.softmax(output, dim=1).numpy()[0]
            
            prob_down, prob_up = proba[0], proba[1]
            
            if prob_up > 0.6:
                signal = "BUY"
            elif prob_down > 0.6:
                signal = "SELL"
            else:
                signal = "HOLD"
            
            confidence = max(prob_up, prob_down)
            
            return Prediction(
                symbol=symbol,
                signal=signal,
                confidence=confidence,
                probability_up=prob_up,
                probability_down=prob_down,
                model_type="lstm",
                model_version=self.lstm_metadata.get('version', 'v1'),
                timestamp=datetime.now(),
                features_used=len(feature_cols)
            )
            
        except Exception as e:
            print(f"Error in LSTM prediction: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def predict(
        self,
        df: pd.DataFrame,
        symbol: str,
        model_preference: str = "auto"
    ) -> Optional[Prediction]:
        """
        Make prediction using best available model.
        
        Args:
            df: DataFrame with OHLCV data
            symbol: Stock symbol
            model_preference: "rf", "lstm", or "auto" (tries LSTM first)
        
        Returns:
            Prediction object or None
        """
        # Prepare features
        features = self.prepare_features(df)
        
        if len(features) == 0:
            print(f"No valid features for {symbol}")
            return None
        
        # Choose model
        if model_preference == "lstm" and self.lstm_model is not None:
            return self.predict_lstm(features, symbol)
        elif model_preference == "rf" and self.rf_model is not None:
            return self.predict_rf(features, symbol)
        elif model_preference == "auto":
            # Try LSTM first, fall back to RF
            if self.lstm_model is not None:
                result = self.predict_lstm(features, symbol)
                if result:
                    return result
            if self.rf_model is not None:
                return self.predict_rf(features, symbol)
        
        return None
    
    def predict_batch(
        self,
        data: Dict[str, pd.DataFrame],
        model_preference: str = "auto"
    ) -> List[Prediction]:
        """
        Make predictions for multiple symbols.
        
        Args:
            data: Dict mapping symbol -> OHLCV DataFrame
            model_preference: Model preference
        
        Returns:
            List of Prediction objects
        """
        predictions = []
        
        for symbol, df in data.items():
            try:
                pred = self.predict(df, symbol, model_preference)
                if pred:
                    predictions.append(pred)
            except Exception as e:
                print(f"Error predicting {symbol}: {e}")
        
        return predictions
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about loaded models."""
        info = {
            "random_forest": None,
            "lstm": None
        }
        
        if self.rf_model is not None:
            info["random_forest"] = {
                "loaded": True,
                "metadata": self.rf_metadata
            }
        
        if self.lstm_model is not None:
            info["lstm"] = {
                "loaded": True,
                "metadata": self.lstm_metadata
            }
        
        return info


# Singleton instance for backend use
_service_instance: Optional[InferenceService] = None

def get_inference_service(models_dir: str = "models") -> InferenceService:
    """Get or create the inference service singleton."""
    global _service_instance
    
    if _service_instance is None:
        _service_instance = InferenceService(models_dir)
        _service_instance.load_all_models()
    
    return _service_instance


if __name__ == "__main__":
    # Test the inference service
    import yfinance as yf
    
    print("Testing Inference Service...")
    
    # Initialize service
    service = InferenceService(models_dir="models")
    
    # Try to load models
    results = service.load_all_models()
    print(f"Model loading results: {results}")
    
    # Download some test data
    print("\nDownloading test data...")
    test_symbols = ["AAPL", "MSFT"]
    
    for symbol in test_symbols:
        df = yf.download(symbol, period="3mo", progress=False)
        if len(df) > 0:
            pred = service.predict(df, symbol)
            if pred:
                print(f"\n{symbol} Prediction:")
                print(f"  Signal:     {pred.signal}")
                print(f"  Confidence: {pred.confidence:.2%}")
                print(f"  P(Up):      {pred.probability_up:.2%}")
                print(f"  P(Down):    {pred.probability_down:.2%}")
                print(f"  Model:      {pred.model_type}")
            else:
                print(f"\n{symbol}: No prediction available")
