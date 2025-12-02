"""
Signal Generator

Generates trading signals from ML predictions:
- Buy/Sell/Hold signals
- Signal strength and confidence
- Multi-timeframe signals
- Signal aggregation
"""
import numpy as np
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import deque
from loguru import logger


class SignalType(str, Enum):
    """Type of trading signal."""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    WEAK_BUY = "weak_buy"
    HOLD = "hold"
    WEAK_SELL = "weak_sell"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


class SignalSource(str, Enum):
    """Source of the signal."""
    PRICE_PREDICTION = "price_prediction"
    TREND_ANALYSIS = "trend_analysis"
    VOLATILITY_MODEL = "volatility_model"
    RISK_ASSESSMENT = "risk_assessment"
    TECHNICAL_INDICATOR = "technical_indicator"
    ENSEMBLE = "ensemble"


@dataclass
class TradingSignal:
    """Individual trading signal."""
    symbol: str
    signal_type: SignalType
    source: SignalSource
    strength: float  # 0 to 1
    confidence: float  # 0 to 1
    price_target: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    timeframe: str = "1d"  # 1h, 4h, 1d, 1w
    valid_until: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if isinstance(self.signal_type, str):
            self.signal_type = SignalType(self.signal_type)
        if isinstance(self.source, str):
            self.source = SignalSource(self.source)
    
    @property
    def is_valid(self) -> bool:
        """Check if signal is still valid."""
        if self.valid_until is None:
            return True
        return datetime.utcnow() < self.valid_until
    
    @property
    def direction(self) -> int:
        """Get signal direction: 1=buy, -1=sell, 0=hold."""
        if self.signal_type in [SignalType.STRONG_BUY, SignalType.BUY, SignalType.WEAK_BUY]:
            return 1
        elif self.signal_type in [SignalType.STRONG_SELL, SignalType.SELL, SignalType.WEAK_SELL]:
            return -1
        return 0
    
    def to_dict(self) -> dict:
        return {
            'symbol': self.symbol,
            'signal_type': self.signal_type.value,
            'source': self.source.value,
            'strength': self.strength,
            'confidence': self.confidence,
            'price_target': self.price_target,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'timeframe': self.timeframe,
            'valid_until': self.valid_until.isoformat() if self.valid_until else None,
            'created_at': self.created_at.isoformat(),
            'direction': self.direction,
            'is_valid': self.is_valid,
            'metadata': self.metadata
        }


@dataclass
class AggregatedSignal:
    """Aggregated signal from multiple sources."""
    symbol: str
    consensus_signal: SignalType
    consensus_strength: float
    consensus_confidence: float
    individual_signals: List[TradingSignal]
    agreement_ratio: float  # How many signals agree
    recommended_action: str
    position_size_suggestion: float  # 0 to 1, percentage of available capital
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            'symbol': self.symbol,
            'consensus_signal': self.consensus_signal.value,
            'consensus_strength': self.consensus_strength,
            'consensus_confidence': self.consensus_confidence,
            'individual_signals': [s.to_dict() for s in self.individual_signals],
            'agreement_ratio': self.agreement_ratio,
            'recommended_action': self.recommended_action,
            'position_size_suggestion': self.position_size_suggestion,
            'created_at': self.created_at.isoformat()
        }


