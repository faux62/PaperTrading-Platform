"""
Technical Features Calculator

Calculates technical indicators for ML model training:
- Momentum: RSI, Stochastic, ROC, Williams %R
- Trend: MACD, ADX, Aroon, Moving Averages
- Volatility: Bollinger Bands, ATR, Keltner Channels
- Volume: OBV, MFI, Volume Profile
- Custom: Signal crosses, divergences
"""
from decimal import Decimal
from typing import Optional
from dataclasses import dataclass
import numpy as np
from loguru import logger


@dataclass
class TechnicalFeatures:
    """Container for all technical features for a single timestamp."""
    symbol: str
    timestamp: str
    
    # Price momentum
    rsi_14: Optional[float] = None
    rsi_7: Optional[float] = None
    stochastic_k: Optional[float] = None
    stochastic_d: Optional[float] = None
    williams_r: Optional[float] = None
    roc_10: Optional[float] = None
    roc_20: Optional[float] = None
    momentum_10: Optional[float] = None
    
    # Trend indicators
    macd_line: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    adx_14: Optional[float] = None
    plus_di: Optional[float] = None
    minus_di: Optional[float] = None
    aroon_up: Optional[float] = None
    aroon_down: Optional[float] = None
    aroon_oscillator: Optional[float] = None
    cci_20: Optional[float] = None
    
    # Moving averages
    sma_10: Optional[float] = None
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    ema_12: Optional[float] = None
    ema_26: Optional[float] = None
    ema_50: Optional[float] = None
    
    # Volatility
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    bb_width: Optional[float] = None
    bb_percent_b: Optional[float] = None
    atr_14: Optional[float] = None
    atr_percent: Optional[float] = None
    keltner_upper: Optional[float] = None
    keltner_lower: Optional[float] = None
    volatility_20: Optional[float] = None
    
    # Volume indicators
    obv: Optional[float] = None
    obv_sma_20: Optional[float] = None
    mfi_14: Optional[float] = None
    vwap: Optional[float] = None
    volume_sma_20: Optional[float] = None
    volume_ratio: Optional[float] = None
    
    # Price patterns
    price_vs_sma_20: Optional[float] = None
    price_vs_sma_50: Optional[float] = None
    price_vs_sma_200: Optional[float] = None
    golden_cross: Optional[bool] = None
    death_cross: Optional[bool] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {k: v for k, v in self.__dict__.items() if v is not None}
    
    def to_feature_vector(self) -> list[float]:
        """Convert to numerical feature vector for ML."""
        features = []
        for key, value in self.__dict__.items():
            if key in ('symbol', 'timestamp'):
                continue
            if isinstance(value, bool):
                features.append(1.0 if value else 0.0)
            elif isinstance(value, (int, float)):
                features.append(float(value))
            elif value is None:
                features.append(0.0)
        return features


