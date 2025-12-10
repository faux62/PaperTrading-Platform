"""
ML Predictions Job

Scheduled job that automatically generates ML predictions and signals
for portfolio symbols, watchlist symbols, and popular stocks.
"""
import asyncio
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from loguru import logger
import numpy as np

from app.db.database import async_session_maker
from app.db.models import Portfolio, Position, Watchlist, User
from app.data_providers import orchestrator as market_orchestrator
from app.ml.inference import (
    get_inference_service,
    get_signal_generator,
    PredictionRequest,
    PredictionType,
    SignalType
)
from app.db.redis_client import redis_client
import json


@dataclass
class MLPrediction:
    """Stored ML prediction."""
    symbol: str
    signal_type: str
    confidence: float
    direction: int  # 1 = bullish, -1 = bearish, 0 = neutral
    price_target: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    predicted_change: float = 0.0
    model_version: str = "2.0.0"
    source: str = "ML Ensemble"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    valid_until: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(hours=24))
    
    def to_dict(self) -> dict:
        return {
            'symbol': self.symbol,
            'signal_type': self.signal_type,
            'confidence': self.confidence,
            'direction': self.direction,
            'price_target': self.price_target,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'predicted_change': self.predicted_change,
            'model_version': self.model_version,
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'valid_until': self.valid_until.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'MLPrediction':
        return cls(
            symbol=data['symbol'],
            signal_type=data['signal_type'],
            confidence=data['confidence'],
            direction=data['direction'],
            price_target=data.get('price_target'),
            stop_loss=data.get('stop_loss'),
            take_profit=data.get('take_profit'),
            predicted_change=data.get('predicted_change', 0.0),
            model_version=data.get('model_version', '2.0.0'),
            source=data.get('source', 'ML Ensemble'),
            timestamp=datetime.fromisoformat(data['timestamp']) if isinstance(data['timestamp'], str) else data['timestamp'],
            valid_until=datetime.fromisoformat(data['valid_until']) if isinstance(data.get('valid_until'), str) else datetime.utcnow() + timedelta(hours=24)
        )


class MLPredictionsJob:
    """
    Job that generates ML predictions for tracked symbols.
    
    Runs periodically to:
    1. Fetch symbols from portfolios and watchlists
    2. Get market data and compute features
    3. Generate ML predictions
    4. Store signals in Redis for API access
    """
    
    REDIS_KEY_PREFIX = "ml:predictions:"
    REDIS_ACTIVE_KEY = "ml:active_signals"
    POPULAR_SYMBOLS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM', 'V', 'WMT']
    
    def __init__(self):
        self.inference_service = get_inference_service()
        self.signal_generator = get_signal_generator()
        self.orchestrator = None
        self.redis_client = None
        self._last_run: Optional[datetime] = None
        self._running = False
    
    async def initialize(self):
        """Initialize services."""
        if self.orchestrator is None:
            self.orchestrator = market_orchestrator
        if self.redis_client is None:
            self.redis_client = redis_client.client
    
    async def get_tracked_symbols(self) -> Set[str]:
        """Get all symbols from portfolios and watchlists."""
        symbols = set()
        
        try:
            async with async_session_maker() as session:
                # Get all portfolio positions
                from sqlalchemy import select
                from sqlalchemy.orm import selectinload
                
                # Get portfolios with positions
                portfolios_query = select(Portfolio).options(selectinload(Portfolio.positions))
                result = await session.execute(portfolios_query)
                portfolios = result.scalars().all()
                
                for portfolio in portfolios:
                    for position in portfolio.positions:
                        if position.symbol and position.quantity > 0:
                            symbols.add(position.symbol)
                
                # Get watchlists
                watchlists_query = select(Watchlist)
                result = await session.execute(watchlists_query)
                watchlists = result.scalars().all()
                
                for watchlist in watchlists:
                    if watchlist.symbols:
                        for sym in watchlist.symbols:
                            symbols.add(sym)
                
        except Exception as e:
            logger.error(f"Error fetching tracked symbols: {e}")
        
        # Add popular symbols as fallback
        symbols.update(self.POPULAR_SYMBOLS)
        
        return symbols
    
    async def compute_features(self, symbol: str) -> Optional[np.ndarray]:
        """Compute ML features for a symbol."""
        try:
            if self.orchestrator is None:
                await self.initialize()
            
            # Get historical data
            from app.data_providers.adapters.base import TimeFrame
            from datetime import date, timedelta
            
            end_date = date.today()
            start_date = end_date - timedelta(days=365)  # 1 year of data
            
            history = await self.orchestrator.get_historical(
                symbol=symbol,
                timeframe=TimeFrame.DAY,
                start_date=start_date,
                end_date=end_date
            )
            
            if not history or len(history) < 20:
                logger.warning(f"Insufficient historical data for {symbol}: {len(history) if history else 0} bars")
                return None
            
            # Extract OHLCV data - convert Decimal to float
            prices = np.array([float(h.close) for h in history])
            highs = np.array([float(h.high) for h in history])
            lows = np.array([float(h.low) for h in history])
            volumes = np.array([float(h.volume) for h in history])
            
            # Compute features
            features = []
            
            # Price features
            returns = np.diff(prices) / prices[:-1]
            features.extend([
                returns[-1],  # Last return
                np.mean(returns[-5:]),  # 5-day avg return
                np.mean(returns[-20:]),  # 20-day avg return
                np.std(returns[-20:]),  # 20-day volatility
            ])
            
            # Momentum features (RSI-like)
            gains = np.where(returns > 0, returns, 0)
            losses = np.where(returns < 0, -returns, 0)
            avg_gain = np.mean(gains[-14:]) if len(gains) >= 14 else np.mean(gains)
            avg_loss = np.mean(losses[-14:]) if len(losses) >= 14 else np.mean(losses)
            rs = avg_gain / (avg_loss + 1e-10)
            rsi = 100 - (100 / (1 + rs))
            features.append(rsi / 100)  # Normalized RSI
            
            # Moving average features
            sma_20 = np.mean(prices[-20:])
            sma_50 = np.mean(prices[-50:]) if len(prices) >= 50 else np.mean(prices)
            sma_200 = np.mean(prices[-200:]) if len(prices) >= 200 else np.mean(prices)
            
            features.extend([
                (prices[-1] / sma_20) - 1,  # Price vs SMA20
                (prices[-1] / sma_50) - 1,  # Price vs SMA50
                (sma_20 / sma_50) - 1,  # SMA cross
            ])
            
            # Volume features
            avg_volume = np.mean(volumes[-20:])
            features.append(volumes[-1] / (avg_volume + 1e-10))  # Volume ratio
            
            # Bollinger band position
            bb_std = np.std(prices[-20:])
            bb_upper = sma_20 + 2 * bb_std
            bb_lower = sma_20 - 2 * bb_std
            bb_position = (prices[-1] - bb_lower) / (bb_upper - bb_lower + 1e-10)
            features.append(bb_position)
            
            # True range / ATR
            tr = np.maximum(
                highs[-20:] - lows[-20:],
                np.maximum(
                    np.abs(highs[-20:] - np.roll(prices[-20:], 1)),
                    np.abs(lows[-20:] - np.roll(prices[-20:], 1))
                )
            )
            atr = np.mean(tr)
            features.append(atr / prices[-1])  # ATR as % of price
            
            return np.array(features)
            
        except Exception as e:
            logger.error(f"Error computing features for {symbol}: {e}")
            return None
    
    async def generate_prediction(self, symbol: str, features: np.ndarray, current_price: float) -> Optional[MLPrediction]:
        """Generate ML prediction for a symbol."""
        try:
            # Make prediction using inference service
            request = PredictionRequest(
                symbol=symbol,
                features=features,
                prediction_types=[
                    PredictionType.PRICE_DIRECTION,
                    PredictionType.TREND,
                    PredictionType.VOLATILITY,
                    PredictionType.RISK
                ],
                horizon=7
            )
            
            response = await self.inference_service.predict_async(request)
            
            # Extract prediction details
            predictions = response.predictions
            confidence = response.confidence
            
            # Determine signal type and direction
            direction = 0
            signal_type = 'hold'
            predicted_change = 0.0
            
            # Parse predictions
            price_pred = predictions.get('price_direction', {})
            trend_pred = predictions.get('trend', {})
            
            if isinstance(price_pred, dict):
                pred_direction = price_pred.get('predicted_direction', 0)
                pred_change = price_pred.get('predicted_change', 0)
                predicted_change = pred_change
                direction = 1 if pred_direction > 0 else (-1 if pred_direction < 0 else 0)
            
            # Map to signal type based on confidence and direction
            if confidence >= 0.8:
                signal_type = 'strong_buy' if direction > 0 else 'strong_sell' if direction < 0 else 'hold'
            elif confidence >= 0.65:
                signal_type = 'buy' if direction > 0 else 'sell' if direction < 0 else 'hold'
            elif confidence >= 0.55:
                signal_type = 'weak_buy' if direction > 0 else 'weak_sell' if direction < 0 else 'hold'
            else:
                signal_type = 'hold'
            
            # Calculate price targets
            price_target = None
            stop_loss = None
            take_profit = None
            
            if direction != 0:
                volatility = predictions.get('volatility', {}).get('predicted_volatility', 0.02)
                if isinstance(volatility, dict):
                    volatility = 0.02
                
                if direction > 0:  # Bullish
                    price_target = current_price * (1 + abs(predicted_change) if predicted_change else (1 + volatility * 2))
                    stop_loss = current_price * (1 - volatility * 1.5)
                    take_profit = current_price * (1 + volatility * 3)
                else:  # Bearish
                    price_target = current_price * (1 - abs(predicted_change) if predicted_change else (1 - volatility * 2))
                    stop_loss = current_price * (1 + volatility * 1.5)
                    take_profit = current_price * (1 - volatility * 3)
            
            return MLPrediction(
                symbol=symbol,
                signal_type=signal_type,
                confidence=confidence,
                direction=direction,
                price_target=price_target,
                stop_loss=stop_loss,
                take_profit=take_profit,
                predicted_change=predicted_change,
                model_version=response.model_versions.get('price_direction', '2.0.0'),
                source='ML Ensemble'
            )
            
        except Exception as e:
            logger.error(f"Error generating prediction for {symbol}: {e}")
            return None
    
    async def generate_fallback_prediction(self, symbol: str, current_price: float, features: np.ndarray) -> MLPrediction:
        """Generate a simple rule-based prediction as fallback."""
        try:
            # Extract key features
            last_return = features[0]
            avg_return_5d = features[1]
            avg_return_20d = features[2]
            volatility = features[3]
            rsi = features[4] * 100  # Denormalize
            price_vs_sma20 = features[5]
            volume_ratio = features[8]
            
            # Simple scoring system
            score = 0
            confidence = 0.5
            
            # Trend score
            if avg_return_5d > 0.01:
                score += 2
            elif avg_return_5d < -0.01:
                score -= 2
            
            # RSI score
            if rsi < 30:
                score += 2  # Oversold = bullish
                confidence += 0.1
            elif rsi > 70:
                score -= 2  # Overbought = bearish
                confidence += 0.1
            elif 40 < rsi < 60:
                confidence += 0.05
            
            # SMA position
            if price_vs_sma20 > 0.02:
                score += 1  # Above SMA = bullish
            elif price_vs_sma20 < -0.02:
                score -= 1  # Below SMA = bearish
            
            # Volume confirmation
            if volume_ratio > 1.5:
                confidence += 0.1
                if score > 0:
                    score += 1
                elif score < 0:
                    score -= 1
            
            # Determine signal
            direction = 1 if score > 0 else (-1 if score < 0 else 0)
            abs_score = abs(score)
            
            if abs_score >= 4:
                signal_type = 'strong_buy' if direction > 0 else 'strong_sell'
                confidence = min(0.85, confidence + 0.2)
            elif abs_score >= 2:
                signal_type = 'buy' if direction > 0 else 'sell'
                confidence = min(0.75, confidence + 0.1)
            elif abs_score >= 1:
                signal_type = 'weak_buy' if direction > 0 else 'weak_sell'
            else:
                signal_type = 'hold'
                direction = 0
            
            # Price targets based on volatility
            predicted_change = avg_return_5d * 2 if direction != 0 else 0
            
            price_target = None
            stop_loss = None
            take_profit = None
            
            if direction != 0:
                if direction > 0:
                    price_target = current_price * (1 + volatility * 2)
                    stop_loss = current_price * (1 - volatility * 1.5)
                    take_profit = current_price * (1 + volatility * 3)
                else:
                    price_target = current_price * (1 - volatility * 2)
                    stop_loss = current_price * (1 + volatility * 1.5)
                    take_profit = current_price * (1 - volatility * 3)
            
            return MLPrediction(
                symbol=symbol,
                signal_type=signal_type,
                confidence=confidence,
                direction=direction,
                price_target=price_target,
                stop_loss=stop_loss,
                take_profit=take_profit,
                predicted_change=predicted_change,
                model_version='rules-1.0.0',
                source='Technical Analysis'
            )
            
        except Exception as e:
            logger.error(f"Error in fallback prediction for {symbol}: {e}")
            return MLPrediction(
                symbol=symbol,
                signal_type='hold',
                confidence=0.5,
                direction=0,
                source='Default'
            )
    
    async def store_prediction(self, prediction: MLPrediction):
        """Store prediction in Redis."""
        try:
            if self.redis_client is None:
                await self.initialize()
            
            # Store individual prediction
            key = f"{self.REDIS_KEY_PREFIX}{prediction.symbol}"
            await self.redis_client.set(
                key,
                json.dumps(prediction.to_dict()),
                ex=86400  # 24 hour TTL
            )
            
            # Add to active signals set
            active_data = {
                'symbol': prediction.symbol,
                'signal_type': prediction.signal_type,
                'confidence': prediction.confidence,
                'direction': prediction.direction,
                'timestamp': prediction.timestamp.isoformat()
            }
            
            # Get current active signals
            active_signals_raw = await self.redis_client.get(self.REDIS_ACTIVE_KEY)
            if active_signals_raw:
                active_signals = json.loads(active_signals_raw)
            else:
                active_signals = []
            
            # Update or add signal
            updated = False
            for i, sig in enumerate(active_signals):
                if sig['symbol'] == prediction.symbol:
                    active_signals[i] = active_data
                    updated = True
                    break
            
            if not updated:
                active_signals.append(active_data)
            
            # Keep only recent signals (last 50)
            active_signals = sorted(active_signals, key=lambda x: x['timestamp'], reverse=True)[:50]
            
            await self.redis_client.set(
                self.REDIS_ACTIVE_KEY,
                json.dumps(active_signals),
                ex=86400
            )
            
            logger.debug(f"Stored prediction for {prediction.symbol}: {prediction.signal_type}")
            
        except Exception as e:
            logger.error(f"Error storing prediction for {prediction.symbol}: {e}")
    
    async def run(self, force: bool = False) -> Dict[str, Any]:
        """
        Run the ML predictions job.
        
        Args:
            force: Run even if recently executed
            
        Returns:
            Summary of job execution
        """
        if self._running:
            return {'status': 'skipped', 'reason': 'Job already running'}
        
        # Check if we ran recently (within 15 minutes)
        if not force and self._last_run:
            since_last = datetime.utcnow() - self._last_run
            if since_last < timedelta(minutes=15):
                return {
                    'status': 'skipped',
                    'reason': f'Ran {since_last.seconds // 60} minutes ago'
                }
        
        self._running = True
        start_time = datetime.utcnow()
        results = {
            'status': 'completed',
            'started_at': start_time.isoformat(),
            'symbols_processed': 0,
            'predictions_generated': 0,
            'errors': []
        }
        
        try:
            await self.initialize()
            
            # Get symbols to analyze
            symbols = await self.get_tracked_symbols()
            logger.info(f"ML Predictions Job: Processing {len(symbols)} symbols")
            
            # Process each symbol
            for symbol in symbols:
                try:
                    # Get current price
                    quote = await self.orchestrator.get_quote(symbol)
                    if not quote:
                        logger.warning(f"No quote for {symbol}, skipping")
                        continue
                    
                    current_price = quote.price
                    results['symbols_processed'] += 1
                    
                    # Compute features
                    features = await self.compute_features(symbol)
                    if features is None:
                        # Use fallback prediction
                        prediction = await self.generate_fallback_prediction(
                            symbol, current_price, 
                            np.zeros(11)  # Default features
                        )
                    else:
                        # Try ML prediction, fallback to rules-based
                        prediction = await self.generate_prediction(symbol, features, current_price)
                        
                        # If ML prediction failed or returned default (no actual predictions),
                        # use rules-based fallback with computed features
                        if prediction is None or (prediction.source == 'ML Ensemble' and prediction.confidence == 0.5 and prediction.direction == 0):
                            prediction = await self.generate_fallback_prediction(
                                symbol, current_price, features
                            )
                    
                    # Store prediction
                    await self.store_prediction(prediction)
                    results['predictions_generated'] += 1
                    
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    error_msg = f"Error processing {symbol}: {str(e)}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
            
            self._last_run = datetime.utcnow()
            results['completed_at'] = self._last_run.isoformat()
            results['duration_seconds'] = (self._last_run - start_time).total_seconds()
            
            logger.info(
                f"ML Predictions Job completed: {results['predictions_generated']} predictions "
                f"for {results['symbols_processed']} symbols in {results['duration_seconds']:.1f}s"
            )
            
        except Exception as e:
            results['status'] = 'failed'
            results['error'] = str(e)
            logger.error(f"ML Predictions Job failed: {e}")
        finally:
            self._running = False
        
        return results


# Singleton instance
_ml_predictions_job: Optional[MLPredictionsJob] = None


def get_ml_predictions_job() -> MLPredictionsJob:
    """Get the ML predictions job singleton."""
    global _ml_predictions_job
    if _ml_predictions_job is None:
        _ml_predictions_job = MLPredictionsJob()
    return _ml_predictions_job


async def run_ml_predictions_job(force: bool = False) -> Dict[str, Any]:
    """Convenience function to run the ML predictions job."""
    job = get_ml_predictions_job()
    return await job.run(force=force)
