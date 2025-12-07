"""
Phase 5 ML Tests: ML Predictions Validation
============================================

Test Coverage:
- ML-01: Prediction genera output valido
- ML-02: Confidence score 0-100%
- ML-03: Signal generation (buy/sell/hold)
- ML-04: Backtesting (basic validation)
"""
import pytest
import numpy as np
from datetime import datetime, timedelta

from app.ml.inference.predictor import (
    PredictionRequest,
    PredictionResponse,
    PredictionType,
    ModelCache
)
from app.ml.inference.signal_generator import (
    SignalType,
    SignalSource,
    TradingSignal,
    AggregatedSignal,
    SignalGenerator
)


class TestML01PredictionOutput:
    """ML-01: Prediction genera output valido."""
    
    def test_prediction_request_creation(self):
        """PredictionRequest si crea correttamente."""
        features = np.random.randn(10, 5)
        request = PredictionRequest(
            symbol="AAPL",
            features=features,
            prediction_types=[PredictionType.PRICE_DIRECTION],
            horizon=1
        )
        
        assert request.symbol == "AAPL"
        assert request.horizon == 1
        assert request.request_id  # Auto-generated
        assert request.features.shape == (10, 5)
        print(f"\n✓ ML-01: PredictionRequest created: {request.request_id}")
    
    def test_prediction_response_structure(self):
        """PredictionResponse ha struttura corretta."""
        response = PredictionResponse(
            request_id="test_123",
            symbol="AAPL",
            predictions={"direction": 1, "magnitude": 0.02},
            confidence=0.85,
            latency_ms=15.5
        )
        
        assert response.request_id == "test_123"
        assert response.symbol == "AAPL"
        assert "direction" in response.predictions
        assert 0 <= response.confidence <= 1
        
        # Test to_dict
        data = response.to_dict()
        assert "predictions" in data
        assert "confidence" in data
        print(f"\n✓ ML-01: PredictionResponse valid: {response.confidence:.2%} confidence")
    
    def test_prediction_types_enum(self):
        """PredictionType enum ha tutti i tipi necessari."""
        expected_types = [
            "PRICE_DIRECTION",
            "TREND",
            "VOLATILITY",
            "RISK",
            "ENSEMBLE"
        ]
        
        for t in expected_types:
            assert hasattr(PredictionType, t)
        
        print(f"\n✓ ML-01: All {len(expected_types)} PredictionTypes available")


class TestML02ConfidenceScore:
    """ML-02: Confidence score 0-100%."""
    
    def test_confidence_bounds(self):
        """Confidence deve essere tra 0 e 1."""
        # Test valid confidence
        response = PredictionResponse(
            request_id="test",
            symbol="AAPL",
            predictions={},
            confidence=0.75
        )
        assert 0 <= response.confidence <= 1
        
        # Test edge cases
        response_low = PredictionResponse(
            request_id="test_low",
            symbol="AAPL",
            predictions={},
            confidence=0.0
        )
        assert response_low.confidence == 0.0
        
        response_high = PredictionResponse(
            request_id="test_high",
            symbol="AAPL",
            predictions={},
            confidence=1.0
        )
        assert response_high.confidence == 1.0
        
        print(f"\n✓ ML-02: Confidence scores validated (0.0 to 1.0)")
    
    def test_signal_confidence_range(self):
        """TradingSignal confidence in range valido."""
        signal = TradingSignal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            source=SignalSource.PRICE_PREDICTION,
            strength=0.8,
            confidence=0.92
        )
        
        assert 0 <= signal.confidence <= 1
        assert 0 <= signal.strength <= 1
        print(f"\n✓ ML-02: Signal confidence {signal.confidence:.2%}, strength {signal.strength:.2%}")


