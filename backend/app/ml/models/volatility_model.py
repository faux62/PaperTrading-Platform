"""
Volatility Models

Models for predicting and forecasting market volatility:
- GARCH(1,1) for short-term volatility
- EWMA for exponentially weighted volatility
- Realized volatility estimators
- Prophet-style trend decomposition
"""
import numpy as np
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import pickle
from pathlib import Path
from loguru import logger


class VolatilityRegime(str, Enum):
    """Market volatility regime classification."""
    VERY_LOW = "very_low"      # < 10% annualized
    LOW = "low"                # 10-15%
    NORMAL = "normal"          # 15-25%
    HIGH = "high"              # 25-35%
    VERY_HIGH = "very_high"    # > 35%


@dataclass
class VolatilityForecast:
    """Result of a volatility forecast."""
    symbol: str
    current_volatility: float  # Annualized
    forecast_volatility: float  # Predicted annualized
    regime: VolatilityRegime
    confidence_interval: Tuple[float, float]  # 95% CI
    forecast_horizon_days: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    model_type: str = "GARCH"
    model_version: str = "1.0.0"
    
    # Additional metrics
    vix_comparison: Optional[float] = None  # Ratio to VIX
    percentile_rank: Optional[float] = None  # Historical percentile
    trend: Optional[str] = None  # "increasing", "decreasing", "stable"
    
    def to_dict(self) -> dict:
        return {
            'symbol': self.symbol,
            'current_volatility': self.current_volatility,
            'forecast_volatility': self.forecast_volatility,
            'regime': self.regime.value,
            'confidence_interval': list(self.confidence_interval),
            'forecast_horizon_days': self.forecast_horizon_days,
            'timestamp': self.timestamp.isoformat(),
            'model_type': self.model_type,
            'model_version': self.model_version,
            'vix_comparison': self.vix_comparison,
            'percentile_rank': self.percentile_rank,
            'trend': self.trend
        }


@dataclass
class GARCHConfig:
    """GARCH model configuration."""
    p: int = 1  # GARCH lag order
    q: int = 1  # ARCH lag order
    dist: str = "normal"  # Error distribution: "normal", "t", "ged"
    mean_model: str = "constant"  # Mean model: "zero", "constant", "ar"
    
    # Volatility targeting
    use_vol_targeting: bool = True
    target_vol: float = 0.15  # 15% annualized target
    
    # Forecasting
    forecast_horizon: int = 21  # Days to forecast
    n_simulations: int = 1000  # For Monte Carlo
    
    # Regime thresholds (annualized)
    very_low_threshold: float = 0.10
    low_threshold: float = 0.15
    high_threshold: float = 0.25
    very_high_threshold: float = 0.35
    
    def to_dict(self) -> dict:
        return {
            'p': self.p,
            'q': self.q,
            'dist': self.dist,
            'mean_model': self.mean_model,
            'forecast_horizon': self.forecast_horizon,
            'n_simulations': self.n_simulations
        }


