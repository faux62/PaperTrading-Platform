"""
Backtesting Framework

Framework for testing ML models and trading strategies on historical data:
- Walk-forward backtesting
- Event-driven simulation
- Performance metrics calculation
- Transaction cost modeling
"""
import numpy as np
import pandas as pd
from typing import Optional, List, Dict, Any, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from abc import ABC, abstractmethod
from loguru import logger


class OrderSide(str, Enum):
    """Order side."""
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Order type."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


@dataclass
class Order:
    """Represents an order in the backtest."""
    symbol: str
    side: OrderSide
    quantity: float
    order_type: OrderType = OrderType.MARKET
    price: Optional[float] = None  # For limit orders
    stop_price: Optional[float] = None  # For stop orders
    timestamp: datetime = field(default_factory=datetime.utcnow)
    filled: bool = False
    fill_price: Optional[float] = None
    fill_timestamp: Optional[datetime] = None
    commission: float = 0.0
    slippage: float = 0.0


@dataclass
class Position:
    """Represents a position in the backtest."""
    symbol: str
    quantity: float
    entry_price: float
    entry_timestamp: datetime
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    
    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price
    
    @property
    def cost_basis(self) -> float:
        return self.quantity * self.entry_price


@dataclass
class Trade:
    """Represents an executed trade."""
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    timestamp: datetime
    commission: float = 0.0
    slippage: float = 0.0
    pnl: float = 0.0  # For closing trades


@dataclass
class BacktestConfig:
    """Backtesting configuration."""
    initial_capital: float = 100000.0
    commission_rate: float = 0.001  # 0.1%
    slippage_rate: float = 0.0005  # 0.05%
    max_position_size: float = 0.1  # 10% of capital
    risk_free_rate: float = 0.02  # 2% annual
    benchmark_symbol: Optional[str] = "SPY"
    trading_days_per_year: int = 252
    allow_short: bool = True
    margin_requirement: float = 0.5  # 50% for shorts


@dataclass
class BacktestMetrics:
    """Comprehensive backtest performance metrics."""
    # Returns
    total_return: float = 0.0
    annualized_return: float = 0.0
    benchmark_return: float = 0.0
    alpha: float = 0.0
    beta: float = 0.0
    
    # Risk metrics
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    
    # Drawdown
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0  # Days
    average_drawdown: float = 0.0
    
    # Trading metrics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    
    # Efficiency
    avg_holding_period: float = 0.0
    turnover: float = 0.0
    
    # Time series
    equity_curve: List[float] = field(default_factory=list)
    returns: List[float] = field(default_factory=list)
    drawdowns: List[float] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            'total_return': self.total_return,
            'annualized_return': self.annualized_return,
            'benchmark_return': self.benchmark_return,
            'alpha': self.alpha,
            'beta': self.beta,
            'volatility': self.volatility,
            'sharpe_ratio': self.sharpe_ratio,
            'sortino_ratio': self.sortino_ratio,
            'calmar_ratio': self.calmar_ratio,
            'max_drawdown': self.max_drawdown,
            'max_drawdown_duration': self.max_drawdown_duration,
            'average_drawdown': self.average_drawdown,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.win_rate,
            'profit_factor': self.profit_factor,
            'average_win': self.average_win,
            'average_loss': self.average_loss,
            'largest_win': self.largest_win,
            'largest_loss': self.largest_loss,
            'avg_holding_period': self.avg_holding_period,
            'turnover': self.turnover
        }


