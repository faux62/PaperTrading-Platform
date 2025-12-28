"""
ML Model Training from Database

Trains Random Forest model using historical data from PostgreSQL database.
Supports training on ALL symbols in the database.
"""
import os
import sys
import json
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
import logging
import argparse

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Scikit-learn
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    classification_report, confusion_matrix
)

# Feature engineering
from feature_engineering import calculate_technical_features

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Directories - use /app/models when in container, otherwise relative
if Path("/app/models").exists():
    MODEL_DIR = Path("/app/models")
else:
    MODEL_DIR = Path(__file__).parent.parent / "models"
    MODEL_DIR.mkdir(exist_ok=True)

# Database connection
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://papertrading_user:dev_password_123@localhost:5432/papertrading"
)


def load_data_from_db(min_bars: int = 500) -> pd.DataFrame:
    """
    Load historical price data from PostgreSQL database.
    
    Args:
        min_bars: Minimum number of bars required per symbol
        
    Returns:
        DataFrame with OHLCV data for all symbols
    """
    import psycopg2
    
    logger.info("Connecting to database...")
    conn = psycopg2.connect(DATABASE_URL)
    
    # Query to get symbols with enough data
    query = """
    WITH symbol_counts AS (
        SELECT symbol, COUNT(*) as bar_count
        FROM price_bars
        WHERE timeframe = 'D1'
        GROUP BY symbol
        HAVING COUNT(*) >= %s
    )
    SELECT pb.symbol, pb.timestamp, pb.open, pb.high, pb.low, pb.close, pb.volume
    FROM price_bars pb
    INNER JOIN symbol_counts sc ON pb.symbol = sc.symbol
    WHERE pb.timeframe = 'D1'
    ORDER BY pb.symbol, pb.timestamp
    """
    
    logger.info(f"Loading data (min {min_bars} bars per symbol)...")
    df = pd.read_sql(query, conn, params=(min_bars,))
    conn.close()
    
    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.rename(columns={'timestamp': 'date'})
    
    symbols = df['symbol'].nunique()
    logger.info(f"Loaded {len(df):,} bars for {symbols} symbols")
    
    return df


