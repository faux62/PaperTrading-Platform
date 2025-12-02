"""
PaperTrading Platform - Analytics API Endpoints

Provides REST API for:
- Performance analytics
- Risk metrics
- Benchmark comparisons
- Custom reports
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from enum import Enum
import numpy as np
from loguru import logger

from app.core.analytics import (
    get_performance_analytics,
    get_risk_metrics_calculator,
    get_benchmark_service,
    VaRMethod,
    BenchmarkType
)


router = APIRouter()


# ==================== Schemas ====================

class TimeRange(str, Enum):
    """Predefined time ranges."""
    ONE_WEEK = "1W"
    ONE_MONTH = "1M"
    THREE_MONTHS = "3M"
    SIX_MONTHS = "6M"
    ONE_YEAR = "1Y"
    YTD = "YTD"
    ALL = "ALL"


class PerformanceRequest(BaseModel):
    """Performance analysis request."""
    time_range: TimeRange = TimeRange.ONE_YEAR
    benchmark_symbol: Optional[str] = "SPY"
    include_drawdown: bool = True
    include_rolling: bool = False
    rolling_window: int = 60


class RiskMetricsRequest(BaseModel):
    """Risk metrics request."""
    time_range: TimeRange = TimeRange.ONE_YEAR
    var_confidence: float = Field(0.95, ge=0.9, le=0.99)
    var_method: str = "historical"
    include_factor_analysis: bool = False
    include_stress_test: bool = False


class BenchmarkRequest(BaseModel):
    """Benchmark comparison request."""
    benchmark_symbols: List[str] = Field(default_factory=lambda: ["SPY"])
    time_range: TimeRange = TimeRange.ONE_YEAR
    include_rolling: bool = False
    rolling_window: int = 60


class PerformanceMetricsResponse(BaseModel):
    """Performance metrics response."""
    portfolio_id: int
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: Optional[float] = None
    max_drawdown: float
    max_drawdown_duration_days: Optional[int] = None
    win_rate: Optional[float] = None
    profit_factor: Optional[float] = None
    period_start: datetime
    period_end: datetime


class RiskMetricsResponse(BaseModel):
    """Risk metrics response."""
    portfolio_id: int
    var_95: float
    var_99: float
    cvar_95: float
    beta: float
    alpha: float
    r_squared: float
    skewness: float
    kurtosis: float
    var_method: str
    period_start: datetime
    period_end: datetime


class BenchmarkComparisonResponse(BaseModel):
    """Benchmark comparison response."""
    portfolio_id: int
    benchmark_symbol: str
    portfolio_return: float
    benchmark_return: float
    excess_return: float
    alpha: float
    beta: float
    tracking_error: float
    information_ratio: float
    up_capture: float
    down_capture: float
    period_start: datetime
    period_end: datetime


class DrawdownResponse(BaseModel):
    """Drawdown analysis response."""
    portfolio_id: int
    current_drawdown: float
    max_drawdown: float
    max_drawdown_start: Optional[datetime] = None
    max_drawdown_end: Optional[datetime] = None
    recovery_date: Optional[datetime] = None
    drawdown_duration_days: Optional[int] = None


class RollingMetricsResponse(BaseModel):
    """Rolling metrics response."""
    portfolio_id: int
    window: int
    dates: List[datetime]
    returns: List[float]
    volatility: List[float]
    sharpe: List[float]


# ==================== Helper Functions ====================

def _get_date_range(time_range: TimeRange) -> tuple[datetime, datetime]:
    """Convert time range enum to actual dates."""
    end_date = datetime.now()
    
    if time_range == TimeRange.ONE_WEEK:
        start_date = end_date - timedelta(days=7)
    elif time_range == TimeRange.ONE_MONTH:
        start_date = end_date - timedelta(days=30)
    elif time_range == TimeRange.THREE_MONTHS:
        start_date = end_date - timedelta(days=90)
    elif time_range == TimeRange.SIX_MONTHS:
        start_date = end_date - timedelta(days=180)
    elif time_range == TimeRange.ONE_YEAR:
        start_date = end_date - timedelta(days=365)
    elif time_range == TimeRange.YTD:
        start_date = datetime(end_date.year, 1, 1)
    else:  # ALL
        start_date = datetime(2000, 1, 1)
    
    return start_date, end_date


async def _get_portfolio_returns(
    portfolio_id: int,
    start_date: datetime,
    end_date: datetime
) -> tuple[np.ndarray, List[datetime]]:
    """
    Get portfolio returns for the given period.
    In production, this would fetch from database.
    """
    # Placeholder - generate sample data for demonstration
    # In production, fetch from trades/positions database
    logger.info(f"Fetching returns for portfolio {portfolio_id} from {start_date} to {end_date}")
    
    days = (end_date - start_date).days
    if days <= 0:
        days = 252
    
    # Generate sample returns
    np.random.seed(portfolio_id)  # Reproducible for same portfolio
    returns = np.random.normal(0.0005, 0.015, days)
    dates = [start_date + timedelta(days=i) for i in range(days)]
    
    return returns, dates


async def _get_benchmark_returns(
    symbol: str,
    start_date: datetime,
    end_date: datetime
) -> np.ndarray:
    """
    Get benchmark returns for the given period.
    In production, this would fetch from market data provider.
    """
    days = (end_date - start_date).days
    if days <= 0:
        days = 252
    
    # Generate sample benchmark returns
    np.random.seed(hash(symbol) % 10000)
    returns = np.random.normal(0.0004, 0.012, days)
    
    return returns


# ==================== Performance Endpoints ====================

@router.get("/performance/{portfolio_id}", response_model=PerformanceMetricsResponse)
async def get_performance(
    portfolio_id: int,
    time_range: TimeRange = Query(TimeRange.ONE_YEAR),
    benchmark_symbol: str = Query("SPY")
):
    """
    Get portfolio performance metrics.
    
    Returns comprehensive performance analysis including:
    - Total and annualized returns
    - Risk-adjusted metrics (Sharpe, Sortino, Calmar)
    - Drawdown analysis
    - Win/loss statistics
    """
    try:
        start_date, end_date = _get_date_range(time_range)
        returns, dates = await _get_portfolio_returns(portfolio_id, start_date, end_date)
        
        analytics = get_performance_analytics()
        metrics = analytics.calculate_metrics(returns)
        
        return PerformanceMetricsResponse(
            portfolio_id=portfolio_id,
            total_return=metrics.total_return,
            annualized_return=metrics.annualized_return,
            volatility=metrics.volatility,
            sharpe_ratio=metrics.sharpe_ratio,
            sortino_ratio=metrics.sortino_ratio,
            calmar_ratio=metrics.calmar_ratio,
            max_drawdown=metrics.max_drawdown,
            max_drawdown_duration_days=metrics.max_drawdown_duration,
            win_rate=metrics.win_rate,
            profit_factor=metrics.profit_factor,
            period_start=start_date,
            period_end=end_date
        )
    
    except Exception as e:
        logger.error(f"Error calculating performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/performance/{portfolio_id}/detailed")
async def get_detailed_performance(
    portfolio_id: int,
    request: PerformanceRequest
):
    """
    Get detailed performance analysis with optional rolling metrics.
    """
    try:
        start_date, end_date = _get_date_range(request.time_range)
        returns, dates = await _get_portfolio_returns(portfolio_id, start_date, end_date)
        
        analytics = get_performance_analytics()
        metrics = analytics.calculate_metrics(returns)
        
        result = {
            "portfolio_id": portfolio_id,
            "metrics": {
                "total_return": metrics.total_return,
                "annualized_return": metrics.annualized_return,
                "volatility": metrics.volatility,
                "sharpe_ratio": metrics.sharpe_ratio,
                "sortino_ratio": metrics.sortino_ratio,
                "calmar_ratio": metrics.calmar_ratio,
                "max_drawdown": metrics.max_drawdown
            },
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            }
        }
        
        # Add drawdown analysis if requested
        if request.include_drawdown:
            drawdown = analytics.analyze_drawdowns(returns)
            result["drawdown"] = {
                "current": drawdown.current_drawdown,
                "maximum": drawdown.max_drawdown,
                "duration_days": drawdown.max_drawdown_duration
            }
        
        # Add rolling metrics if requested
        if request.include_rolling:
            rolling = analytics.calculate_rolling_metrics(
                returns, 
                window=request.rolling_window
            )
            result["rolling"] = {
                "window": request.rolling_window,
                "dates": [d.isoformat() for d in rolling.dates],
                "returns": rolling.returns,
                "volatility": rolling.volatility,
                "sharpe": rolling.sharpe
            }
        
        return result
    
    except Exception as e:
        logger.error(f"Error in detailed performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/{portfolio_id}/drawdown", response_model=DrawdownResponse)
async def get_drawdown_analysis(
    portfolio_id: int,
    time_range: TimeRange = Query(TimeRange.ONE_YEAR)
):
    """
    Get detailed drawdown analysis for portfolio.
    """
    try:
        start_date, end_date = _get_date_range(time_range)
        returns, dates = await _get_portfolio_returns(portfolio_id, start_date, end_date)
        
        analytics = get_performance_analytics()
        drawdown = analytics.analyze_drawdowns(returns, dates)
        
        return DrawdownResponse(
            portfolio_id=portfolio_id,
            current_drawdown=drawdown.current_drawdown,
            max_drawdown=drawdown.max_drawdown,
            max_drawdown_start=drawdown.max_drawdown_start,
            max_drawdown_end=drawdown.max_drawdown_end,
            recovery_date=drawdown.recovery_date,
            drawdown_duration_days=drawdown.max_drawdown_duration
        )
    
    except Exception as e:
        logger.error(f"Error in drawdown analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Risk Metrics Endpoints ====================

@router.get("/risk/{portfolio_id}", response_model=RiskMetricsResponse)
async def get_risk_metrics(
    portfolio_id: int,
    time_range: TimeRange = Query(TimeRange.ONE_YEAR),
    var_method: str = Query("historical")
):
    """
    Get risk metrics (VaR, Beta, etc.) for portfolio.
    """
    try:
        start_date, end_date = _get_date_range(time_range)
        returns, dates = await _get_portfolio_returns(portfolio_id, start_date, end_date)
        benchmark_returns = await _get_benchmark_returns("SPY", start_date, end_date)
        
        risk_calc = get_risk_metrics_calculator()
        
        # Calculate VaR
        method = VaRMethod(var_method) if var_method in ['historical', 'parametric', 'monte_carlo'] else VaRMethod.HISTORICAL
        var_95 = risk_calc.calculate_var(returns, confidence=0.95, method=method)
        var_99 = risk_calc.calculate_var(returns, confidence=0.99, method=method)
        cvar_95 = risk_calc.calculate_cvar(returns, confidence=0.95)
        
        # Calculate Beta
        beta_analysis = risk_calc.calculate_beta(returns, benchmark_returns)
        
        # Calculate tail risk
        tail_risk = risk_calc.calculate_tail_risk(returns)
        
        return RiskMetricsResponse(
            portfolio_id=portfolio_id,
            var_95=var_95.var_value,
            var_99=var_99.var_value,
            cvar_95=cvar_95,
            beta=beta_analysis.beta,
            alpha=beta_analysis.alpha,
            r_squared=beta_analysis.r_squared,
            skewness=tail_risk.skewness,
            kurtosis=tail_risk.kurtosis,
            var_method=method.value,
            period_start=start_date,
            period_end=end_date
        )
    
    except Exception as e:
        logger.error(f"Error calculating risk metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/risk/{portfolio_id}/detailed")
async def get_detailed_risk_metrics(
    portfolio_id: int,
    request: RiskMetricsRequest
):
    """
    Get detailed risk analysis with factor decomposition.
    """
    try:
        start_date, end_date = _get_date_range(request.time_range)
        returns, dates = await _get_portfolio_returns(portfolio_id, start_date, end_date)
        benchmark_returns = await _get_benchmark_returns("SPY", start_date, end_date)
        
        risk_calc = get_risk_metrics_calculator()
        
        # Basic risk metrics
        method = VaRMethod(request.var_method) if request.var_method in ['historical', 'parametric', 'monte_carlo'] else VaRMethod.HISTORICAL
        var_result = risk_calc.calculate_var(returns, confidence=request.var_confidence, method=method)
        
        result = {
            "portfolio_id": portfolio_id,
            "var": {
                "value": var_result.var_value,
                "confidence": var_result.confidence,
                "method": var_result.method.value,
                "holding_period": var_result.holding_period
            },
            "cvar": risk_calc.calculate_cvar(returns, confidence=request.var_confidence),
            "beta_analysis": risk_calc.calculate_beta(returns, benchmark_returns).to_dict(),
            "tail_risk": risk_calc.calculate_tail_risk(returns).to_dict(),
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            }
        }
        
        # Add factor analysis if requested
        if request.include_factor_analysis:
            # Generate sample factor returns
            factor_returns = {
                "market": benchmark_returns,
                "size": np.random.normal(0.0001, 0.005, len(returns)),
                "value": np.random.normal(0.0001, 0.005, len(returns)),
                "momentum": np.random.normal(0.0001, 0.006, len(returns))
            }
            factor_exposure = risk_calc.calculate_factor_exposure(returns, factor_returns)
            result["factor_exposure"] = factor_exposure.to_dict()
        
        # Add stress test if requested
        if request.include_stress_test:
            stress_scenarios = {
                "market_crash": -0.20,
                "mild_correction": -0.10,
                "volatility_spike": -0.15,
                "rate_hike": -0.05
            }
            stress_test = risk_calc.stress_test(returns, benchmark_returns, stress_scenarios)
            result["stress_test"] = [st.to_dict() for st in stress_test]
        
        return result
    
    except Exception as e:
        logger.error(f"Error in detailed risk analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/risk/{portfolio_id}/var-history")
async def get_var_history(
    portfolio_id: int,
    time_range: TimeRange = Query(TimeRange.ONE_YEAR),
    window: int = Query(60, ge=20, le=252),
    confidence: float = Query(0.95, ge=0.9, le=0.99)
):
    """
    Get historical VaR series for portfolio.
    """
    try:
        start_date, end_date = _get_date_range(time_range)
        returns, dates = await _get_portfolio_returns(portfolio_id, start_date, end_date)
        
        risk_calc = get_risk_metrics_calculator()
        
        # Calculate rolling VaR
        var_series = []
        var_dates = []
        
        for i in range(window - 1, len(returns)):
            window_returns = returns[i - window + 1:i + 1]
            var_result = risk_calc.calculate_var(window_returns, confidence=confidence)
            var_series.append(var_result.var_value)
            if i < len(dates):
                var_dates.append(dates[i].isoformat())
        
        return {
            "portfolio_id": portfolio_id,
            "window": window,
            "confidence": confidence,
            "dates": var_dates,
            "var_values": var_series
        }
    
    except Exception as e:
        logger.error(f"Error calculating VaR history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Benchmark Endpoints ====================

@router.get("/benchmark/{portfolio_id}", response_model=BenchmarkComparisonResponse)
async def compare_benchmark(
    portfolio_id: int,
    benchmark: str = Query("SPY"),
    time_range: TimeRange = Query(TimeRange.ONE_YEAR)
):
    """
    Compare portfolio to benchmark.
    """
    try:
        start_date, end_date = _get_date_range(time_range)
        returns, dates = await _get_portfolio_returns(portfolio_id, start_date, end_date)
        benchmark_returns = await _get_benchmark_returns(benchmark, start_date, end_date)
        
        benchmark_service = get_benchmark_service()
        comparison = benchmark_service.compare_to_benchmark(returns, benchmark_returns, dates=dates)
        
        return BenchmarkComparisonResponse(
            portfolio_id=portfolio_id,
            benchmark_symbol=benchmark,
            portfolio_return=comparison.portfolio_return,
            benchmark_return=comparison.benchmark_return,
            excess_return=comparison.excess_return,
            alpha=comparison.alpha,
            beta=comparison.beta,
            tracking_error=comparison.tracking_error,
            information_ratio=comparison.information_ratio,
            up_capture=comparison.up_capture,
            down_capture=comparison.down_capture,
            period_start=start_date,
            period_end=end_date
        )
    
    except Exception as e:
        logger.error(f"Error comparing benchmark: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/benchmark/{portfolio_id}/multi")
async def compare_multiple_benchmarks(
    portfolio_id: int,
    request: BenchmarkRequest
):
    """
    Compare portfolio to multiple benchmarks.
    """
    try:
        start_date, end_date = _get_date_range(request.time_range)
        returns, dates = await _get_portfolio_returns(portfolio_id, start_date, end_date)
        
        benchmark_service = get_benchmark_service()
        
        # Fetch all benchmark returns
        benchmark_data = {}
        for symbol in request.benchmark_symbols:
            benchmark_data[symbol] = await _get_benchmark_returns(symbol, start_date, end_date)
        
        # Compare to all benchmarks
        comparisons = benchmark_service.compare_to_multiple_benchmarks(returns, benchmark_data, dates)
        
        result = {
            "portfolio_id": portfolio_id,
            "comparisons": [c.to_dict() for c in comparisons],
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            }
        }
        
        # Add rolling metrics if requested
        if request.include_rolling and request.benchmark_symbols:
            primary_benchmark = request.benchmark_symbols[0]
            rolling = benchmark_service.calculate_rolling_comparison(
                returns,
                benchmark_data[primary_benchmark],
                window=request.rolling_window,
                dates=dates
            )
            result["rolling"] = {
                metric: rm.to_dict() for metric, rm in rolling.items()
            }
        
        return result
    
    except Exception as e:
        logger.error(f"Error in multi-benchmark comparison: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/benchmark/list")
async def list_available_benchmarks():
    """
    List available benchmarks for comparison.
    """
    benchmark_service = get_benchmark_service()
    return {
        "benchmarks": [b.to_dict() for b in benchmark_service.STANDARD_BENCHMARKS.values()]
    }


# ==================== Attribution Endpoints ====================

@router.get("/attribution/{portfolio_id}")
async def get_return_attribution(
    portfolio_id: int,
    time_range: TimeRange = Query(TimeRange.ONE_YEAR)
):
    """
    Get return attribution analysis.
    """
    try:
        start_date, end_date = _get_date_range(time_range)
        returns, dates = await _get_portfolio_returns(portfolio_id, start_date, end_date)
        
        analytics = get_performance_analytics()
        
        # Sample weights and asset returns for demonstration
        # In production, fetch from portfolio positions
        weights = np.array([0.4, 0.3, 0.2, 0.1])
        asset_returns = np.random.normal(0.0004, 0.012, (4, len(returns)))
        benchmark_weights = np.array([0.25, 0.25, 0.25, 0.25])
        
        attribution = analytics.calculate_attribution(
            weights=weights,
            returns=asset_returns,
            benchmark_weights=benchmark_weights
        )
        
        return {
            "portfolio_id": portfolio_id,
            "attribution": attribution.to_dict() if attribution else None,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            }
        }
    
    except Exception as e:
        logger.error(f"Error in return attribution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Summary Endpoints ====================

@router.get("/summary/{portfolio_id}")
async def get_analytics_summary(
    portfolio_id: int,
    time_range: TimeRange = Query(TimeRange.ONE_YEAR),
    benchmark: str = Query("SPY")
):
    """
    Get comprehensive analytics summary for portfolio.
    
    Combines performance, risk, and benchmark metrics in one response.
    """
    try:
        start_date, end_date = _get_date_range(time_range)
        returns, dates = await _get_portfolio_returns(portfolio_id, start_date, end_date)
        benchmark_returns = await _get_benchmark_returns(benchmark, start_date, end_date)
        
        analytics = get_performance_analytics()
        risk_calc = get_risk_metrics_calculator()
        benchmark_service = get_benchmark_service()
        
        # Calculate all metrics
        perf_metrics = analytics.calculate_metrics(returns)
        drawdown = analytics.analyze_drawdowns(returns, dates)
        var_result = risk_calc.calculate_var(returns, confidence=0.95)
        beta_analysis = risk_calc.calculate_beta(returns, benchmark_returns)
        benchmark_comparison = benchmark_service.compare_to_benchmark(returns, benchmark_returns, dates=dates)
        
        return {
            "portfolio_id": portfolio_id,
            "summary": {
                "performance": {
                    "total_return": perf_metrics.total_return,
                    "annualized_return": perf_metrics.annualized_return,
                    "volatility": perf_metrics.volatility,
                    "sharpe_ratio": perf_metrics.sharpe_ratio,
                    "sortino_ratio": perf_metrics.sortino_ratio,
                    "max_drawdown": perf_metrics.max_drawdown
                },
                "risk": {
                    "var_95": var_result.var_value,
                    "beta": beta_analysis.beta,
                    "alpha": beta_analysis.alpha,
                    "r_squared": beta_analysis.r_squared
                },
                "benchmark": {
                    "symbol": benchmark,
                    "excess_return": benchmark_comparison.excess_return,
                    "tracking_error": benchmark_comparison.tracking_error,
                    "information_ratio": benchmark_comparison.information_ratio,
                    "up_capture": benchmark_comparison.up_capture,
                    "down_capture": benchmark_comparison.down_capture
                },
                "drawdown": {
                    "current": drawdown.current_drawdown,
                    "maximum": drawdown.max_drawdown,
                    "duration_days": drawdown.max_drawdown_duration
                }
            },
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "range": time_range.value
            }
        }
    
    except Exception as e:
        logger.error(f"Error generating analytics summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
