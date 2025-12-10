"""
LSTM Model Training

Deep learning model for stock prediction using PyTorch.
"""
import os
import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass, asdict
import logging

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

# Local imports
from data_collector import load_data, get_symbol_data, DEFAULT_SYMBOLS
from feature_engineering import calculate_technical_features, create_labels

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Model directory
MODEL_DIR = Path(__file__).parent.parent / "models"
MODEL_DIR.mkdir(exist_ok=True)

# Device
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'mps' if torch.backends.mps.is_available() else 'cpu')
logger.info(f"Using device: {DEVICE}")


class LSTMPredictor(nn.Module):
    """LSTM model for stock price direction prediction."""
    
    def __init__(
        self,
        input_size: int,
        hidden_size: int = 128,
        num_layers: int = 2,
        dropout: float = 0.3,
        num_classes: int = 2
    ):
        super().__init__()
        
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        # LSTM layers
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=True
        )
        
        # Attention mechanism
        self.attention = nn.Sequential(
            nn.Linear(hidden_size * 2, hidden_size),
            nn.Tanh(),
            nn.Linear(hidden_size, 1),
            nn.Softmax(dim=1)
        )
        
        # Fully connected layers
        self.fc = nn.Sequential(
            nn.Linear(hidden_size * 2, hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size // 2, num_classes)
        )
        
    def forward(self, x):
        # x shape: (batch, seq_len, features)
        
        # LSTM
        lstm_out, _ = self.lstm(x)
        # lstm_out shape: (batch, seq_len, hidden_size * 2)
        
        # Attention
        attention_weights = self.attention(lstm_out)
        # attention_weights shape: (batch, seq_len, 1)
        
        # Weighted sum
        context = torch.sum(attention_weights * lstm_out, dim=1)
        # context shape: (batch, hidden_size * 2)
        
        # Classification
        output = self.fc(context)
        
        return output


def create_sequences(
    X: np.ndarray,
    y: np.ndarray,
    seq_length: int = 20
) -> Tuple[np.ndarray, np.ndarray]:
    """Create sequences for LSTM training."""
    X_seq = []
    y_seq = []
    
    for i in range(seq_length, len(X)):
        X_seq.append(X[i-seq_length:i])
        y_seq.append(y[i])
    
    return np.array(X_seq), np.array(y_seq)


class LSTMTrainer:
    """Trainer for LSTM model."""
    
    def __init__(
        self,
        input_size: int,
        hidden_size: int = 128,
        num_layers: int = 2,
        dropout: float = 0.3,
        seq_length: int = 20,
        learning_rate: float = 0.001
    ):
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout = dropout
        self.seq_length = seq_length
        self.learning_rate = learning_rate
        
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names: List[str] = []
        self.is_trained = False
        
    def _create_model(self) -> LSTMPredictor:
        """Create LSTM model."""
        return LSTMPredictor(
            input_size=self.input_size,
            hidden_size=self.hidden_size,
            num_layers=self.num_layers,
            dropout=self.dropout
        ).to(DEVICE)
    
    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        feature_names: List[str],
        epochs: int = 50,
        batch_size: int = 64,
        patience: int = 10
    ) -> Dict[str, Any]:
        """
        Train LSTM model.
        
        Args:
            X_train: Training features (already sequenced)
            y_train: Training labels
            X_val: Validation features
            y_val: Validation labels
            feature_names: Feature names
            epochs: Number of training epochs
            batch_size: Batch size
            patience: Early stopping patience
            
        Returns:
            Training metrics
        """
        self.feature_names = feature_names
        
        # Scale features
        logger.info("Scaling features...")
        n_samples, seq_len, n_features = X_train.shape
        X_train_flat = X_train.reshape(-1, n_features)
        X_train_scaled = self.scaler.fit_transform(X_train_flat).reshape(n_samples, seq_len, n_features)
        
        n_samples_val = X_val.shape[0]
        X_val_flat = X_val.reshape(-1, n_features)
        X_val_scaled = self.scaler.transform(X_val_flat).reshape(n_samples_val, seq_len, n_features)
        
        # Convert to tensors
        X_train_tensor = torch.FloatTensor(X_train_scaled).to(DEVICE)
        y_train_tensor = torch.LongTensor(y_train).to(DEVICE)
        X_val_tensor = torch.FloatTensor(X_val_scaled).to(DEVICE)
        y_val_tensor = torch.LongTensor(y_val).to(DEVICE)
        
        # Create data loaders
        train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        
        # Create model
        self.model = self._create_model()
        
        # Loss and optimizer
        criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=self.learning_rate)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode='min', factor=0.5, patience=5
        )
        
        # Training loop
        best_val_loss = float('inf')
        best_val_acc = 0
        patience_counter = 0
        history = {'train_loss': [], 'val_loss': [], 'train_acc': [], 'val_acc': []}
        
        logger.info(f"Training LSTM for {epochs} epochs...")
        
        for epoch in range(epochs):
            # Training
            self.model.train()
            train_loss = 0
            train_correct = 0
            train_total = 0
            
            for batch_X, batch_y in train_loader:
                optimizer.zero_grad()
                outputs = self.model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                optimizer.step()
                
                train_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                train_total += batch_y.size(0)
                train_correct += (predicted == batch_y).sum().item()
            
            train_loss /= len(train_loader)
            train_acc = train_correct / train_total
            
            # Validation
            self.model.eval()
            with torch.no_grad():
                val_outputs = self.model(X_val_tensor)
                val_loss = criterion(val_outputs, y_val_tensor).item()
                _, val_predicted = torch.max(val_outputs.data, 1)
                val_acc = (val_predicted == y_val_tensor).sum().item() / len(y_val_tensor)
            
            # Update scheduler
            scheduler.step(val_loss)
            
            # Record history
            history['train_loss'].append(train_loss)
            history['val_loss'].append(val_loss)
            history['train_acc'].append(train_acc)
            history['val_acc'].append(val_acc)
            
            # Early stopping
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_val_acc = val_acc
                patience_counter = 0
                # Save best model
                best_model_state = self.model.state_dict().copy()
            else:
                patience_counter += 1
            
            if (epoch + 1) % 5 == 0 or epoch == 0:
                logger.info(
                    f"Epoch {epoch+1}/{epochs} - "
                    f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.4f}, "
                    f"Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.4f}"
                )
            
            if patience_counter >= patience:
                logger.info(f"Early stopping at epoch {epoch+1}")
                break
        
        # Load best model
        self.model.load_state_dict(best_model_state)
        self.is_trained = True
        
        logger.info(f"Best validation accuracy: {best_val_acc:.4f}")
        
        return {
            'history': history,
            'best_val_loss': best_val_loss,
            'best_val_acc': best_val_acc,
            'epochs_trained': len(history['train_loss'])
        }
    
    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, float]:
        """Evaluate model on test set."""
        if not self.is_trained:
            raise ValueError("Model not trained")
        
        # Scale
        n_samples, seq_len, n_features = X_test.shape
        X_test_flat = X_test.reshape(-1, n_features)
        X_test_scaled = self.scaler.transform(X_test_flat).reshape(n_samples, seq_len, n_features)
        
        # Convert to tensor
        X_test_tensor = torch.FloatTensor(X_test_scaled).to(DEVICE)
        
        # Predict
        self.model.eval()
        with torch.no_grad():
            outputs = self.model(X_test_tensor)
            _, predicted = torch.max(outputs.data, 1)
            y_pred = predicted.cpu().numpy()
        
        # Metrics
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, average='weighted', zero_division=0),
            'recall': recall_score(y_test, y_pred, average='weighted', zero_division=0),
            'f1': f1_score(y_test, y_pred, average='weighted', zero_division=0)
        }
        
        return metrics
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions."""
        if not self.is_trained:
            raise ValueError("Model not trained")
        
        # Scale
        if X.ndim == 2:
            X = X.reshape(1, X.shape[0], X.shape[1])
        
        n_samples, seq_len, n_features = X.shape
        X_flat = X.reshape(-1, n_features)
        X_scaled = self.scaler.transform(X_flat).reshape(n_samples, seq_len, n_features)
        
        # Convert to tensor
        X_tensor = torch.FloatTensor(X_scaled).to(DEVICE)
        
        # Predict
        self.model.eval()
        with torch.no_grad():
            outputs = self.model(X_tensor)
            _, predicted = torch.max(outputs.data, 1)
        
        return predicted.cpu().numpy()
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Get prediction probabilities."""
        if not self.is_trained:
            raise ValueError("Model not trained")
        
        # Scale
        if X.ndim == 2:
            X = X.reshape(1, X.shape[0], X.shape[1])
        
        n_samples, seq_len, n_features = X.shape
        X_flat = X.reshape(-1, n_features)
        X_scaled = self.scaler.transform(X_flat).reshape(n_samples, seq_len, n_features)
        
        # Convert to tensor
        X_tensor = torch.FloatTensor(X_scaled).to(DEVICE)
        
        # Predict
        self.model.eval()
        with torch.no_grad():
            outputs = self.model(X_tensor)
            proba = torch.softmax(outputs, dim=1)
        
        return proba.cpu().numpy()
    
    def save(self, name: str):
        """Save model."""
        model_path = MODEL_DIR / f"{name}_lstm.pt"
        scaler_path = MODEL_DIR / f"{name}_lstm_scaler.pkl"
        config_path = MODEL_DIR / f"{name}_lstm_config.json"
        
        # Save model state
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'input_size': self.input_size,
            'hidden_size': self.hidden_size,
            'num_layers': self.num_layers,
            'dropout': self.dropout,
            'feature_names': self.feature_names
        }, model_path)
        
        # Save scaler
        import pickle
        with open(scaler_path, 'wb') as f:
            pickle.dump(self.scaler, f)
        
        # Save config
        config = {
            'input_size': self.input_size,
            'hidden_size': self.hidden_size,
            'num_layers': self.num_layers,
            'dropout': self.dropout,
            'seq_length': self.seq_length,
            'feature_names': self.feature_names,
            'trained_at': datetime.now().isoformat()
        }
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"LSTM model saved to {model_path}")
    
    def load(self, name: str):
        """Load model."""
        model_path = MODEL_DIR / f"{name}_lstm.pt"
        scaler_path = MODEL_DIR / f"{name}_lstm_scaler.pkl"
        
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")
        
        # Load model state
        checkpoint = torch.load(model_path, map_location=DEVICE)
        
        self.input_size = checkpoint['input_size']
        self.hidden_size = checkpoint['hidden_size']
        self.num_layers = checkpoint['num_layers']
        self.dropout = checkpoint['dropout']
        self.feature_names = checkpoint['feature_names']
        
        self.model = self._create_model()
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model.eval()
        
        # Load scaler
        import pickle
        with open(scaler_path, 'rb') as f:
            self.scaler = pickle.load(f)
        
        self.is_trained = True
        logger.info(f"LSTM model loaded from {model_path}")


