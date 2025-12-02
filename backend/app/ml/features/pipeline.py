"""
Feature Pipeline

Orchestrates feature calculation and storage:
- Scheduled feature updates
- Batch processing
- Historical backfill
- Quality validation
"""
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import asyncio
from loguru import logger

from app.ml.features.technical_features import (
    TechnicalFeaturesCalculator,
    TechnicalFeatures,
    calculate_technical_features,
)
from app.ml.features.fundamental_features import (
    FundamentalFeaturesCalculator,
    FundamentalFeatures,
    FinancialStatements,
    calculate_fundamental_features,
)
from app.ml.features.market_features import (
    MarketFeaturesCalculator,
    MarketFeatures,
    calculate_market_features,
    SECTOR_MAPPING,
    SECTOR_ETF_MAPPING,
)
from app.ml.features.feature_store import (
    FeatureStore,
    CombinedFeatures,
    get_feature_store,
)


class FeatureType(Enum):
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    MARKET = "market"


@dataclass
class PipelineConfig:
    """Configuration for feature pipeline."""
    # Processing settings
    batch_size: int = 50
    parallel_jobs: int = 4
    retry_attempts: int = 3
    retry_delay_seconds: int = 5
    
    # Feature settings
    technical_lookback_days: int = 252  # 1 year
    fundamental_update_frequency: str = "quarterly"
    market_lookback_days: int = 252
    
    # Validation thresholds
    max_missing_features_pct: float = 0.1  # 10% max missing
    min_data_points: int = 100
    
    # Scheduling
    intraday_update_interval_minutes: int = 5
    daily_update_time: str = "18:00"  # After market close
    weekend_skip: bool = True


@dataclass
class FeatureQuality:
    """Quality metrics for calculated features."""
    symbol: str
    feature_type: str
    timestamp: str
    
    total_features: int = 0
    filled_features: int = 0
    missing_features: int = 0
    missing_pct: float = 0.0
    
    validation_passed: bool = True
    validation_errors: List[str] = None
    
    def __post_init__(self):
        if self.validation_errors is None:
            self.validation_errors = []
    
    def to_dict(self) -> dict:
        return {
            'symbol': self.symbol,
            'feature_type': self.feature_type,
            'timestamp': self.timestamp,
            'total_features': self.total_features,
            'filled_features': self.filled_features,
            'missing_features': self.missing_features,
            'missing_pct': self.missing_pct,
            'validation_passed': self.validation_passed,
            'validation_errors': self.validation_errors,
        }


@dataclass
class PipelineResult:
    """Result of pipeline execution."""
    success: bool
    symbols_processed: int
    symbols_failed: int
    features_calculated: int
    duration_seconds: float
    errors: List[str]
    quality_reports: List[FeatureQuality]
    
    def to_dict(self) -> dict:
        return {
            'success': self.success,
            'symbols_processed': self.symbols_processed,
            'symbols_failed': self.symbols_failed,
            'features_calculated': self.features_calculated,
            'duration_seconds': self.duration_seconds,
            'errors': self.errors,
            'quality_reports': [q.to_dict() for q in self.quality_reports],
        }