def prepare_features_for_symbol(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """
    Calculate technical features for a single symbol.
    
    Args:
        df: DataFrame with OHLCV data for one symbol
        
    Returns:
        DataFrame with features or None if insufficient data
    """
    try:
        if len(df) < 250:  # Need at least ~1 year for indicators
            return None
        
        # Calculate technical indicators
        df_features = calculate_technical_features(df)
        
        # Drop rows with NaN (initial periods for indicators)
        df_features = df_features.dropna()
        
        if len(df_features) < 100:
            return None
            
        return df_features
        
    except Exception as e:
        logger.warning(f"Error calculating features: {e}")
        return None


def create_labels(df: pd.DataFrame, horizon: int = 5, threshold: float = 0.02) -> pd.Series:
    """
    Create binary labels based on future returns.
    
    Args:
        df: DataFrame with 'close' column
        horizon: Number of days to look ahead
        threshold: Minimum return to be considered 'up'
        
    Returns:
        Series with binary labels (1 = up, 0 = not up)
    """
    future_return = df['close'].shift(-horizon) / df['close'] - 1
    labels = (future_return > threshold).astype(int)
    return labels


def prepare_training_data(
    df: pd.DataFrame,
    horizon: int = 5,
    threshold: float = 0.02
) -> Tuple[np.ndarray, np.ndarray, List[str], pd.DataFrame]:
    """
    Prepare training data from all symbols.
    
    Args:
        df: DataFrame with all symbols' OHLCV data
        horizon: Prediction horizon in days
        threshold: Return threshold for positive label
        
    Returns:
        X (features), y (labels), feature_names, full dataframe with features
    """
    all_features = []
    symbols_processed = 0
    symbols_skipped = 0
    
    symbols = df['symbol'].unique()
    logger.info(f"Processing {len(symbols)} symbols...")
    
    for i, symbol in enumerate(symbols):
        if (i + 1) % 50 == 0:
            logger.info(f"  Processing symbol {i+1}/{len(symbols)}...")
        
        symbol_df = df[df['symbol'] == symbol].copy()
        symbol_df = symbol_df.set_index('date').sort_index()
        
        # Calculate features
        features_df = prepare_features_for_symbol(symbol_df)
        
        if features_df is None:
            symbols_skipped += 1
            continue
        
        # Create labels
        features_df['label'] = create_labels(features_df, horizon, threshold)
        
        # Drop rows where we can't compute future return
        features_df = features_df.dropna(subset=['label'])
        
        if len(features_df) < 50:
            symbols_skipped += 1
            continue
        
        features_df['symbol'] = symbol
        all_features.append(features_df)
        symbols_processed += 1
    
    logger.info(f"Processed {symbols_processed} symbols, skipped {symbols_skipped}")
    
    if not all_features:
        raise ValueError("No valid data after feature engineering")
    
    # Combine all features
    combined = pd.concat(all_features, axis=0)
    
    # Select feature columns (exclude metadata)
    exclude_cols = ['symbol', 'label', 'open', 'high', 'low', 'close', 'volume', 
                    'dividends', 'stock_splits', 'date']
    feature_cols = [c for c in combined.columns if c not in exclude_cols and not c.startswith('_')]
    
    logger.info(f"Using {len(feature_cols)} features")
    
    X = combined[feature_cols].values
    y = combined['label'].values
    
    return X, y, feature_cols, combined


def train_model(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    feature_names: List[str]
) -> Tuple[RandomForestClassifier, StandardScaler, Dict[str, Any]]:
    """
    Train Random Forest classifier.
    
    Returns:
        model, scaler, metrics dict
    """
    logger.info("Scaling features...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    logger.info("Training Random Forest model...")
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=8,
        min_samples_split=100,
        min_samples_leaf=50,
        max_features='sqrt',
        n_jobs=-1,
        random_state=42,
        class_weight='balanced',
        bootstrap=True,
        oob_score=True
    )
    
    model.fit(X_train_scaled, y_train)
    
    # Predictions
    train_pred = model.predict(X_train_scaled)
    test_pred = model.predict(X_test_scaled)
    
    # Metrics
    metrics = {
        'train_accuracy': accuracy_score(y_train, train_pred),
        'test_accuracy': accuracy_score(y_test, test_pred),
        'oob_score': model.oob_score_,
        'precision': precision_score(y_test, test_pred, zero_division=0),
        'recall': recall_score(y_test, test_pred, zero_division=0),
        'f1': f1_score(y_test, test_pred, zero_division=0),
        'confusion_matrix': confusion_matrix(y_test, test_pred).tolist(),
        'classification_report': classification_report(y_test, test_pred)
    }
    
    # Feature importance
    importance = dict(zip(feature_names, model.feature_importances_))
    importance = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))
    metrics['feature_importance'] = importance
    
    return model, scaler, metrics


