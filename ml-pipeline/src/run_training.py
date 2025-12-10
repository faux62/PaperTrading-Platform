#!/usr/bin/env python3
"""
ML Training Pipeline

Complete pipeline to:
1. Download historical data
2. Generate technical features
3. Train ML models (Random Forest + LSTM)
4. Save trained models for production use
"""
import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from data_collector import download_historical_data, save_data, DEFAULT_SYMBOLS
from train_model import train_multi_symbol_model

# Try to import LSTM trainer (optional, requires PyTorch)
try:
    from train_lstm import train_lstm_model
    LSTM_AVAILABLE = True
except ImportError:
    LSTM_AVAILABLE = False
    print("⚠️  PyTorch not available - LSTM training disabled")


def main():
    parser = argparse.ArgumentParser(description="ML Training Pipeline")
    parser.add_argument(
        '--symbols', 
        nargs='+', 
        default=None,
        help='Symbols to train on (default: all)'
    )
    parser.add_argument(
        '--years', 
        type=int, 
        default=5,
        help='Years of historical data (default: 5)'
    )
    parser.add_argument(
        '--model', 
        choices=['rf', 'lstm', 'both'], 
        default='both',
        help='Model type to train (default: both)'
    )
    parser.add_argument(
        '--horizon', 
        type=int, 
        default=5,
        help='Prediction horizon in days (default: 5)'
    )
    parser.add_argument(
        '--threshold', 
        type=float, 
        default=0.02,
        help='Buy/sell threshold (default: 0.02 = 2%%)'
    )
    parser.add_argument(
        '--skip-download',
        action='store_true',
        help='Skip data download (use existing data)'
    )
    parser.add_argument(
        '--epochs',
        type=int,
        default=30,
        help='LSTM training epochs (default: 30)'
    )
    
    args = parser.parse_args()
    
    symbols = args.symbols or DEFAULT_SYMBOLS
    
    print("=" * 70)
    print("🚀 ML TRAINING PIPELINE")
    print("=" * 70)
    print(f"\n📋 Configuration:")
    print(f"   Symbols:    {len(symbols)} stocks")
    print(f"   Years:      {args.years}")
    print(f"   Horizon:    {args.horizon} days")
    print(f"   Threshold:  {args.threshold*100}%")
    print(f"   Models:     {args.model}")
    
    # Step 1: Download data
    if not args.skip_download:
        print("\n" + "=" * 70)
        print("📥 STEP 1: Downloading Historical Data")
        print("=" * 70)
        
        data = download_historical_data(symbols, years=args.years)
        
        if not data:
            print("❌ No data downloaded. Exiting.")
            sys.exit(1)
        
        save_data(data)
        print(f"✅ Downloaded data for {len(data)} symbols")
    else:
        print("\n⏭️  Skipping data download (using existing data)")
    
    # Step 2: Train Random Forest
    if args.model in ['rf', 'both']:
        print("\n" + "=" * 70)
        print("🌲 STEP 2: Training Random Forest Model")
        print("=" * 70)
        
        try:
            rf_predictor, rf_metrics = train_multi_symbol_model(
                symbols=symbols,
                model_type="random_forest",
                horizon=args.horizon,
                threshold=args.threshold
            )
            
            print(f"\n✅ Random Forest Training Complete!")
            print(f"   Train Accuracy:      {rf_metrics.train_accuracy:.2%}")
            print(f"   Validation Accuracy: {rf_metrics.val_accuracy:.2%}")
            print(f"   Test Accuracy:       {rf_metrics.test_accuracy:.2%}")
            print(f"   F1 Score:            {rf_metrics.f1:.2%}")
            
        except Exception as e:
            print(f"❌ Random Forest training failed: {e}")
            if args.model == 'rf':
                sys.exit(1)
    
    # Step 3: Train LSTM
    if args.model in ['lstm', 'both']:
        if not LSTM_AVAILABLE:
            print("\n⚠️  LSTM training skipped - PyTorch not installed")
            print("   To enable LSTM: pip install torch")
        else:
            print("\n" + "=" * 70)
            print("🧠 STEP 3: Training LSTM Model")
            print("=" * 70)
            
            try:
                lstm_trainer, lstm_results = train_lstm_model(
                    symbols=symbols[:15],  # Use fewer for LSTM
                    seq_length=20,
                    horizon=args.horizon,
                    threshold=args.threshold,
                    epochs=args.epochs,
                    batch_size=64
                )
                
                print(f"\n✅ LSTM Training Complete!")
                print(f"   Best Val Accuracy: {lstm_results['train_results']['best_val_acc']:.2%}")
                print(f"   Test Accuracy:     {lstm_results['test_metrics']['accuracy']:.2%}")
                print(f"   Test F1:           {lstm_results['test_metrics']['f1']:.2%}")
                
            except Exception as e:
                print(f"❌ LSTM training failed: {e}")
                import traceback
                traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 70)
    print("🎉 TRAINING PIPELINE COMPLETE!")
    print("=" * 70)
    print(f"\n📁 Models saved to: ml-pipeline/models/")
    print(f"\nTo use in production:")
    print(f"   1. Copy models to backend/ml_models/")
    print(f"   2. Update inference service to load trained models")
    print(f"   3. Restart backend")


if __name__ == "__main__":
    main()