class BaseStrategy(ABC):
    """Abstract base class for trading strategies."""
    
    @abstractmethod
    def generate_signals(
        self,
        data: pd.DataFrame,
        predictions: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Generate trading signals.
        
        Args:
            data: Market data
            predictions: Optional ML model predictions
            
        Returns:
            Dictionary of symbol -> target position (1=long, -1=short, 0=flat)
        """
        pass
    
    def on_bar(self, timestamp: datetime, data: Dict[str, Any]):
        """Called on each new bar of data."""
        pass


class MLStrategy(BaseStrategy):
    """Strategy that uses ML model predictions."""
    
    def __init__(
        self,
        model: Any,
        threshold: float = 0.6,
        position_sizing: str = "equal"
    ):
        self.model = model
        self.threshold = threshold
        self.position_sizing = position_sizing
    
    def generate_signals(
        self,
        data: pd.DataFrame,
        predictions: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        signals = {}
        
        if predictions:
            for symbol, pred in predictions.items():
                if hasattr(pred, 'confidence'):
                    confidence = pred.confidence
                elif hasattr(pred, 'probability_up'):
                    confidence = abs(pred.probability_up - 0.5) * 2
                else:
                    confidence = 0.5
                
                # Generate signal based on prediction
                if hasattr(pred, 'direction'):
                    direction = pred.direction.value if hasattr(pred.direction, 'value') else pred.direction
                    if 'up' in str(direction).lower() and confidence >= self.threshold:
                        signals[symbol] = 1.0
                    elif 'down' in str(direction).lower() and confidence >= self.threshold:
                        signals[symbol] = -1.0
                    else:
                        signals[symbol] = 0.0
                elif hasattr(pred, 'trend'):
                    trend = pred.trend.value if hasattr(pred.trend, 'value') else pred.trend
                    if 'up' in str(trend).lower() and confidence >= self.threshold:
                        signals[symbol] = 1.0 if 'strong' in str(trend).lower() else 0.5
                    elif 'down' in str(trend).lower() and confidence >= self.threshold:
                        signals[symbol] = -1.0 if 'strong' in str(trend).lower() else -0.5
                    else:
                        signals[symbol] = 0.0
        
        return signals


class Backtester:
    """
    Main backtesting engine.
    
    Features:
    - Event-driven simulation
    - Transaction cost modeling
    - Position sizing
    - Risk management
    - Performance analysis
    """
    
    def __init__(self, config: Optional[BacktestConfig] = None):
        self.config = config or BacktestConfig()
        
        # State
        self.cash = self.config.initial_capital
        self.positions: Dict[str, Position] = {}
        self.orders: List[Order] = []
        self.trades: List[Trade] = []
        self.equity_history: List[Tuple[datetime, float]] = []
        
        # Current timestamp
        self.current_timestamp: Optional[datetime] = None
        
    def reset(self):
        """Reset backtester state."""
        self.cash = self.config.initial_capital
        self.positions = {}
        self.orders = []
        self.trades = []
        self.equity_history = []
        self.current_timestamp = None
    
    @property
    def equity(self) -> float:
        """Current total equity."""
        position_value = sum(pos.market_value for pos in self.positions.values())
        return self.cash + position_value
    
    def _calculate_slippage(self, price: float, side: OrderSide) -> float:
        """Calculate slippage cost."""
        slippage = price * self.config.slippage_rate
        return slippage if side == OrderSide.BUY else -slippage
    
    def _calculate_commission(self, quantity: float, price: float) -> float:
        """Calculate commission cost."""
        return abs(quantity) * price * self.config.commission_rate
    
    def submit_order(self, order: Order) -> Order:
        """Submit an order for execution."""
        order.timestamp = self.current_timestamp or datetime.utcnow()
        self.orders.append(order)
        return order
    
    def _execute_order(
        self,
        order: Order,
        current_price: float
    ) -> Optional[Trade]:
        """Execute an order at current price."""
        # Calculate execution price with slippage
        slippage = self._calculate_slippage(current_price, order.side)
        fill_price = current_price + slippage
        
        # Calculate commission
        commission = self._calculate_commission(order.quantity, fill_price)
        
        # Check if we have enough capital
        cost = order.quantity * fill_price + commission
        
        if order.side == OrderSide.BUY:
            if cost > self.cash:
                logger.warning(f"Insufficient funds for order: {cost} > {self.cash}")
                return None
            self.cash -= cost
        else:  # SELL
            # Check if we have the position
            if order.symbol in self.positions:
                pos = self.positions[order.symbol]
                if order.quantity > pos.quantity and not self.config.allow_short:
                    logger.warning(f"Cannot sell more than owned: {order.quantity} > {pos.quantity}")
                    return None
        
        # Execute
        order.filled = True
        order.fill_price = fill_price
        order.fill_timestamp = self.current_timestamp
        order.commission = commission
        order.slippage = slippage
        
        # Update position
        pnl = self._update_position(order)
        
        # Create trade record
        trade = Trade(
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=fill_price,
            timestamp=self.current_timestamp or datetime.utcnow(),
            commission=commission,
            slippage=abs(slippage),
            pnl=pnl
        )
        
        self.trades.append(trade)
        return trade
    
    def _update_position(self, order: Order) -> float:
        """Update position after order execution and return PnL."""
        pnl = 0.0
        symbol = order.symbol
        fill_price = order.fill_price or 0.0
        
        if order.side == OrderSide.BUY:
            if symbol in self.positions:
                # Add to existing position
                pos = self.positions[symbol]
                total_quantity = pos.quantity + order.quantity
                avg_price = (pos.entry_price * pos.quantity + fill_price * order.quantity) / total_quantity
                pos.quantity = total_quantity
                pos.entry_price = avg_price
            else:
                # New position
                self.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=order.quantity,
                    entry_price=fill_price,
                    entry_timestamp=self.current_timestamp or datetime.utcnow(),
                    current_price=fill_price
                )
        else:  # SELL
            if symbol in self.positions:
                pos = self.positions[symbol]
                # Calculate PnL
                pnl = (fill_price - pos.entry_price) * min(order.quantity, pos.quantity)
                pnl -= order.commission
                
                # Update or close position
                if order.quantity >= pos.quantity:
                    # Full close
                    self.cash += pos.quantity * fill_price - order.commission
                    del self.positions[symbol]
                else:
                    # Partial close
                    pos.quantity -= order.quantity
                    self.cash += order.quantity * fill_price - order.commission
            else:
                # Short position
                if self.config.allow_short:
                    self.positions[symbol] = Position(
                        symbol=symbol,
                        quantity=-order.quantity,
                        entry_price=fill_price,
                        entry_timestamp=self.current_timestamp or datetime.utcnow(),
                        current_price=fill_price
                    )
                    self.cash += order.quantity * fill_price - order.commission
        
        return pnl
    
    def _update_positions(self, prices: Dict[str, float]):
        """Update position values with current prices."""
        for symbol, pos in self.positions.items():
            if symbol in prices:
                pos.current_price = prices[symbol]
                pos.unrealized_pnl = (pos.current_price - pos.entry_price) * pos.quantity
    
    def run(
        self,
        data: pd.DataFrame,
        strategy: BaseStrategy,
        model: Optional[Any] = None
    ) -> BacktestMetrics:
        """
        Run backtest.
        
        Args:
            data: OHLCV data with datetime index
            strategy: Trading strategy
            model: Optional ML model for predictions
            
        Returns:
            BacktestMetrics with results
        """
        self.reset()
        
        # Ensure data is sorted by date
        data = data.sort_index()
        
        # Determine symbols (from columns or assume single symbol)
        if 'symbol' in data.columns:
            symbols = data['symbol'].unique().tolist()
        else:
            symbols = ['default']
        
        # Run simulation
        for timestamp, row in data.iterrows():
            self.current_timestamp = timestamp
            
            # Get current prices
            if 'close' in row:
                prices = {symbols[0]: row['close']}
            else:
                prices = {s: row.get(f'{s}_close', row.get('close', 100)) for s in symbols}
            
            # Update position values
            self._update_positions(prices)
            
            # Generate predictions if model provided
            predictions = {}
            if model is not None:
                try:
                    # Prepare features (simplified)
                    features = row.values.reshape(1, -1) if hasattr(row, 'values') else None
                    if features is not None and hasattr(model, 'predict'):
                        pred = model.predict(features)
                        predictions[symbols[0]] = pred[0] if isinstance(pred, list) else pred
                except Exception as e:
                    logger.debug(f"Prediction error: {e}")
            
            # Generate signals
            signals = strategy.generate_signals(
                data.loc[:timestamp],
                predictions
            )
            
            # Execute signals
            for symbol, signal in signals.items():
                current_price = prices.get(symbol, 100)
                current_pos = self.positions.get(symbol)
                current_qty = current_pos.quantity if current_pos else 0
                
                # Calculate target position
                target_value = self.equity * self.config.max_position_size * signal
                target_qty = target_value / current_price if current_price > 0 else 0
                
                # Calculate trade quantity
                trade_qty = target_qty - current_qty
                
                if abs(trade_qty) > 0.01:  # Minimum trade threshold
                    side = OrderSide.BUY if trade_qty > 0 else OrderSide.SELL
                    order = Order(
                        symbol=symbol,
                        side=side,
                        quantity=abs(trade_qty),
                        order_type=OrderType.MARKET
                    )
                    self._execute_order(order, current_price)
            
            # Record equity
            self.equity_history.append((timestamp, self.equity))
            
            # Strategy callback
            strategy.on_bar(timestamp, dict(row) if hasattr(row, 'to_dict') else {})
        
        # Calculate final metrics
        return self._calculate_metrics(data)
    
    def _calculate_metrics(self, data: pd.DataFrame) -> BacktestMetrics:
        """Calculate comprehensive performance metrics."""
        metrics = BacktestMetrics()
        
        if not self.equity_history:
            return metrics
        
        # Extract equity curve
        equity_curve = [e[1] for e in self.equity_history]
        metrics.equity_curve = equity_curve
        
        # Returns
        initial = equity_curve[0]
        final = equity_curve[-1]
        metrics.total_return = (final - initial) / initial if initial > 0 else 0
        
        # Daily returns
        returns = []
        for i in range(1, len(equity_curve)):
            r = (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1] if equity_curve[i-1] > 0 else 0
            returns.append(r)
        metrics.returns = returns
        
        # Annualized return
        n_days = len(equity_curve)
        if n_days > 1:
            metrics.annualized_return = (
                (1 + metrics.total_return) ** (self.config.trading_days_per_year / n_days) - 1
            )
        
        # Volatility
        if returns:
            metrics.volatility = np.std(returns) * np.sqrt(self.config.trading_days_per_year)
        
        # Sharpe Ratio
        if metrics.volatility > 0:
            excess_return = metrics.annualized_return - self.config.risk_free_rate
            metrics.sharpe_ratio = excess_return / metrics.volatility
        
        # Sortino Ratio (downside volatility)
        negative_returns = [r for r in returns if r < 0]
        if negative_returns:
            downside_vol = np.std(negative_returns) * np.sqrt(self.config.trading_days_per_year)
            if downside_vol > 0:
                metrics.sortino_ratio = (metrics.annualized_return - self.config.risk_free_rate) / downside_vol
        
        # Drawdown analysis
        drawdowns = self._calculate_drawdowns(equity_curve)
        metrics.drawdowns = drawdowns
        metrics.max_drawdown = min(drawdowns) if drawdowns else 0
        metrics.average_drawdown = np.mean([d for d in drawdowns if d < 0]) if any(d < 0 for d in drawdowns) else 0
        
        # Max drawdown duration
        if drawdowns:
            max_duration = 0
            current_duration = 0
            for dd in drawdowns:
                if dd < 0:
                    current_duration += 1
                    max_duration = max(max_duration, current_duration)
                else:
                    current_duration = 0
            metrics.max_drawdown_duration = max_duration
        
        # Calmar Ratio
        if metrics.max_drawdown < 0:
            metrics.calmar_ratio = metrics.annualized_return / abs(metrics.max_drawdown)
        
        # Trade analysis
        metrics.total_trades = len(self.trades)
        
        winning = [t for t in self.trades if t.pnl > 0]
        losing = [t for t in self.trades if t.pnl < 0]
        
        metrics.winning_trades = len(winning)
        metrics.losing_trades = len(losing)
        
        if metrics.total_trades > 0:
            metrics.win_rate = metrics.winning_trades / metrics.total_trades
        
        if winning:
            metrics.average_win = np.mean([t.pnl for t in winning])
            metrics.largest_win = max(t.pnl for t in winning)
        
        if losing:
            metrics.average_loss = np.mean([t.pnl for t in losing])
            metrics.largest_loss = min(t.pnl for t in losing)
        
        # Profit factor
        total_wins = sum(t.pnl for t in winning) if winning else 0
        total_losses = abs(sum(t.pnl for t in losing)) if losing else 1
        metrics.profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        return metrics
    
    def _calculate_drawdowns(self, equity_curve: List[float]) -> List[float]:
        """Calculate drawdown series."""
        drawdowns = []
        peak = equity_curve[0] if equity_curve else 0
        
        for value in equity_curve:
            if value > peak:
                peak = value
            drawdown = (value - peak) / peak if peak > 0 else 0
            drawdowns.append(drawdown)
        
        return drawdowns


class WalkForwardBacktester(Backtester):
    """
    Walk-forward backtesting.
    
    Trains model on rolling windows and tests on out-of-sample data.
    """
    
    def __init__(
        self,
        config: Optional[BacktestConfig] = None,
        train_window: int = 252,  # 1 year
        test_window: int = 63,    # 3 months
        retrain_frequency: int = 21  # Monthly
    ):
        super().__init__(config)
        self.train_window = train_window
        self.test_window = test_window
        self.retrain_frequency = retrain_frequency
        
        self.models_used: List[Dict[str, Any]] = []
    
    def run(
        self,
        data: pd.DataFrame,
        strategy: BaseStrategy,
        model: Optional[Any] = None,
        X: Optional[np.ndarray] = None,
        y: Optional[np.ndarray] = None
    ) -> BacktestMetrics:
        """
        Run walk-forward backtest.
        
        Args:
            data: Market data
            strategy: Trading strategy
            model: ML model (must have fit/predict methods)
            X: Features for model training
            y: Targets for model training
        """
        self.reset()
        self.models_used = []
        
        if model is None or X is None or y is None:
            # Fallback to regular backtest
            return super().run(data, strategy, model)
        
        data = data.sort_index()
        n_samples = len(data)
        
        # Walk-forward iteration
        current_model = None
        last_train_idx = 0
        
        for i in range(self.train_window, n_samples):
            # Check if we need to retrain
            if (i - last_train_idx) >= self.retrain_frequency or current_model is None:
                train_start = max(0, i - self.train_window)
                train_end = i
                
                # Train model
                X_train = X[train_start:train_end]
                y_train = y[train_start:train_end]
                
                try:
                    if hasattr(model, 'fit'):
                        model.fit(X_train, y_train)
                        current_model = model
                        last_train_idx = i
                        
                        self.models_used.append({
                            'train_start': train_start,
                            'train_end': train_end,
                            'test_start': i
                        })
                except Exception as e:
                    logger.warning(f"Model training failed: {e}")
            
            # Get current row
            row = data.iloc[i]
            timestamp = data.index[i]
            self.current_timestamp = timestamp
            
            # Update prices
            prices = {'default': row['close'] if 'close' in row else 100}
            self._update_positions(prices)
            
            # Generate prediction
            predictions = {}
            if current_model is not None:
                try:
                    features = X[i:i+1]
                    pred = current_model.predict(features)
                    predictions['default'] = pred[0] if isinstance(pred, list) else pred
                except Exception as e:
                    logger.debug(f"Prediction failed: {e}")
            
            # Generate and execute signals
            signals = strategy.generate_signals(data.iloc[:i+1], predictions)
            
            for symbol, signal in signals.items():
                current_price = prices.get(symbol, 100)
                current_pos = self.positions.get(symbol)
                current_qty = current_pos.quantity if current_pos else 0
                
                target_value = self.equity * self.config.max_position_size * signal
                target_qty = target_value / current_price if current_price > 0 else 0
                trade_qty = target_qty - current_qty
                
                if abs(trade_qty) > 0.01:
                    side = OrderSide.BUY if trade_qty > 0 else OrderSide.SELL
                    order = Order(symbol=symbol, side=side, quantity=abs(trade_qty))
                    self._execute_order(order, current_price)
            
            self.equity_history.append((timestamp, self.equity))
        
        return self._calculate_metrics(data)


def run_backtest(
    data: pd.DataFrame,
    strategy: BaseStrategy,
    model: Optional[Any] = None,
    config: Optional[BacktestConfig] = None,
    walk_forward: bool = False,
    X: Optional[np.ndarray] = None,
    y: Optional[np.ndarray] = None
) -> BacktestMetrics:
    """
    Convenience function to run a backtest.
    
    Args:
        data: Market data
        strategy: Trading strategy
        model: Optional ML model
        config: Backtest configuration
        walk_forward: Use walk-forward testing
        X: Features for walk-forward training
        y: Targets for walk-forward training
        
    Returns:
        BacktestMetrics
    """
    if walk_forward:
        backtester = WalkForwardBacktester(config)
        return backtester.run(data, strategy, model, X, y)
    else:
        backtester = Backtester(config)
        return backtester.run(data, strategy, model)