def save_model(
    model: RandomForestClassifier,
    scaler: StandardScaler,
    feature_names: List[str],
    metrics: Dict[str, Any],
    symbols_used: List[str],
    horizon: int,
    threshold: float
):
    """Save trained model and metadata."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save model
    model_path = MODEL_DIR / f"stock_predictor_rf_{timestamp}.pkl"
    with open(model_path, 'wb') as f:
        pickle.dump({
            'model': model,
            'scaler': scaler,
            'feature_names': feature_names
        }, f)
    
    # Save as 'latest' for easy loading
    latest_path = MODEL_DIR / "stock_predictor_rf_latest.pkl"
    with open(latest_path, 'wb') as f:
        pickle.dump({
            'model': model,
            'scaler': scaler,
            'feature_names': feature_names
        }, f)
    
    # Save metadata
    metadata = {
        'model_name': 'stock_predictor_random_forest',
        'model_type': 'RandomForestClassifier',
        'version': timestamp,
        'trained_at': datetime.now().isoformat(),
        'symbols_count': len(symbols_used),
        'symbols_used': symbols_used[:50],  # First 50 for reference
        'feature_count': len(feature_names),
        'feature_names': feature_names,
        'hyperparameters': {
            'n_estimators': 200,
            'max_depth': 8,
            'min_samples_split': 100,
            'min_samples_leaf': 50,
            'horizon_days': horizon,
            'return_threshold': threshold
        },
        'metrics': {
            'train_accuracy': metrics['train_accuracy'],
            'test_accuracy': metrics['test_accuracy'],
            'oob_score': metrics['oob_score'],
            'precision': metrics['precision'],
            'recall': metrics['recall'],
            'f1': metrics['f1']
        },
        'top_features': list(metrics['feature_importance'].items())[:20]
    }
    
    metadata_path = MODEL_DIR / f"stock_predictor_random_forest_metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    logger.info(f"Model saved to {model_path}")
    logger.info(f"Metadata saved to {metadata_path}")
    
    return model_path, metadata_path


def main():
    parser = argparse.ArgumentParser(description='Train ML model from database')
    parser.add_argument('--min-bars', type=int, default=500,
                        help='Minimum bars per symbol (default: 500)')
    parser.add_argument('--horizon', type=int, default=5,
                        help='Prediction horizon in days (default: 5)')
    parser.add_argument('--threshold', type=float, default=0.02,
                        help='Return threshold for positive label (default: 0.02)')
    parser.add_argument('--test-size', type=float, default=0.2,
                        help='Test set size (default: 0.2)')
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("ML MODEL TRAINING FROM DATABASE")
    logger.info("=" * 60)
    logger.info(f"Parameters:")
    logger.info(f"  - Min bars per symbol: {args.min_bars}")
    logger.info(f"  - Prediction horizon: {args.horizon} days")
    logger.info(f"  - Return threshold: {args.threshold:.1%}")
    logger.info(f"  - Test size: {args.test_size:.0%}")
    logger.info("=" * 60)
    
    # Load data from database
    df = load_data_from_db(min_bars=args.min_bars)
    
    # Prepare features
    X, y, feature_names, combined_df = prepare_training_data(
        df, horizon=args.horizon, threshold=args.threshold
    )
    
    logger.info(f"Total samples: {len(X):,}")
    logger.info(f"Label distribution: {np.mean(y):.1%} positive")
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=args.test_size, random_state=42, stratify=y
    )
    
    logger.info(f"Training samples: {len(X_train):,}")
    logger.info(f"Test samples: {len(X_test):,}")
    
    # Train model
    model, scaler, metrics = train_model(
        X_train, y_train, X_test, y_test, feature_names
    )
    
    # Results
    logger.info("=" * 60)
    logger.info("TRAINING RESULTS")
    logger.info("=" * 60)
    logger.info(f"Train Accuracy: {metrics['train_accuracy']:.2%}")
    logger.info(f"Test Accuracy:  {metrics['test_accuracy']:.2%}")
    logger.info(f"OOB Score:      {metrics['oob_score']:.2%}")
    logger.info(f"Precision:      {metrics['precision']:.2%}")
    logger.info(f"Recall:         {metrics['recall']:.2%}")
    logger.info(f"F1 Score:       {metrics['f1']:.2%}")
    logger.info("")
    logger.info("Top 10 Features:")
    for i, (feat, imp) in enumerate(list(metrics['feature_importance'].items())[:10]):
        logger.info(f"  {i+1}. {feat}: {imp:.4f}")
    
    # Save model
    symbols_used = df['symbol'].unique().tolist()
    model_path, metadata_path = save_model(
        model, scaler, feature_names, metrics, symbols_used,
        args.horizon, args.threshold
    )
    
    logger.info("=" * 60)
    logger.info("TRAINING COMPLETE")
    logger.info("=" * 60)
    
    return metrics


if __name__ == "__main__":
    main()
