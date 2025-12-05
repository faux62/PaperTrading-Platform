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
    RiskMetrics,
    VaRResult,
    VaRMethod,
    BetaAnalysis,
    CorrelationAnalysis,
    StressTestResult,
    RiskSummary,
    get_risk_metrics
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
from .reporting import (
    ReportGenerator,
    Report,
    ReportSection,
    ReportSchedule,
    ReportType,
    ReportFormat,
    ReportFrequency,
    get_report_generator
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
    'RiskMetrics',
    'VaRResult',
    'VaRMethod',
    'BetaAnalysis',
    'CorrelationAnalysis',
    'StressTestResult',
    'RiskSummary',
    'get_risk_metrics',
    # Benchmarking
    'BenchmarkService',
    'BenchmarkInfo',
    'BenchmarkType',
    'BenchmarkComparison',
    'RollingBenchmarkMetric',
    'PeerGroupComparison',
    'get_benchmark_service',
    # Reporting
    'ReportGenerator',
    'Report',
    'ReportSection',
    'ReportSchedule',
    'ReportType',
    'ReportFormat',
    'ReportFrequency',
    'get_report_generator'
]
