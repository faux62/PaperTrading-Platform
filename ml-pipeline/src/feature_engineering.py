"""
Feature Engineering for ML Models

Calculates technical indicators and prepares features for training.
"""
import pandas as pd
import numpy as np
from typing import List, Tuple, Optional
import ta
from ta.trend import SMAIndicator, EMAIndicator, MACD, ADXIndicator, CCIIndicator
from ta.momentum import RSIIndicator, StochasticOscillator, WilliamsRIndicator, ROCIndicator
from ta.volatility import BollingerBands, AverageTrueRange, KeltnerChannel
from ta.volume import OnBalanceVolumeIndicator, VolumeWeightedAveragePrice, MFIIndicator
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calculate_technical_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate comprehensive technical indicators.
    
    Args:
        df: DataFrame with OHLCV data (columns: open, high, low, close, volume)
        
    Returns:
        DataFrame with original data plus technical features
    """
    df = df.copy()
    
    # Ensure we have the required columns
    required = ['open', 'high', 'low', 'close', 'volume']
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")
    
    high = df['high']
    low = df['low']
    close = df['close']
    volume = df['volume']
    
    # ==================== TREND INDICATORS ====================
    
    # Simple Moving Averages
    for period in [5, 10, 20, 50, 200]:
        sma = SMAIndicator(close, window=period)
        df[f'sma_{period}'] = sma.sma_indicator()
        df[f'close_sma_{period}_ratio'] = close / df[f'sma_{period}']
    
    # Exponential Moving Averages
    for period in [12, 26, 50]:
        ema = EMAIndicator(close, window=period)
        df[f'ema_{period}'] = ema.ema_indicator()
    
    # MACD
    macd = MACD(close)
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['macd_histogram'] = macd.macd_diff()
    
    # ADX (Average Directional Index)
    adx = ADXIndicator(high, low, close)
    df['adx'] = adx.adx()
    df['adx_pos'] = adx.adx_pos()
    df['adx_neg'] = adx.adx_neg()
    
    # CCI (Commodity Channel Index)
    cci = CCIIndicator(high, low, close)
    df['cci'] = cci.cci()
    
    # ==================== MOMENTUM INDICATORS ====================
    
    # RSI
    for period in [7, 14, 21]:
        rsi = RSIIndicator(close, window=period)
        df[f'rsi_{period}'] = rsi.rsi()
    
    # Stochastic Oscillator
    stoch = StochasticOscillator(high, low, close)
    df['stoch_k'] = stoch.stoch()
    df['stoch_d'] = stoch.stoch_signal()
    
    # Williams %R
    williams = WilliamsRIndicator(high, low, close)
    df['williams_r'] = williams.williams_r()
    
    # Rate of Change
    for period in [5, 10, 20]:
        roc = ROCIndicator(close, window=period)
        df[f'roc_{period}'] = roc.roc()
    
    # ==================== VOLATILITY INDICATORS ====================
    
    # Bollinger Bands
    bb = BollingerBands(close)
    df['bb_high'] = bb.bollinger_hband()
    df['bb_low'] = bb.bollinger_lband()
    df['bb_mid'] = bb.bollinger_mavg()
    df['bb_width'] = (df['bb_high'] - df['bb_low']) / df['bb_mid']
    df['bb_pct'] = (close - df['bb_low']) / (df['bb_high'] - df['bb_low'])
    
    # ATR (Average True Range)
    for period in [7, 14, 21]:
        atr = AverageTrueRange(high, low, close, window=period)
        df[f'atr_{period}'] = atr.average_true_range()
        df[f'atr_{period}_pct'] = df[f'atr_{period}'] / close * 100
    
    # Keltner Channel
    kc = KeltnerChannel(high, low, close)
    df['kc_high'] = kc.keltner_channel_hband()
    df['kc_low'] = kc.keltner_channel_lband()
    df['kc_mid'] = kc.keltner_channel_mband()
    
    # ==================== VOLUME INDICATORS ====================
    
    # On Balance Volume
    obv = OnBalanceVolumeIndicator(close, volume)
    df['obv'] = obv.on_balance_volume()
    
    # Money Flow Index
    mfi = MFIIndicator(high, low, close, volume)
    df['mfi'] = mfi.money_flow_index()
    
    # Volume SMA ratio
    df['volume_sma_20'] = volume.rolling(window=20).mean()
    df['volume_ratio'] = volume / df['volume_sma_20']
    
    # ==================== PRICE FEATURES ====================
    
    # Returns
    df['return_1d'] = close.pct_change(1)
    df['return_5d'] = close.pct_change(5)
    df['return_10d'] = close.pct_change(10)
    df['return_20d'] = close.pct_change(20)
    
    # Volatility (rolling std of returns)
    df['volatility_5d'] = df['return_1d'].rolling(window=5).std()
    df['volatility_20d'] = df['return_1d'].rolling(window=20).std()
    
    # High-Low range
    df['hl_range'] = (high - low) / close
    df['hl_range_avg'] = df['hl_range'].rolling(window=20).mean()
    
    # Gap
    df['gap'] = (df['open'] - close.shift(1)) / close.shift(1)
    
    # Intraday position
    df['intraday_position'] = (close - low) / (high - low + 1e-10)
    
    # Distance from 52-week high/low
    df['high_52w'] = high.rolling(window=252).max()
    df['low_52w'] = low.rolling(window=252).min()
    df['dist_from_high'] = (close - df['high_52w']) / df['high_52w']
    df['dist_from_low'] = (close - df['low_52w']) / df['low_52w']
    
    # ==================== TREND FEATURES ====================
    
    # Price above/below MAs
    df['above_sma_20'] = (close > df['sma_20']).astype(int)
    df['above_sma_50'] = (close > df['sma_50']).astype(int)
    df['above_sma_200'] = (close > df['sma_200']).astype(int)
    
    # Golden/Death cross signals
    df['sma_20_50_cross'] = (df['sma_20'] > df['sma_50']).astype(int)
    df['sma_50_200_cross'] = (df['sma_50'] > df['sma_200']).astype(int)
    
    return df


def create_labels(df: pd.DataFrame, horizon: int = 5, threshold: float = 0.02) -> pd.DataFrame:
    """
    Create target labels for classification.
    
    Args:
        df: DataFrame with close prices
        horizon: Number of days to look ahead
        threshold: Percentage threshold for buy/sell signals
        
    Returns:
        DataFrame with target labels
    """
    df = df.copy()
    
    # Future return
    df['future_return'] = df['close'].shift(-horizon) / df['close'] - 1
    
    # Classification labels
    # 0 = Sell (return < -threshold)
    # 1 = Hold (return between -threshold and +threshold)
    # 2 = Buy (return > threshold)
    df['target'] = 1  # Default to Hold
    df.loc[df['future_return'] > threshold, 'target'] = 2  # Buy
    df.loc[df['future_return'] < -threshold, 'target'] = 0  # Sell
    
    # Binary classification (simpler)
    # 1 = Price goes up, 0 = Price goes down
    df['target_binary'] = (df['future_return'] > 0).astype(int)
    
    return df


def prepare_training_data(
    df: pd.DataFrame,
    feature_columns: Optional[List[str]] = None,
    target_column: str = 'target_binary',
    test_size: float = 0.2,
    validation_size: float = 0.1
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, List[str]]:
    """
    Prepare data for training with train/val/test split.
    
    Uses time-based split (no shuffle) to prevent look-ahead bias.
    
    Returns:
        X_train, X_val, X_test, y_train, y_val, y_test, feature_names
    """
    df = df.copy()
    
    # Drop rows with NaN
    df = df.dropna()
    
    # Default feature columns (exclude target and non-feature columns)
    exclude_cols = ['target', 'target_binary', 'future_return', 'symbol', 
                    'open', 'high', 'low', 'close', 'volume', 'dividends', 'stock_splits']
    
    if feature_columns is None:
        feature_columns = [c for c in df.columns if c not in exclude_cols]
    
    # Extract features and target
    X = df[feature_columns].values
    y = df[target_column].values
    
    # Time-based split (chronological order)
    n = len(X)
    train_end = int(n * (1 - test_size - validation_size))
    val_end = int(n * (1 - test_size))
    
    X_train = X[:train_end]
    y_train = y[:train_end]
    
    X_val = X[train_end:val_end]
    y_val = y[train_end:val_end]
    
    X_test = X[val_end:]
    y_test = y[val_end:]
    
    logger.info(f"Data split: Train={len(X_train)}, Val={len(X_val)}, Test={len(X_test)}")
    
    return X_train, X_val, X_test, y_train, y_val, y_test, feature_columns


def get_feature_list() -> List[str]:
    """Get list of all feature names that will be generated."""
    # This should match the features calculated in calculate_technical_features
    features = []
    
    # SMAs and ratios
    for period in [5, 10, 20, 50, 200]:
        features.extend([f'sma_{period}', f'close_sma_{period}_ratio'])
    
    # EMAs
    for period in [12, 26, 50]:
        features.append(f'ema_{period}')
    
    # MACD
    features.extend(['macd', 'macd_signal', 'macd_histogram'])
    
    # ADX
    features.extend(['adx', 'adx_pos', 'adx_neg'])
    
    # CCI
    features.append('cci')
    
    # RSI
    for period in [7, 14, 21]:
        features.append(f'rsi_{period}')
    
    # Stochastic
    features.extend(['stoch_k', 'stoch_d'])
    
    # Williams %R
    features.append('williams_r')
    
    # ROC
    for period in [5, 10, 20]:
        features.append(f'roc_{period}')
    
    # Bollinger Bands
    features.extend(['bb_high', 'bb_low', 'bb_mid', 'bb_width', 'bb_pct'])
    
    # ATR
    for period in [7, 14, 21]:
        features.extend([f'atr_{period}', f'atr_{period}_pct'])
    
    # Keltner Channel
    features.extend(['kc_high', 'kc_low', 'kc_mid'])
    
    # Volume
    features.extend(['obv', 'mfi', 'volume_sma_20', 'volume_ratio'])
    
    # Returns and volatility
    features.extend(['return_1d', 'return_5d', 'return_10d', 'return_20d',
                     'volatility_5d', 'volatility_20d'])
    
    # Price features
    features.extend(['hl_range', 'hl_range_avg', 'gap', 'intraday_position',
                     'high_52w', 'low_52w', 'dist_from_high', 'dist_from_low'])
    
    # Trend features
    features.extend(['above_sma_20', 'above_sma_50', 'above_sma_200',
                     'sma_20_50_cross', 'sma_50_200_cross'])
    
    return features


if __name__ == "__main__":
    # Test feature engineering
    from data_collector import load_data, get_symbol_data
    
    print("=" * 60)
    print("Feature Engineering Test")
    print("=" * 60)
    
    try:
        df = load_data()
        symbol_df = get_symbol_data(df, 'AAPL')
        
        print(f"\nOriginal data shape: {symbol_df.shape}")
        
        # Calculate features
        df_features = calculate_technical_features(symbol_df)
        print(f"With features shape: {df_features.shape}")
        
        # Create labels
        df_labels = create_labels(df_features)
        print(f"With labels shape: {df_labels.shape}")
        
        # Show label distribution
        print(f"\nLabel distribution:")
        print(df_labels['target'].value_counts())
        print(f"\nBinary label distribution:")
        print(df_labels['target_binary'].value_counts())
        
        # Prepare training data
        X_train, X_val, X_test, y_train, y_val, y_test, features = prepare_training_data(df_labels)
        print(f"\nFeatures: {len(features)}")
        print(f"Train: {X_train.shape}, Val: {X_val.shape}, Test: {X_test.shape}")
        
    except FileNotFoundError:
        print("❌ No data file found. Run data_collector.py first.")