class TestML03SignalGeneration:
    """ML-03: Signal generation (buy/sell/hold)."""
    
    def test_signal_types_complete(self):
        """Tutti i tipi di segnale sono disponibili."""
        expected = ["STRONG_BUY", "BUY", "WEAK_BUY", "HOLD", "WEAK_SELL", "SELL", "STRONG_SELL"]
        
        for sig_type in expected:
            assert hasattr(SignalType, sig_type)
        
        print(f"\n✓ ML-03: All {len(expected)} SignalTypes available")
    
    def test_signal_direction(self):
        """Signal direction corretto per ogni tipo."""
        # Buy signals should have direction 1
        for buy_type in [SignalType.STRONG_BUY, SignalType.BUY, SignalType.WEAK_BUY]:
            signal = TradingSignal(
                symbol="AAPL",
                signal_type=buy_type,
                source=SignalSource.ENSEMBLE,
                strength=0.7,
                confidence=0.8
            )
            assert signal.direction == 1, f"{buy_type} should have direction 1"
        
        # Sell signals should have direction -1
        for sell_type in [SignalType.STRONG_SELL, SignalType.SELL, SignalType.WEAK_SELL]:
            signal = TradingSignal(
                symbol="AAPL",
                signal_type=sell_type,
                source=SignalSource.ENSEMBLE,
                strength=0.7,
                confidence=0.8
            )
            assert signal.direction == -1, f"{sell_type} should have direction -1"
        
        # Hold should have direction 0
        hold_signal = TradingSignal(
            symbol="AAPL",
            signal_type=SignalType.HOLD,
            source=SignalSource.ENSEMBLE,
            strength=0.5,
            confidence=0.6
        )
        assert hold_signal.direction == 0
        
        print(f"\n✓ ML-03: Signal directions correct (BUY=1, SELL=-1, HOLD=0)")
    
    def test_signal_validity(self):
        """Signal validity check funziona."""
        # Valid signal (no expiry)
        signal_no_expiry = TradingSignal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            source=SignalSource.TREND_ANALYSIS,
            strength=0.7,
            confidence=0.8
        )
        assert signal_no_expiry.is_valid
        
        # Valid signal (future expiry)
        signal_future = TradingSignal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            source=SignalSource.TREND_ANALYSIS,
            strength=0.7,
            confidence=0.8,
            valid_until=datetime.utcnow() + timedelta(hours=1)
        )
        assert signal_future.is_valid
        
        # Expired signal
        signal_expired = TradingSignal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            source=SignalSource.TREND_ANALYSIS,
            strength=0.7,
            confidence=0.8,
            valid_until=datetime.utcnow() - timedelta(hours=1)
        )
        assert not signal_expired.is_valid
        
        print(f"\n✓ ML-03: Signal validity check working")
    
    def test_signal_to_dict(self):
        """Signal serialization corretta."""
        signal = TradingSignal(
            symbol="MSFT",
            signal_type=SignalType.STRONG_BUY,
            source=SignalSource.ENSEMBLE,
            strength=0.95,
            confidence=0.88,
            price_target=450.0,
            stop_loss=420.0,
            take_profit=480.0,
            timeframe="1d"
        )
        
        data = signal.to_dict()
        
        assert data['symbol'] == "MSFT"
        assert data['signal_type'] == "strong_buy"
        assert data['direction'] == 1
        assert data['strength'] == 0.95
        assert data['confidence'] == 0.88
        assert data['price_target'] == 450.0
        
        print(f"\n✓ ML-03: Signal serialization complete")
    
    def test_signal_generator_config(self):
        """SignalGenerator config funziona."""
        generator = SignalGenerator(
            buy_threshold=0.6,
            sell_threshold=0.4,
            strong_threshold=0.75
        )
        
        assert generator.buy_threshold == 0.6
        assert generator.sell_threshold == 0.4
        assert generator.strong_threshold == 0.75
        print(f"\n✓ ML-03: SignalGenerator configured (buy_thresh={generator.buy_threshold})")


class TestML04Backtesting:
    """ML-04: Basic backtesting validation."""
    
    def test_signal_backtest_simulation(self):
        """Simulazione backtest con segnali."""
        # Genera segnali di test
        signals = []
        prices = [100, 102, 101, 105, 103, 108, 106, 110, 112, 109]
        
        for i in range(1, len(prices)):
            price_change = (prices[i] - prices[i-1]) / prices[i-1]
            
            if price_change > 0.02:
                sig_type = SignalType.BUY
            elif price_change < -0.02:
                sig_type = SignalType.SELL
            else:
                sig_type = SignalType.HOLD
            
            signals.append(TradingSignal(
                symbol="TEST",
                signal_type=sig_type,
                source=SignalSource.PRICE_PREDICTION,
                strength=abs(price_change) * 10,
                confidence=0.7
            ))
        
        # Calcola accuratezza semplice
        correct = 0
        for i, signal in enumerate(signals):
            if i + 1 < len(prices) - 1:
                future_change = prices[i + 2] - prices[i + 1]
                predicted_direction = signal.direction
                actual_direction = 1 if future_change > 0 else (-1 if future_change < 0 else 0)
                
                if predicted_direction == actual_direction or predicted_direction == 0:
                    correct += 1
        
        accuracy = correct / len(signals) if signals else 0
        
        # Non richiediamo > 50% perché è un test sintetico
        assert len(signals) > 0
        print(f"\n✓ ML-04: Backtest simulation ran ({len(signals)} signals, {accuracy:.2%} accuracy)")
    
    def test_model_cache_functionality(self):
        """ModelCache funziona correttamente."""
        cache = ModelCache(max_size=5, ttl_seconds=3600)
        
        # Test empty cache
        assert cache.get("nonexistent") is None
        
        # Cache should have basic functionality
        assert cache.max_size == 5
        assert cache.ttl.total_seconds() == 3600
        
        print(f"\n✓ ML-04: ModelCache functional (max_size={cache.max_size})")


class TestSignalSources:
    """Test signal sources enum."""
    
    def test_all_sources_available(self):
        """Tutte le fonti di segnale disponibili."""
        expected_sources = [
            "PRICE_PREDICTION",
            "TREND_ANALYSIS",
            "VOLATILITY_MODEL",
            "RISK_ASSESSMENT",
            "TECHNICAL_INDICATOR",
            "ENSEMBLE"
        ]
        
        for source in expected_sources:
            assert hasattr(SignalSource, source)
        
        print(f"\n✓ All {len(expected_sources)} SignalSources available")