class GARCHVolatilityModel:
    """
    GARCH(p,q) model for volatility forecasting.
    
    GARCH(1,1) equation:
    σ²(t) = ω + α * ε²(t-1) + β * σ²(t-1)
    
    Where:
    - σ²(t) is the conditional variance at time t
    - ω is the constant (omega)
    - α is the ARCH coefficient (alpha)
    - β is the GARCH coefficient (beta)
    - ε(t-1) is the previous period's return
    """
    
    def __init__(self, config: Optional[GARCHConfig] = None):
        self.config = config or GARCHConfig()
        self.model = None
        self.fitted_model = None
        self.is_trained = False
        self.model_version = "1.0.0"
        
        # GARCH parameters (after fitting)
        self.omega: Optional[float] = None
        self.alpha: Optional[float] = None
        self.beta: Optional[float] = None
        self.persistence: Optional[float] = None  # alpha + beta
        self.long_run_variance: Optional[float] = None
        
        # Historical volatility data
        self.vol_history: List[float] = []
        
    def _calculate_returns(self, prices: np.ndarray) -> np.ndarray:
        """Calculate log returns from prices."""
        return np.diff(np.log(prices)) * 100  # Percentage returns
    
    def fit(
        self,
        prices: np.ndarray,
        returns: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """
        Fit GARCH model to price or return data.
        
        Args:
            prices: Array of prices (will calculate returns)
            returns: Pre-calculated returns (optional)
            
        Returns:
            Fitting results with parameters
        """
        # Calculate returns if not provided
        if returns is None:
            returns = self._calculate_returns(prices)
        
        logger.info(f"Fitting GARCH({self.config.p},{self.config.q}) to {len(returns)} observations")
        
        try:
            from arch import arch_model
            
            # Create and fit GARCH model
            self.model = arch_model(
                returns,
                p=self.config.p,
                q=self.config.q,
                mean=self.config.mean_model,
                vol='Garch',
                dist=self.config.dist
            )
            
            self.fitted_model = self.model.fit(disp='off')
            
            # Extract parameters
            params = self.fitted_model.params
            self.omega = float(params.get('omega', 0))
            self.alpha = float(params.get('alpha[1]', 0))
            self.beta = float(params.get('beta[1]', 0))
            
            # Calculate derived metrics
            self.persistence = self.alpha + self.beta
            if self.persistence < 1:
                self.long_run_variance = self.omega / (1 - self.persistence)
            
            # Store volatility history
            self.vol_history = list(self.fitted_model.conditional_volatility)
            
            self.is_trained = True
            
            results = {
                'omega': self.omega,
                'alpha': self.alpha,
                'beta': self.beta,
                'persistence': self.persistence,
                'long_run_volatility': np.sqrt(self.long_run_variance) * np.sqrt(252) if self.long_run_variance else None,
                'log_likelihood': float(self.fitted_model.loglikelihood),
                'aic': float(self.fitted_model.aic),
                'bic': float(self.fitted_model.bic)
            }
            
            logger.info(f"GARCH fit complete. Persistence: {self.persistence:.4f}")
            
            return results
            
        except ImportError:
            logger.warning("arch package not available, using simple EWMA")
            return self._fit_ewma(returns)
    
    def _fit_ewma(self, returns: np.ndarray) -> Dict[str, Any]:
        """Fallback to EWMA volatility."""
        # Use standard EWMA with lambda = 0.94 (RiskMetrics)
        lambda_param = 0.94
        
        variance = np.zeros(len(returns))
        variance[0] = returns[0] ** 2
        
        for i in range(1, len(returns)):
            variance[i] = lambda_param * variance[i-1] + (1 - lambda_param) * returns[i-1] ** 2
        
        self.vol_history = list(np.sqrt(variance))
        self.alpha = 1 - lambda_param
        self.beta = lambda_param
        self.persistence = 1.0
        self.is_trained = True
        
        return {
            'method': 'EWMA',
            'lambda': lambda_param,
            'current_volatility': self.vol_history[-1]
        }
    
    def forecast(
        self,
        horizon: Optional[int] = None,
        n_simulations: Optional[int] = None
    ) -> VolatilityForecast:
        """
        Forecast future volatility.
        
        Args:
            horizon: Forecast horizon in days
            n_simulations: Number of Monte Carlo simulations
            
        Returns:
            VolatilityForecast object
        """
        if not self.is_trained:
            raise ValueError("Model not fitted yet")
        
        horizon = horizon or self.config.forecast_horizon
        n_simulations = n_simulations or self.config.n_simulations
        
        # Current volatility (annualized)
        current_vol = self.vol_history[-1] * np.sqrt(252) / 100 if self.vol_history else 0.20
        
        try:
            if self.fitted_model is not None:
                # Use arch package forecasting
                forecast = self.fitted_model.forecast(horizon=horizon)
                forecast_variance = forecast.variance.values[-1, :]
                
                # Average forecast volatility
                avg_variance = np.mean(forecast_variance)
                forecast_vol = np.sqrt(avg_variance) * np.sqrt(252) / 100
                
                # Confidence interval via simulation
                simulations = self.fitted_model.forecast(
                    horizon=horizon,
                    method='simulation',
                    simulations=n_simulations
                )
                
                sim_vols = np.sqrt(simulations.variance.values[-1, :]) * np.sqrt(252) / 100
                ci_lower = float(np.percentile(sim_vols, 2.5))
                ci_upper = float(np.percentile(sim_vols, 97.5))
            else:
                # EWMA forecast (mean-reverting)
                forecast_vol = current_vol
                ci_lower = forecast_vol * 0.8
                ci_upper = forecast_vol * 1.2
        
        except Exception as e:
            logger.warning(f"Forecast error: {e}, using current vol")
            forecast_vol = current_vol
            ci_lower = forecast_vol * 0.8
            ci_upper = forecast_vol * 1.2
        
        # Determine regime
        regime = self._classify_regime(forecast_vol)
        
        # Determine trend
        if len(self.vol_history) >= 20:
            recent_vol = np.mean(self.vol_history[-5:])
            older_vol = np.mean(self.vol_history[-20:-5])
            if recent_vol > older_vol * 1.1:
                trend = "increasing"
            elif recent_vol < older_vol * 0.9:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "unknown"
        
        # Calculate percentile rank
        if len(self.vol_history) >= 252:
            percentile = np.sum(np.array(self.vol_history) <= current_vol * 100 / np.sqrt(252)) / len(self.vol_history)
        else:
            percentile = None
        
        return VolatilityForecast(
            symbol="",  # Set by caller
            current_volatility=float(current_vol),
            forecast_volatility=float(forecast_vol),
            regime=regime,
            confidence_interval=(ci_lower, ci_upper),
            forecast_horizon_days=horizon,
            model_type=f"GARCH({self.config.p},{self.config.q})",
            model_version=self.model_version,
            percentile_rank=percentile,
            trend=trend
        )
    
    def _classify_regime(self, volatility: float) -> VolatilityRegime:
        """Classify volatility into regime."""
        if volatility < self.config.very_low_threshold:
            return VolatilityRegime.VERY_LOW
        elif volatility < self.config.low_threshold:
            return VolatilityRegime.LOW
        elif volatility < self.config.high_threshold:
            return VolatilityRegime.NORMAL
        elif volatility < self.config.very_high_threshold:
            return VolatilityRegime.HIGH
        else:
            return VolatilityRegime.VERY_HIGH
    
    def get_historical_volatility(
        self,
        window: int = 20,
        annualize: bool = True
    ) -> np.ndarray:
        """Get historical realized volatility."""
        if not self.vol_history:
            return np.array([])
        
        vol = np.array(self.vol_history)
        
        if annualize:
            vol = vol * np.sqrt(252) / 100
        
        return vol
    
    def save(self, path: str):
        """Save model to disk."""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        
        # Save fitted model
        if self.fitted_model is not None:
            with open(path / "garch_model.pkl", 'wb') as f:
                pickle.dump(self.fitted_model, f)
        
        # Save metadata
        metadata = {
            'config': self.config.to_dict(),
            'omega': self.omega,
            'alpha': self.alpha,
            'beta': self.beta,
            'persistence': self.persistence,
            'long_run_variance': self.long_run_variance,
            'vol_history': self.vol_history[-252:],  # Last year
            'is_trained': self.is_trained,
            'model_version': self.model_version,
            'saved_at': datetime.utcnow().isoformat()
        }
        
        with open(path / "metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Model saved to {path}")
    
    @classmethod
    def load(cls, path: str) -> 'GARCHVolatilityModel':
        """Load model from disk."""
        path = Path(path)
        
        with open(path / "metadata.json", 'r') as f:
            metadata = json.load(f)
        
        config = GARCHConfig(**metadata['config'])
        model = cls(config)
        model.omega = metadata['omega']
        model.alpha = metadata['alpha']
        model.beta = metadata['beta']
        model.persistence = metadata['persistence']
        model.long_run_variance = metadata['long_run_variance']
        model.vol_history = metadata['vol_history']
        model.is_trained = metadata['is_trained']
        model.model_version = metadata['model_version']
        
        # Load fitted model
        fitted_path = path / "garch_model.pkl"
        if fitted_path.exists():
            with open(fitted_path, 'rb') as f:
                model.fitted_model = pickle.load(f)
        
        return model


class RealizedVolatilityEstimator:
    """
    Various realized volatility estimators for high-frequency data.
    """
    
    @staticmethod
    def close_to_close(prices: np.ndarray, window: int = 20) -> np.ndarray:
        """Standard close-to-close volatility."""
        returns = np.diff(np.log(prices))
        vol = np.zeros(len(prices))
        
        for i in range(window, len(prices)):
            vol[i] = np.std(returns[i-window:i]) * np.sqrt(252)
        
        return vol
    
    @staticmethod
    def parkinson(
        high: np.ndarray,
        low: np.ndarray,
        window: int = 20
    ) -> np.ndarray:
        """
        Parkinson volatility estimator using high-low range.
        More efficient than close-to-close.
        """
        log_hl = np.log(high / low)
        factor = 1 / (4 * np.log(2))
        
        vol = np.zeros(len(high))
        for i in range(window, len(high)):
            vol[i] = np.sqrt(factor * np.mean(log_hl[i-window:i] ** 2) * 252)
        
        return vol
    
    @staticmethod
    def garman_klass(
        open_: np.ndarray,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        window: int = 20
    ) -> np.ndarray:
        """
        Garman-Klass volatility estimator.
        Uses OHLC data for better efficiency.
        """
        log_hl = np.log(high / low) ** 2
        log_co = np.log(close / open_) ** 2
        
        gk = 0.5 * log_hl - (2 * np.log(2) - 1) * log_co
        
        vol = np.zeros(len(high))
        for i in range(window, len(high)):
            vol[i] = np.sqrt(np.mean(gk[i-window:i]) * 252)
        
        return vol
    
    @staticmethod
    def yang_zhang(
        open_: np.ndarray,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        window: int = 20
    ) -> np.ndarray:
        """
        Yang-Zhang volatility estimator.
        Handles overnight gaps and is drift-independent.
        """
        n = len(close)
        vol = np.zeros(n)
        
        if n < window + 1:
            return vol
        
        # Overnight variance
        log_oc = np.log(open_[1:] / close[:-1])
        
        # Open-close variance  
        log_co = np.log(close / open_)
        
        # Rogers-Satchell variance
        log_ho = np.log(high / open_)
        log_lo = np.log(low / open_)
        log_hc = np.log(high / close)
        log_lc = np.log(low / close)
        rs = log_ho * log_hc + log_lo * log_lc
        
        k = 0.34 / (1.34 + (window + 1) / (window - 1))
        
        for i in range(window, n):
            overnight_var = np.var(log_oc[i-window:i-1])
            openclose_var = np.var(log_co[i-window:i])
            rs_var = np.mean(rs[i-window:i])
            
            yz_var = overnight_var + k * openclose_var + (1 - k) * rs_var
            vol[i] = np.sqrt(yz_var * 252)
        
        return vol


class VolatilitySurfaceModel:
    """
    Model for term structure of volatility (simple implementation).
    """
    
    def __init__(self):
        self.term_vols: Dict[int, float] = {}  # days -> volatility
        
    def fit(self, prices: np.ndarray, windows: List[int] = None):
        """Fit volatility term structure."""
        windows = windows or [5, 10, 20, 60, 120, 252]
        returns = np.diff(np.log(prices))
        
        for window in windows:
            if len(returns) >= window:
                vol = np.std(returns[-window:]) * np.sqrt(252)
                self.term_vols[window] = float(vol)
    
    def get_term_structure(self) -> Dict[int, float]:
        """Get the volatility term structure."""
        return self.term_vols
    
    def interpolate(self, days: int) -> float:
        """Interpolate volatility for a specific tenor."""
        if days in self.term_vols:
            return self.term_vols[days]
        
        # Linear interpolation
        sorted_tenors = sorted(self.term_vols.keys())
        
        if days < sorted_tenors[0]:
            return self.term_vols[sorted_tenors[0]]
        if days > sorted_tenors[-1]:
            return self.term_vols[sorted_tenors[-1]]
        
        # Find surrounding tenors
        lower = max(t for t in sorted_tenors if t <= days)
        upper = min(t for t in sorted_tenors if t >= days)
        
        if lower == upper:
            return self.term_vols[lower]
        
        # Linear interpolation
        weight = (days - lower) / (upper - lower)
        return self.term_vols[lower] * (1 - weight) + self.term_vols[upper] * weight