def train_lstm_model(
    symbols: List[str] = None,
    seq_length: int = 20,
    horizon: int = 5,
    threshold: float = 0.02,
    epochs: int = 50,
    batch_size: int = 64
) -> Tuple[LSTMTrainer, Dict[str, Any]]:
    """
    Train LSTM model on multiple symbols.
    """
    if symbols is None:
        symbols = DEFAULT_SYMBOLS[:10]  # Use fewer symbols for faster training
    
    logger.info(f"Training LSTM model on {len(symbols)} symbols")
    logger.info(f"Sequence length: {seq_length}, Horizon: {horizon} days")
    
    # Load data
    df = load_data()
    
    # Process each symbol
    all_X = []
    all_y = []
    
    for symbol in symbols:
        try:
            symbol_df = get_symbol_data(df, symbol)
            if len(symbol_df) < 500:
                logger.warning(f"Skipping {symbol}: insufficient data")
                continue
            
            # Calculate features
            df_features = calculate_technical_features(symbol_df)
            
            # Create labels
            df_labels = create_labels(df_features, horizon=horizon, threshold=threshold)
            
            # Drop NaN
            df_labels = df_labels.dropna()
            
            # Get features and labels
            exclude_cols = ['target', 'target_binary', 'future_return', 'symbol',
                          'open', 'high', 'low', 'close', 'volume', 'dividends', 'stock_splits']
            feature_cols = [c for c in df_labels.columns if c not in exclude_cols]
            
            X = df_labels[feature_cols].values
            y = df_labels['target_binary'].values
            
            # Create sequences
            X_seq, y_seq = create_sequences(X, y, seq_length)
            
            all_X.append(X_seq)
            all_y.append(y_seq)
            
            logger.info(f"  {symbol}: {len(X_seq)} sequences")
            
        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}")
    
    if not all_X:
        raise ValueError("No data available for training")
    
    # Combine all data
    X_combined = np.concatenate(all_X, axis=0)
    y_combined = np.concatenate(all_y, axis=0)
    
    logger.info(f"Total sequences: {len(X_combined)}")
    
    # Time-based split
    n = len(X_combined)
    train_end = int(n * 0.7)
    val_end = int(n * 0.85)
    
    X_train = X_combined[:train_end]
    y_train = y_combined[:train_end]
    X_val = X_combined[train_end:val_end]
    y_val = y_combined[train_end:val_end]
    X_test = X_combined[val_end:]
    y_test = y_combined[val_end:]
    
    logger.info(f"Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")
    
    # Train model
    n_features = X_train.shape[2]
    trainer = LSTMTrainer(
        input_size=n_features,
        hidden_size=128,
        num_layers=2,
        dropout=0.3,
        seq_length=seq_length
    )
    
    train_results = trainer.train(
        X_train, y_train,
        X_val, y_val,
        feature_names=feature_cols,
        epochs=epochs,
        batch_size=batch_size
    )
    
    # Evaluate
    test_metrics = trainer.evaluate(X_test, y_test)
    logger.info(f"Test Accuracy: {test_metrics['accuracy']:.4f}")
    
    # Save model
    trainer.save("stock_predictor")
    
    return trainer, {
        'train_results': train_results,
        'test_metrics': test_metrics,
        'symbols': symbols
    }


if __name__ == "__main__":
    print("=" * 60)
    print("LSTM Model Training")
    print("=" * 60)
    
    try:
        trainer, results = train_lstm_model(
            symbols=DEFAULT_SYMBOLS[:15],  # Use 15 symbols
            seq_length=20,
            horizon=5,
            threshold=0.02,
            epochs=30,
            batch_size=64
        )
        
        print("\n" + "=" * 60)
        print("✅ LSTM Training Complete!")
        print("=" * 60)
        print(f"\n📊 Model Performance:")
        print(f"   Best Val Accuracy: {results['train_results']['best_val_acc']:.2%}")
        print(f"   Test Accuracy:     {results['test_metrics']['accuracy']:.2%}")
        print(f"   Test Precision:    {results['test_metrics']['precision']:.2%}")
        print(f"   Test Recall:       {results['test_metrics']['recall']:.2%}")
        print(f"   Test F1:           {results['test_metrics']['f1']:.2%}")
        print(f"\n📁 Model saved to: ml-pipeline/models/")
        
    except FileNotFoundError:
        print("\n❌ No data file found!")
        print("   Run data_collector.py first to download historical data.")
    except Exception as e:
        print(f"\n❌ Training failed: {e}")
        import traceback
        traceback.print_exc()