class SignalGenerator:
    """
    Generates trading signals from ML predictions and indicators.
    
    Features:
    - Multi-source signal generation
    - Signal aggregation
    - Risk-adjusted position sizing
    - Signal history tracking
    """
    
    def __init__(
        self,
        buy_threshold: float = 0.6,
        sell_threshold: float = 0.4,
        strong_threshold: float = 0.75,
        max_history: int = 100
    ):
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.strong_threshold = strong_threshold
        
        # Signal history per symbol
        self.signal_history: Dict[str, deque] = {}
        self.max_history = max_history
    
    def generate_signal_from_prediction(
        self,
        symbol: str,
        prediction: Dict[str, Any],
        current_price: float,
        source: SignalSource = SignalSource.PRICE_PREDICTION
    ) -> TradingSignal:
        """
        Generate signal from a single prediction.
        
        Args:
            symbol: Stock symbol
            prediction: Prediction dictionary
            current_price: Current price
            source: Source of the prediction
            
        Returns:
            TradingSignal
        """
        # Extract probability/confidence
        probability = self._extract_probability(prediction)
        confidence = prediction.get('confidence', 0.5)
        
        # Determine signal type
        signal_type = self._determine_signal_type(probability)
        
        # Calculate strength
        strength = abs(probability - 0.5) * 2  # Scale to 0-1
        
        # Calculate targets
        price_target, stop_loss, take_profit = self._calculate_targets(
            current_price, signal_type, strength, prediction
        )
        
        # Set validity
        valid_until = datetime.utcnow() + timedelta(days=1)
        
        signal = TradingSignal(
            symbol=symbol,
            signal_type=signal_type,
            source=source,
            strength=strength,
            confidence=confidence,
            price_target=price_target,
            stop_loss=stop_loss,
            take_profit=take_profit,
            valid_until=valid_until,
            metadata=prediction
        )
        
        # Store in history
        self._add_to_history(symbol, signal)
        
        return signal
    
    def generate_signals_from_ensemble(
        self,
        symbol: str,
        predictions: Dict[str, Any],
        current_price: float
    ) -> List[TradingSignal]:
        """
        Generate signals from ensemble predictions.
        
        Args:
            symbol: Stock symbol
            predictions: Dictionary of predictions by type
            current_price: Current price
            
        Returns:
            List of signals from each source
        """
        signals = []
        
        # Price direction signal
        if 'price_direction' in predictions:
            signal = self.generate_signal_from_prediction(
                symbol,
                predictions['price_direction'],
                current_price,
                SignalSource.PRICE_PREDICTION
            )
            signals.append(signal)
        
        # Trend signal
        if 'trend' in predictions:
            signal = self.generate_signal_from_prediction(
                symbol,
                predictions['trend'],
                current_price,
                SignalSource.TREND_ANALYSIS
            )
            signals.append(signal)
        
        # Volatility signal
        if 'volatility' in predictions:
            vol_pred = predictions['volatility']
            # High volatility suggests caution
            signal = self._generate_volatility_signal(symbol, vol_pred, current_price)
            if signal:
                signals.append(signal)
        
        # Risk signal
        if 'risk' in predictions:
            risk_pred = predictions['risk']
            signal = self._generate_risk_signal(symbol, risk_pred, current_price)
            if signal:
                signals.append(signal)
        
        return signals
    
    def aggregate_signals(
        self,
        signals: List[TradingSignal]
    ) -> AggregatedSignal:
        """
        Aggregate multiple signals into a consensus.
        
        Args:
            signals: List of individual signals
            
        Returns:
            AggregatedSignal with consensus
        """
        if not signals:
            return AggregatedSignal(
                symbol="",
                consensus_signal=SignalType.HOLD,
                consensus_strength=0.0,
                consensus_confidence=0.0,
                individual_signals=[],
                agreement_ratio=0.0,
                recommended_action="No signals available",
                position_size_suggestion=0.0
            )
        
        symbol = signals[0].symbol
        
        # Calculate weighted scores
        buy_score = 0.0
        sell_score = 0.0
        total_weight = 0.0
        
        for signal in signals:
            weight = signal.confidence * signal.strength
            total_weight += weight
            
            if signal.direction > 0:
                buy_score += weight * signal.strength
            elif signal.direction < 0:
                sell_score += weight * signal.strength
        
        # Normalize
        if total_weight > 0:
            buy_score /= total_weight
            sell_score /= total_weight
        
        # Determine consensus
        net_score = buy_score - sell_score
        
        if net_score > 0.5:
            consensus_signal = SignalType.STRONG_BUY
        elif net_score > 0.25:
            consensus_signal = SignalType.BUY
        elif net_score > 0.1:
            consensus_signal = SignalType.WEAK_BUY
        elif net_score < -0.5:
            consensus_signal = SignalType.STRONG_SELL
        elif net_score < -0.25:
            consensus_signal = SignalType.SELL
        elif net_score < -0.1:
            consensus_signal = SignalType.WEAK_SELL
        else:
            consensus_signal = SignalType.HOLD
        
        # Calculate agreement
        directions = [s.direction for s in signals]
        if directions:
            main_direction = 1 if net_score > 0 else (-1 if net_score < 0 else 0)
            agreement = sum(1 for d in directions if d == main_direction) / len(directions)
        else:
            agreement = 0.0
        
        # Calculate confidence
        confidences = [s.confidence for s in signals]
        consensus_confidence = np.mean(confidences) if confidences else 0.0
        
        # Position size suggestion (based on confidence and agreement)
        position_size = min(agreement * consensus_confidence, 1.0)
        
        # Generate action recommendation
        action = self._generate_action_recommendation(
            consensus_signal, consensus_confidence, agreement
        )
        
        return AggregatedSignal(
            symbol=symbol,
            consensus_signal=consensus_signal,
            consensus_strength=abs(net_score),
            consensus_confidence=consensus_confidence,
            individual_signals=signals,
            agreement_ratio=agreement,
            recommended_action=action,
            position_size_suggestion=position_size
        )
    
    def _extract_probability(self, prediction: Dict[str, Any]) -> float:
        """Extract probability from prediction."""
        # Try different keys
        if 'probability_up' in prediction:
            return prediction['probability_up']
        if 'probability' in prediction:
            return prediction['probability']
        if 'confidence' in prediction:
            direction = prediction.get('direction', '')
            conf = prediction['confidence']
            if 'up' in str(direction).lower():
                return 0.5 + conf / 2
            elif 'down' in str(direction).lower():
                return 0.5 - conf / 2
            return 0.5
        if 'direction' in prediction:
            direction = str(prediction['direction']).lower()
            if 'up' in direction or 'bull' in direction:
                return 0.65
            elif 'down' in direction or 'bear' in direction:
                return 0.35
        return 0.5
    
    def _determine_signal_type(self, probability: float) -> SignalType:
        """Determine signal type from probability."""
        if probability >= self.strong_threshold:
            return SignalType.STRONG_BUY
        elif probability >= self.buy_threshold:
            return SignalType.BUY
        elif probability >= 0.55:
            return SignalType.WEAK_BUY
        elif probability <= 1 - self.strong_threshold:
            return SignalType.STRONG_SELL
        elif probability <= self.sell_threshold:
            return SignalType.SELL
        elif probability <= 0.45:
            return SignalType.WEAK_SELL
        else:
            return SignalType.HOLD
    
    def _calculate_targets(
        self,
        current_price: float,
        signal_type: SignalType,
        strength: float,
        prediction: Dict[str, Any]
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """Calculate price target, stop loss, and take profit."""
        # Base move percentage based on strength
        base_move = 0.02 + (strength * 0.03)  # 2-5%
        
        if signal_type in [SignalType.STRONG_BUY, SignalType.BUY, SignalType.WEAK_BUY]:
            price_target = current_price * (1 + base_move)
            stop_loss = current_price * (1 - base_move * 0.5)
            take_profit = current_price * (1 + base_move * 1.5)
        elif signal_type in [SignalType.STRONG_SELL, SignalType.SELL, SignalType.WEAK_SELL]:
            price_target = current_price * (1 - base_move)
            stop_loss = current_price * (1 + base_move * 0.5)
            take_profit = current_price * (1 - base_move * 1.5)
        else:
            price_target = current_price
            stop_loss = None
            take_profit = None
        
        # Round to 2 decimal places
        if price_target:
            price_target = round(price_target, 2)
        if stop_loss:
            stop_loss = round(stop_loss, 2)
        if take_profit:
            take_profit = round(take_profit, 2)
        
        return price_target, stop_loss, take_profit
    
    def _generate_volatility_signal(
        self,
        symbol: str,
        vol_pred: Dict[str, Any],
        current_price: float
    ) -> Optional[TradingSignal]:
        """Generate signal from volatility prediction."""
        regime = vol_pred.get('regime', '')
        forecast = vol_pred.get('forecast', 0)
        
        # High volatility = bearish signal (risk-off)
        if 'high' in str(regime).lower() or 'extreme' in str(regime).lower():
            return TradingSignal(
                symbol=symbol,
                signal_type=SignalType.WEAK_SELL,
                source=SignalSource.VOLATILITY_MODEL,
                strength=0.4,
                confidence=vol_pred.get('confidence', 0.5),
                metadata=vol_pred
            )
        elif 'low' in str(regime).lower():
            return TradingSignal(
                symbol=symbol,
                signal_type=SignalType.WEAK_BUY,
                source=SignalSource.VOLATILITY_MODEL,
                strength=0.3,
                confidence=vol_pred.get('confidence', 0.5),
                metadata=vol_pred
            )
        
        return None
    
    def _generate_risk_signal(
        self,
        symbol: str,
        risk_pred: Dict[str, Any],
        current_price: float
    ) -> Optional[TradingSignal]:
        """Generate signal from risk prediction."""
        risk_level = risk_pred.get('risk_level', '')
        risk_score = risk_pred.get('overall_score', 50)
        
        # High risk = bearish, Low risk = bullish
        if risk_score > 70 or 'high' in str(risk_level).lower() or 'extreme' in str(risk_level).lower():
            return TradingSignal(
                symbol=symbol,
                signal_type=SignalType.SELL if risk_score > 80 else SignalType.WEAK_SELL,
                source=SignalSource.RISK_ASSESSMENT,
                strength=min(risk_score / 100, 1.0),
                confidence=risk_pred.get('confidence', 0.5),
                metadata=risk_pred
            )
        elif risk_score < 30 or 'low' in str(risk_level).lower():
            return TradingSignal(
                symbol=symbol,
                signal_type=SignalType.WEAK_BUY,
                source=SignalSource.RISK_ASSESSMENT,
                strength=1 - (risk_score / 100),
                confidence=risk_pred.get('confidence', 0.5),
                metadata=risk_pred
            )
        
        return None
    
    def _generate_action_recommendation(
        self,
        signal_type: SignalType,
        confidence: float,
        agreement: float
    ) -> str:
        """Generate human-readable action recommendation."""
        if signal_type == SignalType.STRONG_BUY and agreement > 0.7:
            return f"Strong BUY signal with {agreement:.0%} model agreement. Consider entering long position."
        elif signal_type == SignalType.BUY:
            return f"BUY signal detected. {confidence:.0%} confidence, {agreement:.0%} agreement."
        elif signal_type == SignalType.WEAK_BUY:
            return f"Weak bullish bias. Monitor for confirmation before entering."
        elif signal_type == SignalType.STRONG_SELL and agreement > 0.7:
            return f"Strong SELL signal with {agreement:.0%} model agreement. Consider reducing exposure."
        elif signal_type == SignalType.SELL:
            return f"SELL signal detected. {confidence:.0%} confidence, {agreement:.0%} agreement."
        elif signal_type == SignalType.WEAK_SELL:
            return f"Weak bearish bias. Consider tightening stops."
        else:
            return "HOLD position. Mixed or neutral signals, no clear direction."
    
    def _add_to_history(self, symbol: str, signal: TradingSignal):
        """Add signal to history."""
        if symbol not in self.signal_history:
            self.signal_history[symbol] = deque(maxlen=self.max_history)
        self.signal_history[symbol].append(signal)
    
    def get_signal_history(
        self,
        symbol: str,
        limit: int = 10
    ) -> List[TradingSignal]:
        """Get recent signals for a symbol."""
        if symbol not in self.signal_history:
            return []
        return list(self.signal_history[symbol])[-limit:]
    
    def get_active_signals(
        self,
        symbol: Optional[str] = None
    ) -> List[TradingSignal]:
        """Get currently valid signals."""
        active = []
        
        symbols = [symbol] if symbol else self.signal_history.keys()
        
        for sym in symbols:
            if sym in self.signal_history:
                for signal in self.signal_history[sym]:
                    if signal.is_valid:
                        active.append(signal)
        
        return active
    
    def clear_history(self, symbol: Optional[str] = None):
        """Clear signal history."""
        if symbol:
            self.signal_history.pop(symbol, None)
        else:
            self.signal_history.clear()


# Global signal generator instance
_signal_generator: Optional[SignalGenerator] = None


def get_signal_generator() -> SignalGenerator:
    """Get or create global signal generator."""
    global _signal_generator
    if _signal_generator is None:
        _signal_generator = SignalGenerator()
    return _signal_generator