class FeaturePipeline:
    """
    Orchestrates ML feature calculation and storage.
    
    Handles:
    - Technical, fundamental, and market feature calculation
    - Batch processing of multiple symbols
    - Quality validation
    - Historical backfill
    
    Usage:
        pipeline = FeaturePipeline()
        
        # Process single symbol
        features = await pipeline.process_symbol("AAPL", price_data, market_data)
        
        # Batch process
        result = await pipeline.process_batch(["AAPL", "MSFT", "GOOGL"], ...)
    """
    
    def __init__(
        self,
        config: Optional[PipelineConfig] = None,
        feature_store: Optional[FeatureStore] = None,
    ):
        self.config = config or PipelineConfig()
        self.store = feature_store or get_feature_store()
        
        # Calculators
        self.technical_calc = TechnicalFeaturesCalculator()
        self.fundamental_calc = FundamentalFeaturesCalculator()
        self.market_calc = MarketFeaturesCalculator()
        
        # Callbacks
        self._on_symbol_complete: List[Callable] = []
        self._on_error: List[Callable] = []
    
    async def process_symbol(
        self,
        symbol: str,
        prices: List[float],
        highs: List[float],
        lows: List[float],
        volumes: List[float],
        spy_returns: Optional[List[float]] = None,
        sector_returns: Optional[List[float]] = None,
        fundamental_data: Optional[Dict[str, Any]] = None,
        market_data: Optional[Dict[str, Any]] = None,
    ) -> tuple[CombinedFeatures, FeatureQuality]:
        """
        Process a single symbol and calculate all features.
        
        Args:
            symbol: Stock symbol
            prices: Close prices (most recent last)
            highs: High prices
            lows: Low prices  
            volumes: Trading volumes
            spy_returns: S&P 500 daily returns
            sector_returns: Sector ETF daily returns
            fundamental_data: Financial statement data
            market_data: Market regime data
        
        Returns:
            Tuple of (CombinedFeatures, FeatureQuality)
        """
        timestamp = datetime.utcnow().isoformat()
        technical = None
        fundamental = None
        market = None
        quality_errors = []
        
        # Calculate technical features
        try:
            if len(prices) >= self.config.min_data_points:
                technical = calculate_technical_features(
                    symbol=symbol,
                    timestamp=timestamp,
                    prices=prices,
                    highs=highs,
                    lows=lows,
                    volumes=volumes,
                )
            else:
                quality_errors.append(f"Insufficient price data: {len(prices)} points")
        except Exception as e:
            logger.error(f"Technical feature error for {symbol}: {e}")
            quality_errors.append(f"Technical calculation error: {str(e)}")
        
        # Calculate fundamental features
        try:
            if fundamental_data:
                statements = self._parse_fundamental_data(fundamental_data)
                current_price = prices[-1] if prices else 0
                fundamental = calculate_fundamental_features(
                    symbol=symbol,
                    current_price=current_price,
                    statements=statements,
                    market_data=fundamental_data.get('market_data'),
                )
        except Exception as e:
            logger.error(f"Fundamental feature error for {symbol}: {e}")
            quality_errors.append(f"Fundamental calculation error: {str(e)}")
        
        # Calculate market features
        try:
            if spy_returns and len(prices) >= self.config.min_data_points:
                # Calculate stock returns
                stock_returns = [
                    (prices[i] - prices[i-1]) / prices[i-1]
                    for i in range(1, len(prices))
                ]
                
                market = calculate_market_features(
                    symbol=symbol,
                    stock_returns=stock_returns,
                    spy_returns=spy_returns,
                    sector_returns=sector_returns,
                    market_data=market_data,
                )
        except Exception as e:
            logger.error(f"Market feature error for {symbol}: {e}")
            quality_errors.append(f"Market calculation error: {str(e)}")
        
        # Store features
        combined = self.store.store_features(
            symbol=symbol,
            timestamp=timestamp,
            technical=technical,
            fundamental=fundamental,
            market=market,
        )
        
        # Calculate quality metrics
        quality = self._calculate_quality(
            symbol=symbol,
            timestamp=timestamp,
            combined=combined,
            errors=quality_errors,
        )
        
        # Trigger callbacks
        for callback in self._on_symbol_complete:
            try:
                callback(symbol, combined, quality)
            except Exception as e:
                logger.error(f"Callback error: {e}")
        
        return combined, quality
    
    async def process_batch(
        self,
        symbols: List[str],
        price_data: Dict[str, Dict[str, List[float]]],
        spy_returns: Optional[List[float]] = None,
        sector_returns: Optional[Dict[str, List[float]]] = None,
        fundamental_data: Optional[Dict[str, Dict]] = None,
        market_data: Optional[Dict[str, Any]] = None,
    ) -> PipelineResult:
        """
        Process multiple symbols in batch.
        
        Args:
            symbols: List of stock symbols
            price_data: Dict mapping symbols to OHLCV data
                       {'AAPL': {'prices': [...], 'highs': [...], ...}}
            spy_returns: S&P 500 daily returns
            sector_returns: Dict mapping sector names to returns
            fundamental_data: Dict mapping symbols to fundamental data
            market_data: Market regime data
        
        Returns:
            PipelineResult with processing summary
        """
        start_time = datetime.utcnow()
        
        processed = 0
        failed = 0
        features_count = 0
        errors = []
        quality_reports = []
        
        for symbol in symbols:
            try:
                # Get price data for symbol
                symbol_prices = price_data.get(symbol, {})
                if not symbol_prices:
                    errors.append(f"{symbol}: No price data")
                    failed += 1
                    continue
                
                # Get sector returns
                sector = SECTOR_MAPPING.get(symbol)
                sym_sector_returns = None
                if sector and sector_returns:
                    sector_etf = SECTOR_ETF_MAPPING.get(sector)
                    if sector_etf:
                        sym_sector_returns = sector_returns.get(sector)
                
                # Get fundamental data
                sym_fundamental = None
                if fundamental_data:
                    sym_fundamental = fundamental_data.get(symbol)
                
                # Process symbol
                combined, quality = await self.process_symbol(
                    symbol=symbol,
                    prices=symbol_prices.get('prices', []),
                    highs=symbol_prices.get('highs', []),
                    lows=symbol_prices.get('lows', []),
                    volumes=symbol_prices.get('volumes', []),
                    spy_returns=spy_returns,
                    sector_returns=sym_sector_returns,
                    fundamental_data=sym_fundamental,
                    market_data=market_data,
                )
                
                processed += 1
                quality_reports.append(quality)
                
                # Count features
                if combined.technical:
                    features_count += 1
                if combined.fundamental:
                    features_count += 1
                if combined.market:
                    features_count += 1
                
            except Exception as e:
                logger.error(f"Pipeline error for {symbol}: {e}")
                errors.append(f"{symbol}: {str(e)}")
                failed += 1
                
                for callback in self._on_error:
                    try:
                        callback(symbol, e)
                    except:
                        pass
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        return PipelineResult(
            success=failed == 0,
            symbols_processed=processed,
            symbols_failed=failed,
            features_calculated=features_count,
            duration_seconds=duration,
            errors=errors,
            quality_reports=quality_reports,
        )
    
    async def backfill_historical(
        self,
        symbol: str,
        historical_prices: Dict[str, Dict[str, List[float]]],
        spy_returns: Optional[Dict[str, List[float]]] = None,
    ) -> List[CombinedFeatures]:
        """
        Backfill historical features for a symbol.
        
        Args:
            symbol: Stock symbol
            historical_prices: Dict mapping dates to price data
            spy_returns: Historical SPY returns by date
        
        Returns:
            List of CombinedFeatures for each date
        """
        results = []
        
        # Sort dates
        dates = sorted(historical_prices.keys())
        
        # Need rolling window of data
        all_prices = []
        all_highs = []
        all_lows = []
        all_volumes = []
        
        for date in dates:
            day_data = historical_prices[date]
            all_prices.append(day_data.get('close', 0))
            all_highs.append(day_data.get('high', 0))
            all_lows.append(day_data.get('low', 0))
            all_volumes.append(day_data.get('volume', 0))
            
            # Only calculate once we have enough data
            if len(all_prices) >= self.config.min_data_points:
                try:
                    spy_ret = None
                    if spy_returns and date in spy_returns:
                        spy_ret = spy_returns[date]
                    
                    combined, _ = await self.process_symbol(
                        symbol=symbol,
                        prices=all_prices.copy(),
                        highs=all_highs.copy(),
                        lows=all_lows.copy(),
                        volumes=all_volumes.copy(),
                        spy_returns=spy_ret,
                    )
                    results.append(combined)
                except Exception as e:
                    logger.warning(f"Backfill error for {symbol} on {date}: {e}")
        
        logger.info(f"Backfilled {len(results)} feature sets for {symbol}")
        return results
    
    def _parse_fundamental_data(self, data: Dict[str, Any]) -> FinancialStatements:
        """Parse raw fundamental data into FinancialStatements."""
        return FinancialStatements(
            revenue=data.get('revenue'),
            cost_of_revenue=data.get('cost_of_revenue'),
            gross_profit=data.get('gross_profit'),
            operating_income=data.get('operating_income'),
            net_income=data.get('net_income'),
            ebitda=data.get('ebitda'),
            eps=data.get('eps'),
            eps_diluted=data.get('eps_diluted'),
            total_assets=data.get('total_assets'),
            total_liabilities=data.get('total_liabilities'),
            total_equity=data.get('total_equity'),
            current_assets=data.get('current_assets'),
            current_liabilities=data.get('current_liabilities'),
            cash_and_equivalents=data.get('cash'),
            total_debt=data.get('total_debt'),
            long_term_debt=data.get('long_term_debt'),
            short_term_debt=data.get('short_term_debt'),
            inventory=data.get('inventory'),
            accounts_receivable=data.get('accounts_receivable'),
            operating_cash_flow=data.get('operating_cash_flow'),
            investing_cash_flow=data.get('investing_cash_flow'),
            financing_cash_flow=data.get('financing_cash_flow'),
            free_cash_flow=data.get('free_cash_flow'),
            capital_expenditure=data.get('capex'),
            dividends_paid=data.get('dividends_paid'),
            shares_outstanding=data.get('shares_outstanding'),
            shares_diluted=data.get('shares_diluted'),
        )
    
    def _calculate_quality(
        self,
        symbol: str,
        timestamp: str,
        combined: CombinedFeatures,
        errors: List[str],
    ) -> FeatureQuality:
        """Calculate quality metrics for features."""
        total = 0
        filled = 0
        
        # Count technical features
        if combined.technical:
            tech_dict = combined.technical.to_dict()
            tech_features = {k: v for k, v in tech_dict.items() 
                          if k not in ('symbol', 'timestamp')}
            total += len(TechnicalFeaturesCalculator.get_feature_names())
            filled += len(tech_features)
        
        # Count fundamental features
        if combined.fundamental:
            fund_dict = combined.fundamental.to_dict()
            fund_features = {k: v for k, v in fund_dict.items() 
                          if k not in ('symbol', 'timestamp')}
            total += len(FundamentalFeaturesCalculator.get_feature_names())
            filled += len(fund_features)
        
        # Count market features
        if combined.market:
            mkt_dict = combined.market.to_dict()
            mkt_features = {k: v for k, v in mkt_dict.items() 
                         if k not in ('symbol', 'timestamp', 'sector_name', 'market_regime')}
            total += len(MarketFeaturesCalculator.get_feature_names())
            filled += len(mkt_features)
        
        missing = total - filled
        missing_pct = missing / total if total > 0 else 0
        
        validation_passed = (
            missing_pct <= self.config.max_missing_features_pct
            and len(errors) == 0
        )
        
        return FeatureQuality(
            symbol=symbol,
            feature_type='combined',
            timestamp=timestamp,
            total_features=total,
            filled_features=filled,
            missing_features=missing,
            missing_pct=missing_pct,
            validation_passed=validation_passed,
            validation_errors=errors,
        )
    
    def on_symbol_complete(self, callback: Callable) -> None:
        """Register callback for symbol completion."""
        self._on_symbol_complete.append(callback)
    
    def on_error(self, callback: Callable) -> None:
        """Register callback for errors."""
        self._on_error.append(callback)


# Global pipeline instance
_pipeline: Optional[FeaturePipeline] = None


def get_feature_pipeline() -> FeaturePipeline:
    """Get or create global feature pipeline."""
    global _pipeline
    if _pipeline is None:
        _pipeline = FeaturePipeline()
    return _pipeline