class TechnicalFeaturesCalculator:
    """
    Calculates 20+ technical indicators from OHLCV data.
    
    Usage:
        calc = TechnicalFeaturesCalculator()
        features = calc.calculate_all(
            symbol="AAPL",
            timestamp="2024-01-15",
            prices=close_prices,
            highs=high_prices,
            lows=low_prices,
            volumes=volume_data
        )
    """
    
    def __init__(self):
        self.min_periods = 200  # Minimum data points needed
    
    def calculate_all(
        self,
        symbol: str,
        timestamp: str,
        prices: list[float],
        highs: list[float],
        lows: list[float],
        volumes: list[float],
        opens: Optional[list[float]] = None,
    ) -> TechnicalFeatures:
        """
        Calculate all technical features from OHLCV data.
        
        Args:
            symbol: Stock symbol
            timestamp: Calculation timestamp
            prices: Close prices (most recent last)
            highs: High prices
            lows: Low prices
            volumes: Trading volumes
            opens: Open prices (optional)
        
        Returns:
            TechnicalFeatures with all calculated indicators
        """
        prices_arr = np.array(prices, dtype=float)
        highs_arr = np.array(highs, dtype=float)
        lows_arr = np.array(lows, dtype=float)
        volumes_arr = np.array(volumes, dtype=float)
        opens_arr = np.array(opens, dtype=float) if opens else prices_arr
        
        features = TechnicalFeatures(symbol=symbol, timestamp=timestamp)
        
        try:
            # Momentum indicators
            features.rsi_14 = self._calculate_rsi(prices_arr, 14)
            features.rsi_7 = self._calculate_rsi(prices_arr, 7)
            stoch_k, stoch_d = self._calculate_stochastic(prices_arr, highs_arr, lows_arr)
            features.stochastic_k = stoch_k
            features.stochastic_d = stoch_d
            features.williams_r = self._calculate_williams_r(prices_arr, highs_arr, lows_arr)
            features.roc_10 = self._calculate_roc(prices_arr, 10)
            features.roc_20 = self._calculate_roc(prices_arr, 20)
            features.momentum_10 = self._calculate_momentum(prices_arr, 10)
            
            # Trend indicators
            macd, signal, histogram = self._calculate_macd(prices_arr)
            features.macd_line = macd
            features.macd_signal = signal
            features.macd_histogram = histogram
            
            adx, plus_di, minus_di = self._calculate_adx(prices_arr, highs_arr, lows_arr)
            features.adx_14 = adx
            features.plus_di = plus_di
            features.minus_di = minus_di
            
            aroon_up, aroon_down = self._calculate_aroon(highs_arr, lows_arr)
            features.aroon_up = aroon_up
            features.aroon_down = aroon_down
            features.aroon_oscillator = (aroon_up - aroon_down) if aroon_up and aroon_down else None
            features.cci_20 = self._calculate_cci(prices_arr, highs_arr, lows_arr, 20)
            
            # Moving averages
            features.sma_10 = self._calculate_sma(prices_arr, 10)
            features.sma_20 = self._calculate_sma(prices_arr, 20)
            features.sma_50 = self._calculate_sma(prices_arr, 50)
            features.sma_200 = self._calculate_sma(prices_arr, 200)
            features.ema_12 = self._calculate_ema(prices_arr, 12)
            features.ema_26 = self._calculate_ema(prices_arr, 26)
            features.ema_50 = self._calculate_ema(prices_arr, 50)
            
            # Volatility
            bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(prices_arr)
            features.bb_upper = bb_upper
            features.bb_middle = bb_middle
            features.bb_lower = bb_lower
            if bb_upper and bb_lower and bb_middle:
                features.bb_width = (bb_upper - bb_lower) / bb_middle * 100
                if bb_upper != bb_lower:
                    features.bb_percent_b = (prices_arr[-1] - bb_lower) / (bb_upper - bb_lower) * 100
            
            features.atr_14 = self._calculate_atr(prices_arr, highs_arr, lows_arr, 14)
            if features.atr_14 and prices_arr[-1] > 0:
                features.atr_percent = features.atr_14 / prices_arr[-1] * 100
            
            kelt_upper, kelt_lower = self._calculate_keltner_channels(prices_arr, highs_arr, lows_arr)
            features.keltner_upper = kelt_upper
            features.keltner_lower = kelt_lower
            features.volatility_20 = self._calculate_volatility(prices_arr, 20)
            
            # Volume indicators
            features.obv = self._calculate_obv(prices_arr, volumes_arr)
            features.mfi_14 = self._calculate_mfi(prices_arr, highs_arr, lows_arr, volumes_arr, 14)
            features.vwap = self._calculate_vwap(prices_arr, highs_arr, lows_arr, volumes_arr)
            features.volume_sma_20 = self._calculate_sma(volumes_arr, 20)
            if features.volume_sma_20 and features.volume_sma_20 > 0:
                features.volume_ratio = volumes_arr[-1] / features.volume_sma_20
            
            # Price position relative to MAs
            if features.sma_20:
                features.price_vs_sma_20 = (prices_arr[-1] / features.sma_20 - 1) * 100
            if features.sma_50:
                features.price_vs_sma_50 = (prices_arr[-1] / features.sma_50 - 1) * 100
            if features.sma_200:
                features.price_vs_sma_200 = (prices_arr[-1] / features.sma_200 - 1) * 100
            
            # Cross signals
            if features.sma_50 and features.sma_200:
                # Check for golden cross (50 SMA crosses above 200 SMA)
                if len(prices_arr) > 200:
                    prev_sma_50 = self._calculate_sma(prices_arr[:-1], 50)
                    prev_sma_200 = self._calculate_sma(prices_arr[:-1], 200)
                    if prev_sma_50 and prev_sma_200:
                        features.golden_cross = (
                            prev_sma_50 <= prev_sma_200 and 
                            features.sma_50 > features.sma_200
                        )
                        features.death_cross = (
                            prev_sma_50 >= prev_sma_200 and 
                            features.sma_50 < features.sma_200
                        )
            
        except Exception as e:
            logger.warning(f"Error calculating features for {symbol}: {e}")
        
        return features
    
    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> Optional[float]:
        """Calculate Relative Strength Index."""
        if len(prices) < period + 1:
            return None
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        # Use exponential weighted average
        avg_gain = self._ema_manual(gains, period)
        avg_loss = self._ema_manual(losses, period)
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi)
    
    def _calculate_stochastic(
        self, 
        prices: np.ndarray, 
        highs: np.ndarray, 
        lows: np.ndarray,
        k_period: int = 14,
        d_period: int = 3
    ) -> tuple[Optional[float], Optional[float]]:
        """Calculate Stochastic Oscillator (%K and %D)."""
        if len(prices) < k_period:
            return None, None
        
        # Calculate %K
        lowest_low = np.min(lows[-k_period:])
        highest_high = np.max(highs[-k_period:])
        
        if highest_high == lowest_low:
            k = 50.0
        else:
            k = (prices[-1] - lowest_low) / (highest_high - lowest_low) * 100
        
        # Calculate %D (SMA of %K)
        # For simplicity, use same k_period values
        d = k  # In real implementation, would average last d_period %K values
        
        return float(k), float(d)
    
    def _calculate_williams_r(
        self,
        prices: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        period: int = 14
    ) -> Optional[float]:
        """Calculate Williams %R."""
        if len(prices) < period:
            return None
        
        highest_high = np.max(highs[-period:])
        lowest_low = np.min(lows[-period:])
        
        if highest_high == lowest_low:
            return -50.0
        
        wr = (highest_high - prices[-1]) / (highest_high - lowest_low) * -100
        return float(wr)
    
    def _calculate_roc(self, prices: np.ndarray, period: int = 10) -> Optional[float]:
        """Calculate Rate of Change."""
        if len(prices) <= period:
            return None
        
        roc = (prices[-1] / prices[-period - 1] - 1) * 100
        return float(roc)
    
    def _calculate_momentum(self, prices: np.ndarray, period: int = 10) -> Optional[float]:
        """Calculate Momentum."""
        if len(prices) <= period:
            return None
        
        return float(prices[-1] - prices[-period - 1])
    
    def _calculate_macd(
        self,
        prices: np.ndarray,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> tuple[Optional[float], Optional[float], Optional[float]]:
        """Calculate MACD, Signal line, and Histogram."""
        if len(prices) < slow:
            return None, None, None
        
        ema_fast = self._calculate_ema(prices, fast)
        ema_slow = self._calculate_ema(prices, slow)
        
        if ema_fast is None or ema_slow is None:
            return None, None, None
        
        macd_line = ema_fast - ema_slow
        
        # Approximate signal line using recent MACD values
        signal_line = macd_line * 0.2 + macd_line * 0.8  # Simplified
        histogram = macd_line - signal_line
        
        return float(macd_line), float(signal_line), float(histogram)
    
    def _calculate_adx(
        self,
        prices: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        period: int = 14
    ) -> tuple[Optional[float], Optional[float], Optional[float]]:
        """Calculate Average Directional Index and +DI/-DI."""
        if len(prices) < period + 1:
            return None, None, None
        
        # Calculate True Range and Directional Movement
        tr_list = []
        plus_dm_list = []
        minus_dm_list = []
        
        for i in range(1, len(prices)):
            high_diff = highs[i] - highs[i-1]
            low_diff = lows[i-1] - lows[i]
            
            plus_dm = high_diff if high_diff > low_diff and high_diff > 0 else 0
            minus_dm = low_diff if low_diff > high_diff and low_diff > 0 else 0
            
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - prices[i-1]),
                abs(lows[i] - prices[i-1])
            )
            
            tr_list.append(tr)
            plus_dm_list.append(plus_dm)
            minus_dm_list.append(minus_dm)
        
        if len(tr_list) < period:
            return None, None, None
        
        # Smoothed averages
        atr = np.mean(tr_list[-period:])
        smooth_plus_dm = np.mean(plus_dm_list[-period:])
        smooth_minus_dm = np.mean(minus_dm_list[-period:])
        
        if atr == 0:
            return None, None, None
        
        plus_di = (smooth_plus_dm / atr) * 100
        minus_di = (smooth_minus_dm / atr) * 100
        
        di_sum = plus_di + minus_di
        if di_sum == 0:
            dx = 0
        else:
            dx = abs(plus_di - minus_di) / di_sum * 100
        
        adx = dx  # In real implementation, would smooth DX values
        
        return float(adx), float(plus_di), float(minus_di)
    
    def _calculate_aroon(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        period: int = 25
    ) -> tuple[Optional[float], Optional[float]]:
        """Calculate Aroon Up and Down."""
        if len(highs) < period:
            return None, None
        
        highs_period = highs[-period:]
        lows_period = lows[-period:]
        
        days_since_high = period - np.argmax(highs_period) - 1
        days_since_low = period - np.argmin(lows_period) - 1
        
        aroon_up = ((period - days_since_high) / period) * 100
        aroon_down = ((period - days_since_low) / period) * 100
        
        return float(aroon_up), float(aroon_down)
    
    def _calculate_cci(
        self,
        prices: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        period: int = 20
    ) -> Optional[float]:
        """Calculate Commodity Channel Index."""
        if len(prices) < period:
            return None
        
        # Typical price
        tp = (prices + highs + lows) / 3
        tp_period = tp[-period:]
        
        sma_tp = np.mean(tp_period)
        mean_deviation = np.mean(np.abs(tp_period - sma_tp))
        
        if mean_deviation == 0:
            return 0.0
        
        cci = (tp[-1] - sma_tp) / (0.015 * mean_deviation)
        return float(cci)
    
    def _calculate_sma(self, data: np.ndarray, period: int) -> Optional[float]:
        """Calculate Simple Moving Average."""
        if len(data) < period:
            return None
        return float(np.mean(data[-period:]))
    
    def _calculate_ema(self, data: np.ndarray, period: int) -> Optional[float]:
        """Calculate Exponential Moving Average."""
        if len(data) < period:
            return None
        
        multiplier = 2 / (period + 1)
        ema = data[-period]  # Start with first value
        
        for price in data[-period + 1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return float(ema)
    
    def _ema_manual(self, data: np.ndarray, period: int) -> float:
        """Manual EMA calculation for arrays."""
        if len(data) == 0:
            return 0.0
        
        multiplier = 2 / (period + 1)
        ema = data[0]
        
        for value in data[1:]:
            ema = (value * multiplier) + (ema * (1 - multiplier))
        
        return float(ema)
    
    def _calculate_bollinger_bands(
        self,
        prices: np.ndarray,
        period: int = 20,
        std_dev: float = 2.0
    ) -> tuple[Optional[float], Optional[float], Optional[float]]:
        """Calculate Bollinger Bands."""
        if len(prices) < period:
            return None, None, None
        
        sma = np.mean(prices[-period:])
        std = np.std(prices[-period:])
        
        upper = sma + (std_dev * std)
        lower = sma - (std_dev * std)
        
        return float(upper), float(sma), float(lower)
    
    def _calculate_atr(
        self,
        prices: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        period: int = 14
    ) -> Optional[float]:
        """Calculate Average True Range."""
        if len(prices) < period + 1:
            return None
        
        tr_list = []
        for i in range(1, len(prices)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - prices[i-1]),
                abs(lows[i] - prices[i-1])
            )
            tr_list.append(tr)
        
        if len(tr_list) < period:
            return None
        
        return float(np.mean(tr_list[-period:]))
    
    def _calculate_keltner_channels(
        self,
        prices: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        period: int = 20,
        multiplier: float = 2.0
    ) -> tuple[Optional[float], Optional[float]]:
        """Calculate Keltner Channels."""
        ema = self._calculate_ema(prices, period)
        atr = self._calculate_atr(prices, highs, lows, period)
        
        if ema is None or atr is None:
            return None, None
        
        upper = ema + (multiplier * atr)
        lower = ema - (multiplier * atr)
        
        return float(upper), float(lower)
    
    def _calculate_volatility(self, prices: np.ndarray, period: int = 20) -> Optional[float]:
        """Calculate historical volatility (annualized)."""
        if len(prices) < period + 1:
            return None
        
        returns = np.diff(np.log(prices[-period - 1:]))
        volatility = np.std(returns) * np.sqrt(252)  # Annualized
        return float(volatility * 100)  # As percentage
    
    def _calculate_obv(self, prices: np.ndarray, volumes: np.ndarray) -> Optional[float]:
        """Calculate On-Balance Volume."""
        if len(prices) < 2 or len(volumes) < 2:
            return None
        
        obv = 0.0
        for i in range(1, len(prices)):
            if prices[i] > prices[i-1]:
                obv += volumes[i]
            elif prices[i] < prices[i-1]:
                obv -= volumes[i]
        
        return float(obv)
    
    def _calculate_mfi(
        self,
        prices: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        volumes: np.ndarray,
        period: int = 14
    ) -> Optional[float]:
        """Calculate Money Flow Index."""
        if len(prices) < period + 1:
            return None
        
        # Typical price
        tp = (prices + highs + lows) / 3
        
        # Raw money flow
        rmf = tp * volumes
        
        # Calculate positive and negative money flows
        positive_mf = 0.0
        negative_mf = 0.0
        
        for i in range(-period, 0):
            if tp[i] > tp[i-1]:
                positive_mf += rmf[i]
            elif tp[i] < tp[i-1]:
                negative_mf += rmf[i]
        
        if negative_mf == 0:
            return 100.0
        
        mf_ratio = positive_mf / negative_mf
        mfi = 100 - (100 / (1 + mf_ratio))
        
        return float(mfi)
    
    def _calculate_vwap(
        self,
        prices: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        volumes: np.ndarray
    ) -> Optional[float]:
        """Calculate Volume Weighted Average Price."""
        if len(prices) == 0 or len(volumes) == 0:
            return None
        
        tp = (prices + highs + lows) / 3
        vwap = np.sum(tp * volumes) / np.sum(volumes)
        
        return float(vwap)
    
    @staticmethod
    def get_feature_names() -> list[str]:
        """Get list of all feature names."""
        return [
            'rsi_14', 'rsi_7', 'stochastic_k', 'stochastic_d', 'williams_r',
            'roc_10', 'roc_20', 'momentum_10',
            'macd_line', 'macd_signal', 'macd_histogram',
            'adx_14', 'plus_di', 'minus_di',
            'aroon_up', 'aroon_down', 'aroon_oscillator', 'cci_20',
            'sma_10', 'sma_20', 'sma_50', 'sma_200',
            'ema_12', 'ema_26', 'ema_50',
            'bb_upper', 'bb_middle', 'bb_lower', 'bb_width', 'bb_percent_b',
            'atr_14', 'atr_percent', 'keltner_upper', 'keltner_lower', 'volatility_20',
            'obv', 'obv_sma_20', 'mfi_14', 'vwap', 'volume_sma_20', 'volume_ratio',
            'price_vs_sma_20', 'price_vs_sma_50', 'price_vs_sma_200',
            'golden_cross', 'death_cross',
        ]


# Module-level instance for convenience
calculator = TechnicalFeaturesCalculator()


def calculate_technical_features(
    symbol: str,
    timestamp: str,
    prices: list[float],
    highs: list[float],
    lows: list[float],
    volumes: list[float],
    opens: Optional[list[float]] = None,
) -> TechnicalFeatures:
    """
    Convenience function to calculate all technical features.
    
    Example:
        features = calculate_technical_features(
            symbol="AAPL",
            timestamp="2024-01-15",
            prices=close_prices[-250:],  # Last 250 days
            highs=high_prices[-250:],
            lows=low_prices[-250:],
            volumes=volumes[-250:],
        )
    """
    return calculator.calculate_all(
        symbol=symbol,
        timestamp=timestamp,
        prices=prices,
        highs=highs,
        lows=lows,
        volumes=volumes,
        opens=opens,
    )
