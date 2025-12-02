"""
Analytics Package

Contains analytics services:
- Performance analytics
- Risk metrics
- Benchmarking
- Reporting
"""
from .performance import (
    PerformanceAnalytics,
    PerformanceMetrics,
    PeriodReturn,
    AttributionResult,
    ReturnType,
    get_performance_analytics
)
from .risk_metrics import (
    RiskMetricsCalculator,
    VaRResult,
    VaRMethod,
    BetaAnalysis,
    FactorExposure,
    CorrelationAnalysis,
    TailRiskMetrics,
    StressTestResult,
    get_risk_metrics_calculator
)
from .benchmarking import (
    BenchmarkService,
    BenchmarkInfo,
    BenchmarkType,
    BenchmarkComparison,
    RollingBenchmarkMetric,
    PeerGroupComparison,
    get_benchmark_service
)

__all__ = [
    # Performance
    'PerformanceAnalytics',
    'PerformanceMetrics',
    'PeriodReturn',
    'AttributionResult',
    'ReturnType',
    'get_performance_analytics',
    # Risk Metrics
    'RiskMetricsCalculator',
    'VaRResult',
    'VaRMethod',
    'BetaAnalysis',
    'FactorExposure',
    'CorrelationAnalysis',
    'TailRiskMetrics',
    'StressTestResult',
    'get_risk_metrics_calculator',
    # Benchmarking
    'BenchmarkService',
    'BenchmarkInfo',
    'BenchmarkType',
    'BenchmarkComparison',
    'RollingBenchmarkMetric',
    'PeerGroupComparison',
    'get_benchmark_service'
]
