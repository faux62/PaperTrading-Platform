"""
Data Collector for ML Training

Downloads historical market data and prepares it for training.
"""
import os
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Data directory
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def download_historical_data(
    symbols: List[str],
    years: int = 5,
    interval: str = "1d"
) -> Dict[str, pd.DataFrame]:
    """
    Download historical OHLCV data for multiple symbols.
    
    Args:
        symbols: List of stock symbols
        years: Number of years of historical data
        interval: Data interval (1d, 1h, etc.)
        
    Returns:
        Dictionary of symbol -> DataFrame
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=years * 365)
    
    data = {}
    
    for symbol in symbols:
        logger.info(f"Downloading {symbol}...")
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date, interval=interval)
            
            if df.empty:
                logger.warning(f"No data for {symbol}")
                continue
            
            # Clean column names
            df.columns = [c.lower().replace(' ', '_') for c in df.columns]
            
            # Ensure we have required columns
            required = ['open', 'high', 'low', 'close', 'volume']
            if not all(c in df.columns for c in required):
                logger.warning(f"Missing columns for {symbol}")
                continue
            
            # Remove timezone info for consistency
            df.index = df.index.tz_localize(None)
            
            # Add symbol column
            df['symbol'] = symbol
            
            data[symbol] = df
            logger.info(f"  {symbol}: {len(df)} rows ({df.index[0].date()} to {df.index[-1].date()})")
            
        except Exception as e:
            logger.error(f"Error downloading {symbol}: {e}")
    
    return data


def save_data(data: Dict[str, pd.DataFrame], filename: str = "historical_data.csv"):
    """Save all data to a single CSV file."""
    if not data:
        logger.error("No data to save")
        return
    
    # Combine all dataframes
    combined = pd.concat(data.values(), axis=0)
    combined = combined.reset_index()
    combined = combined.rename(columns={'index': 'date', 'Date': 'date'})
    
    filepath = DATA_DIR / filename
    combined.to_csv(filepath, index=False)
    logger.info(f"Saved {len(combined)} rows to {filepath}")
    
    return filepath


def load_data(filename: str = "historical_data.csv") -> pd.DataFrame:
    """Load data from CSV file."""
    filepath = DATA_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Data file not found: {filepath}")
    
    df = pd.read_csv(filepath, parse_dates=['date'])
    return df


def get_symbol_data(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Extract data for a single symbol."""
    return df[df['symbol'] == symbol].copy().set_index('date').sort_index()


# Default symbols for training
DEFAULT_SYMBOLS = [
    # Large cap tech
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA',
    # Finance
    'JPM', 'BAC', 'WFC', 'GS',
    # Consumer
    'WMT', 'KO', 'PEP', 'MCD', 'NKE',
    # Energy
    'XOM', 'CVX',
    # Healthcare
    'JNJ', 'PFE', 'UNH',
    # Industrial
    'BA', 'CAT', 'RTX',
    # Telecom/Utilities
    'VZ', 'T', 'NEE',
    # Semiconductors
    'QCOM', 'AMD', 'INTC',
    # Other
    'PM', 'DIS', 'HD'
]


if __name__ == "__main__":
    # Download data for default symbols
    print("=" * 60)
    print("ML Training Data Collector")
    print("=" * 60)
    
    data = download_historical_data(DEFAULT_SYMBOLS, years=5)
    
    if data:
        filepath = save_data(data)
        print(f"\n✅ Data saved to: {filepath}")
        print(f"   Symbols: {len(data)}")
        print(f"   Total rows: {sum(len(df) for df in data.values())}")
    else:
        print("❌ No data downloaded")
