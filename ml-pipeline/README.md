# ML Training Pipeline

Real machine learning models for stock price prediction.

## Overview

This pipeline trains actual ML models on historical stock data, rather than using rule-based heuristics. It supports:

- **Random Forest Classifier**: Fast, interpretable, good baseline (~65-75% accuracy)
- **LSTM Neural Network**: Deep learning for sequential data (requires more data/compute)

## Quick Start

### 1. Install Dependencies

```bash
cd ml-pipeline
pip install -r requirements.txt
```

### 2. Train Models

```bash
# Train Random Forest only (fast, ~5 min)
python src/run_training.py --model rf

# Train both RF and LSTM
python src/run_training.py --model both --epochs 30

# Custom symbols
python src/run_training.py --symbols AAPL MSFT GOOGL AMZN --model rf

# Use existing data (skip download)
python src/run_training.py --skip-download --model rf
```

### 3. Use in Production

Trained models are saved to `models/` directory:
- `random_forest_multi.pkl` - Random Forest model
- `random_forest_multi_metadata.json` - Model metadata
- `lstm_multi.pt` - LSTM model (if trained)
- `lstm_multi_metadata.json` - LSTM metadata

The backend automatically loads these models via `trained_service.py`.

## Pipeline Components

### 1. Data Collection (`data_collector.py`)
- Downloads historical OHLCV data from Yahoo Finance
- Default: 5 years of daily data
- Saves to `data/` directory as CSV

### 2. Feature Engineering (`feature_engineering.py`)
Calculates 40+ technical indicators:
- **Trend**: SMA, EMA (5, 10, 20, 50, 200 periods)
- **Momentum**: RSI, Stochastic, ROC, Williams %R
- **Volatility**: Bollinger Bands, ATR
- **Volume**: OBV, Volume SMA, Volume Ratio
- **MACD**: Line, Signal, Histogram

### 3. Model Training

#### Random Forest (`train_model.py`)
- Scikit-learn RandomForestClassifier
- 200 trees, max_depth=20
- Handles class imbalance
- Fast training (~1 min per symbol)

#### LSTM (`train_lstm.py`)
- PyTorch LSTM with 2 layers
- 128 hidden units, 0.2 dropout
- Sequence length: 20 days
- Requires GPU for fast training

### 4. Inference (`inference_service.py`)
- Loads trained models
- Calculates features on new data
- Returns predictions with confidence scores

## Training Configuration

```python
# Default parameters in run_training.py
--symbols    # Default: Portfolio stocks (VZ, CVX, PM, etc.)
--years 5    # Years of historical data
--horizon 5  # Prediction horizon (days)
--threshold 0.02  # 2% threshold for buy/sell
--epochs 30  # LSTM training epochs
```

## Model Performance

Expected metrics after training:
- **Random Forest**: 63-72% accuracy, 0.55-0.65 F1 score
- **LSTM**: 60-70% accuracy (requires more data)

Note: Stock prediction is inherently difficult. >60% accuracy is considered good.

## Directory Structure

```
ml-pipeline/
├── data/               # Historical data cache
│   ├── AAPL.csv
│   ├── MSFT.csv
│   └── ...
├── models/             # Trained models
│   ├── random_forest_multi.pkl
│   ├── random_forest_multi_metadata.json
│   └── ...
├── notebooks/          # Jupyter notebooks for analysis
├── src/
│   ├── __init__.py
│   ├── data_collector.py
│   ├── feature_engineering.py
│   ├── train_model.py
│   ├── train_lstm.py
│   ├── inference_service.py
│   └── run_training.py
├── requirements.txt
└── README.md
```

## Integration with Backend

The backend's `trained_service.py` automatically:
1. Looks for models in `ml-pipeline/models/`
2. Loads Random Forest if available
3. Falls back to rule-based analysis if no model

To use trained models:
1. Run training: `python src/run_training.py`
2. Restart backend
3. Models are automatically loaded

## Troubleshooting

### "No model found"
- Run training first: `python src/run_training.py`
- Check `models/` directory exists

### "Not enough data"
- Ensure yfinance can download data
- Check internet connection
- Try different symbols

### Low accuracy
- Stock prediction is hard; 60%+ is good
- Try more data: `--years 10`
- Adjust threshold: `--threshold 0.03`
