"""
ML Training Pipeline

This package contains the complete ML training pipeline for the PaperTrading platform:

- data_collector.py: Download historical market data from Yahoo Finance
- feature_engineering.py: Calculate 40+ technical indicators
- train_model.py: Train Random Forest classifier
- train_lstm.py: Train PyTorch LSTM model
- inference_service.py: Load and use trained models
- run_training.py: Main pipeline orchestrator

Usage:
    # From ml-pipeline directory
    python src/run_training.py --symbols AAPL MSFT GOOGL --model rf
    
    # Train both RF and LSTM
    python src/run_training.py --model both --epochs 50
    
    # Skip data download (use cached data)
    python src/run_training.py --skip-download
"""
from pathlib import Path

__version__ = "1.0.0"

# Package directory
PACKAGE_DIR = Path(__file__).parent
DATA_DIR = PACKAGE_DIR.parent / "data"
MODELS_DIR = PACKAGE_DIR.parent / "models"

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)
