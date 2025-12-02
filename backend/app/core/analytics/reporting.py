"""
Automated Reporting Service

Generates scheduled and on-demand reports:
- Daily/Weekly/Monthly performance reports
- Risk summaries
- Benchmark comparisons
- Custom report templates
"""
import numpy as np
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from loguru import logger
import json


class ReportFrequency(str, Enum):
    """Report generation frequency."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    ON_DEMAND = "on_demand"


class ReportFormat(str, Enum):
    """Report output format."""
    JSON = "json"
    HTML = "html"
    PDF = "pdf"
    CSV = "csv"
    MARKDOWN = "markdown"


class ReportType(str, Enum):
    """Type of report."""
    PERFORMANCE = "performance"
    RISK = "risk"
    BENCHMARK = "benchmark"
    TRADE_SUMMARY = "trade_summary"
    POSITION_SUMMARY = "position_summary"
    COMPREHENSIVE = "comprehensive"


@dataclass
class ReportSection:
    """A section of a report."""
    title: str
    content: Dict[str, Any]
    section_type: str
    order: int = 0
    
    def to_dict(self) -> dict:
        return {
            'title': self.title,
            'content': self.content,
            'section_type': self.section_type,
            'order': self.order
        }


@dataclass
class Report:
    """Generated report."""
    report_id: str
    report_type: ReportType
    title: str
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    sections: List[ReportSection] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            'report_id': self.report_id,
            'report_type': self.report_type.value,
            'title': self.title,
            'generated_at': self.generated_at.isoformat(),
            'period_start': self.period_start.isoformat(),
            'period_end': self.period_end.isoformat(),
            'sections': [s.to_dict() for s in self.sections],
            'metadata': self.metadata
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)
    
    def to_markdown(self) -> str:
        """Convert report to Markdown format."""
        md = f"# {self.title}\n\n"
        md += f"**Generated:** {self.generated_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        md += f"**Period:** {self.period_start.strftime('%Y-%m-%d')} to {self.period_end.strftime('%Y-%m-%d')}\n\n"
        md += "---\n\n"
        
        for section in sorted(self.sections, key=lambda s: s.order):
            md += f"## {section.title}\n\n"
            md += self._format_section_content(section.content)
            md += "\n\n"
        
        return md
    
    def _format_section_content(self, content: Dict[str, Any], indent: int = 0) -> str:
        """Format section content as Markdown."""
        lines = []
        prefix = "  " * indent
        
        for key, value in content.items():
            if isinstance(value, dict):
                lines.append(f"{prefix}**{key}:**")
                lines.append(self._format_section_content(value, indent + 1))
            elif isinstance(value, list):
                lines.append(f"{prefix}**{key}:**")
                for item in value:
                    if isinstance(item, dict):
                        lines.append(self._format_section_content(item, indent + 1))
                    else:
                        lines.append(f"{prefix}  - {item}")
            elif isinstance(value, float):
                lines.append(f"{prefix}- **{key}:** {value:.4f}")
            else:
                lines.append(f"{prefix}- **{key}:** {value}")
        
        return "\n".join(lines)
    
    def to_html(self) -> str:
        """Convert report to HTML format."""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{self.title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #666; border-bottom: 1px solid #ddd; padding-bottom: 5px; }}
        .meta {{ color: #888; margin-bottom: 20px; }}
        .section {{ margin-bottom: 30px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f4f4f4; }}
        .positive {{ color: green; }}
        .negative {{ color: red; }}
    </style>
</head>
<body>
    <h1>{self.title}</h1>
    <div class="meta">
        <p>Generated: {self.generated_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Period: {self.period_start.strftime('%Y-%m-%d')} to {self.period_end.strftime('%Y-%m-%d')}</p>
    </div>
"""
        
        for section in sorted(self.sections, key=lambda s: s.order):
            html += f'    <div class="section">\n'
            html += f'        <h2>{section.title}</h2>\n'
            html += self._format_html_content(section.content)
            html += '    </div>\n'
        
        html += """
</body>
</html>
"""
        return html
    
    def _format_html_content(self, content: Dict[str, Any]) -> str:
        """Format section content as HTML table."""
        html = '        <table>\n'
        
        for key, value in content.items():
            if isinstance(value, dict):
                html += f'            <tr><th colspan="2">{key}</th></tr>\n'
                for k, v in value.items():
                    formatted_value = self._format_html_value(v)
                    html += f'            <tr><td>{k}</td><td>{formatted_value}</td></tr>\n'
            elif isinstance(value, list):
                continue  # Skip lists for simple table format
            else:
                formatted_value = self._format_html_value(value)
                html += f'            <tr><td>{key}</td><td>{formatted_value}</td></tr>\n'
        
        html += '        </table>\n'
        return html
    
    def _format_html_value(self, value: Any) -> str:
        """Format a single value for HTML display."""
        if isinstance(value, float):
            if value > 0:
                return f'<span class="positive">{value:+.4f}</span>'
            elif value < 0:
                return f'<span class="negative">{value:.4f}</span>'
            return f'{value:.4f}'
        return str(value)


@dataclass
class ReportSchedule:
    """Report generation schedule."""
    schedule_id: str
    portfolio_id: int
    report_type: ReportType
    frequency: ReportFrequency
    format: ReportFormat = ReportFormat.JSON
    recipients: List[str] = field(default_factory=list)
    enabled: bool = True
    last_generated: Optional[datetime] = None
    next_scheduled: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        return {
            'schedule_id': self.schedule_id,
            'portfolio_id': self.portfolio_id,
            'report_type': self.report_type.value,
            'frequency': self.frequency.value,
            'format': self.format.value,
            'recipients': self.recipients,
            'enabled': self.enabled,
            'last_generated': self.last_generated.isoformat() if self.last_generated else None,
            'next_scheduled': self.next_scheduled.isoformat() if self.next_scheduled else None
        }


class ReportGenerator:
    """
    Report generation service.
    
    Generates various types of reports:
    - Performance reports
    - Risk reports
    - Benchmark comparisons
    - Comprehensive summaries
    """
    
    def __init__(self):
        self._schedules: Dict[str, ReportSchedule] = {}
        self._report_counter = 0
    
    def generate_performance_report(
        self,
        portfolio_id: int,
        returns: np.ndarray,
        start_date: datetime,
        end_date: datetime,
        metrics: Optional[Dict[str, float]] = None
    ) -> Report:
        """
        Generate performance report.
        
        Args:
            portfolio_id: Portfolio ID
            returns: Array of returns
            start_date: Report start date
            end_date: Report end date
            metrics: Pre-calculated metrics (optional)
            
        Returns:
            Generated Report
        """
        self._report_counter += 1
        report_id = f"PERF-{portfolio_id}-{self._report_counter}"
        
        # Calculate metrics if not provided
        if metrics is None:
            metrics = self._calculate_basic_metrics(returns)
        
        sections = []
        
        # Summary section
        sections.append(ReportSection(
            title="Performance Summary",
            content={
                "Total Return": metrics.get('total_return', 0),
                "Annualized Return": metrics.get('annualized_return', 0),
                "Volatility": metrics.get('volatility', 0),
                "Sharpe Ratio": metrics.get('sharpe_ratio', 0),
                "Sortino Ratio": metrics.get('sortino_ratio', 0)
            },
            section_type="summary",
            order=1
        ))
        
        # Drawdown section
        sections.append(ReportSection(
            title="Drawdown Analysis",
            content={
                "Maximum Drawdown": metrics.get('max_drawdown', 0),
                "Current Drawdown": metrics.get('current_drawdown', 0),
                "Drawdown Duration (days)": metrics.get('drawdown_duration', 0)
            },
            section_type="drawdown",
            order=2
        ))
        
        # Return distribution
        sections.append(ReportSection(
            title="Return Distribution",
            content={
                "Mean Daily Return": float(np.mean(returns)) if len(returns) > 0 else 0,
                "Median Daily Return": float(np.median(returns)) if len(returns) > 0 else 0,
                "Std Daily Return": float(np.std(returns)) if len(returns) > 0 else 0,
                "Best Day": float(np.max(returns)) if len(returns) > 0 else 0,
                "Worst Day": float(np.min(returns)) if len(returns) > 0 else 0,
                "Positive Days": int(np.sum(returns > 0)) if len(returns) > 0 else 0,
                "Negative Days": int(np.sum(returns < 0)) if len(returns) > 0 else 0
            },
            section_type="distribution",
            order=3
        ))
        
        return Report(
            report_id=report_id,
            report_type=ReportType.PERFORMANCE,
            title=f"Performance Report - Portfolio {portfolio_id}",
            generated_at=datetime.now(),
            period_start=start_date,
            period_end=end_date,
            sections=sections,
            metadata={"portfolio_id": portfolio_id}
        )
    
    def generate_risk_report(
        self,
        portfolio_id: int,
        returns: np.ndarray,
        start_date: datetime,
        end_date: datetime,
        risk_metrics: Optional[Dict[str, Any]] = None
    ) -> Report:
        """
        Generate risk report.
        
        Args:
            portfolio_id: Portfolio ID
            returns: Array of returns
            start_date: Report start date
            end_date: Report end date
            risk_metrics: Pre-calculated risk metrics (optional)
            
        Returns:
            Generated Report
        """
        self._report_counter += 1
        report_id = f"RISK-{portfolio_id}-{self._report_counter}"
        
        # Calculate risk metrics if not provided
        if risk_metrics is None:
            risk_metrics = self._calculate_basic_risk_metrics(returns)
        
        sections = []
        
        # VaR section
        sections.append(ReportSection(
            title="Value at Risk",
            content={
                "VaR (95%)": risk_metrics.get('var_95', 0),
                "VaR (99%)": risk_metrics.get('var_99', 0),
                "CVaR (95%)": risk_metrics.get('cvar_95', 0),
                "Method": risk_metrics.get('var_method', 'Historical')
            },
            section_type="var",
            order=1
        ))
        
        # Beta/Correlation section
        sections.append(ReportSection(
            title="Market Sensitivity",
            content={
                "Beta": risk_metrics.get('beta', 1.0),
                "Alpha (Annualized)": risk_metrics.get('alpha', 0),
                "R-Squared": risk_metrics.get('r_squared', 0),
                "Correlation to Market": risk_metrics.get('correlation', 0)
            },
            section_type="beta",
            order=2
        ))
        
        # Tail risk section
        sections.append(ReportSection(
            title="Tail Risk Metrics",
            content={
                "Skewness": risk_metrics.get('skewness', 0),
                "Kurtosis": risk_metrics.get('kurtosis', 0),
                "Jarque-Bera Statistic": risk_metrics.get('jarque_bera', 0)
            },
            section_type="tail_risk",
            order=3
        ))
        
        return Report(
            report_id=report_id,
            report_type=ReportType.RISK,
            title=f"Risk Report - Portfolio {portfolio_id}",
            generated_at=datetime.now(),
            period_start=start_date,
            period_end=end_date,
            sections=sections,
            metadata={"portfolio_id": portfolio_id}
        )
    
    def generate_benchmark_report(
        self,
        portfolio_id: int,
        returns: np.ndarray,
        benchmark_returns: np.ndarray,
        benchmark_name: str,
        start_date: datetime,
        end_date: datetime,
        comparison_metrics: Optional[Dict[str, Any]] = None
    ) -> Report:
        """
        Generate benchmark comparison report.
        
        Args:
            portfolio_id: Portfolio ID
            returns: Portfolio returns
            benchmark_returns: Benchmark returns
            benchmark_name: Name of benchmark
            start_date: Report start date
            end_date: Report end date
            comparison_metrics: Pre-calculated comparison metrics (optional)
            
        Returns:
            Generated Report
        """
        self._report_counter += 1
        report_id = f"BENCH-{portfolio_id}-{self._report_counter}"
        
        # Calculate comparison metrics if not provided
        if comparison_metrics is None:
            comparison_metrics = self._calculate_benchmark_comparison(returns, benchmark_returns)
        
        sections = []
        
        # Return comparison
        sections.append(ReportSection(
            title="Return Comparison",
            content={
                "Portfolio Return": comparison_metrics.get('portfolio_return', 0),
                f"{benchmark_name} Return": comparison_metrics.get('benchmark_return', 0),
                "Excess Return": comparison_metrics.get('excess_return', 0),
                "Tracking Error": comparison_metrics.get('tracking_error', 0)
            },
            section_type="returns",
            order=1
        ))
        
        # Risk-adjusted comparison
        sections.append(ReportSection(
            title="Risk-Adjusted Metrics",
            content={
                "Portfolio Sharpe": comparison_metrics.get('portfolio_sharpe', 0),
                f"{benchmark_name} Sharpe": comparison_metrics.get('benchmark_sharpe', 0),
                "Information Ratio": comparison_metrics.get('information_ratio', 0),
                "Alpha": comparison_metrics.get('alpha', 0),
                "Beta": comparison_metrics.get('beta', 1.0)
            },
            section_type="risk_adjusted",
            order=2
        ))
        
        # Capture ratios
        sections.append(ReportSection(
            title="Capture Ratios",
            content={
                "Up Capture": comparison_metrics.get('up_capture', 1.0),
                "Down Capture": comparison_metrics.get('down_capture', 1.0),
                "Capture Ratio": comparison_metrics.get('capture_ratio', 1.0)
            },
            section_type="capture",
            order=3
        ))
        
        return Report(
            report_id=report_id,
            report_type=ReportType.BENCHMARK,
            title=f"Benchmark Comparison Report - Portfolio {portfolio_id} vs {benchmark_name}",
            generated_at=datetime.now(),
            period_start=start_date,
            period_end=end_date,
            sections=sections,
            metadata={
                "portfolio_id": portfolio_id,
                "benchmark": benchmark_name
            }
        )
    
    def generate_comprehensive_report(
        self,
        portfolio_id: int,
        returns: np.ndarray,
        benchmark_returns: np.ndarray,
        benchmark_name: str,
        start_date: datetime,
        end_date: datetime,
        performance_metrics: Optional[Dict] = None,
        risk_metrics: Optional[Dict] = None,
        benchmark_metrics: Optional[Dict] = None
    ) -> Report:
        """
        Generate comprehensive report combining all analyses.
        
        Args:
            portfolio_id: Portfolio ID
            returns: Portfolio returns
            benchmark_returns: Benchmark returns
            benchmark_name: Name of benchmark
            start_date: Report start date
            end_date: Report end date
            performance_metrics: Pre-calculated performance metrics
            risk_metrics: Pre-calculated risk metrics
            benchmark_metrics: Pre-calculated benchmark metrics
            
        Returns:
            Generated comprehensive Report
        """
        self._report_counter += 1
        report_id = f"COMP-{portfolio_id}-{self._report_counter}"
        
        # Calculate all metrics if not provided
        if performance_metrics is None:
            performance_metrics = self._calculate_basic_metrics(returns)
        if risk_metrics is None:
            risk_metrics = self._calculate_basic_risk_metrics(returns)
        if benchmark_metrics is None:
            benchmark_metrics = self._calculate_benchmark_comparison(returns, benchmark_returns)
        
        sections = []
        
        # Executive summary
        sections.append(ReportSection(
            title="Executive Summary",
            content={
                "Total Return": performance_metrics.get('total_return', 0),
                "vs Benchmark": benchmark_metrics.get('excess_return', 0),
                "Sharpe Ratio": performance_metrics.get('sharpe_ratio', 0),
                "Max Drawdown": performance_metrics.get('max_drawdown', 0),
                "VaR (95%)": risk_metrics.get('var_95', 0)
            },
            section_type="executive_summary",
            order=0
        ))
        
        # Performance details
        sections.append(ReportSection(
            title="Performance Analysis",
            content={
                "Returns": {
                    "Total Return": performance_metrics.get('total_return', 0),
                    "Annualized Return": performance_metrics.get('annualized_return', 0),
                    "Best Month": performance_metrics.get('best_month', 0),
                    "Worst Month": performance_metrics.get('worst_month', 0)
                },
                "Risk-Adjusted": {
                    "Sharpe Ratio": performance_metrics.get('sharpe_ratio', 0),
                    "Sortino Ratio": performance_metrics.get('sortino_ratio', 0),
                    "Calmar Ratio": performance_metrics.get('calmar_ratio', 0)
                }
            },
            section_type="performance",
            order=1
        ))
        
        # Risk details
        sections.append(ReportSection(
            title="Risk Analysis",
            content={
                "Value at Risk": {
                    "VaR 95%": risk_metrics.get('var_95', 0),
                    "VaR 99%": risk_metrics.get('var_99', 0),
                    "CVaR 95%": risk_metrics.get('cvar_95', 0)
                },
                "Market Sensitivity": {
                    "Beta": risk_metrics.get('beta', 1.0),
                    "Alpha": risk_metrics.get('alpha', 0),
                    "R-Squared": risk_metrics.get('r_squared', 0)
                },
                "Distribution": {
                    "Volatility": performance_metrics.get('volatility', 0),
                    "Skewness": risk_metrics.get('skewness', 0),
                    "Kurtosis": risk_metrics.get('kurtosis', 0)
                }
            },
            section_type="risk",
            order=2
        ))
        
        # Benchmark comparison
        sections.append(ReportSection(
            title=f"Benchmark Comparison ({benchmark_name})",
            content={
                "Returns": {
                    "Portfolio Return": benchmark_metrics.get('portfolio_return', 0),
                    "Benchmark Return": benchmark_metrics.get('benchmark_return', 0),
                    "Excess Return": benchmark_metrics.get('excess_return', 0)
                },
                "Relative Metrics": {
                    "Tracking Error": benchmark_metrics.get('tracking_error', 0),
                    "Information Ratio": benchmark_metrics.get('information_ratio', 0),
                    "Up Capture": benchmark_metrics.get('up_capture', 1.0),
                    "Down Capture": benchmark_metrics.get('down_capture', 1.0)
                }
            },
            section_type="benchmark",
            order=3
        ))
        
        return Report(
            report_id=report_id,
            report_type=ReportType.COMPREHENSIVE,
            title=f"Comprehensive Report - Portfolio {portfolio_id}",
            generated_at=datetime.now(),
            period_start=start_date,
            period_end=end_date,
            sections=sections,
            metadata={
                "portfolio_id": portfolio_id,
                "benchmark": benchmark_name,
                "report_type": "comprehensive"
            }
        )
    
    def _calculate_basic_metrics(self, returns: np.ndarray) -> Dict[str, float]:
        """Calculate basic performance metrics."""
        returns = np.asarray(returns)
        if len(returns) == 0:
            return {}
        
        total_return = float(np.prod(1 + returns) - 1)
        annualized_return = float((1 + total_return) ** (252 / len(returns)) - 1) if len(returns) > 0 else 0
        volatility = float(np.std(returns) * np.sqrt(252))
        
        sharpe = 0
        if volatility > 0:
            sharpe = (annualized_return - 0.02) / volatility
        
        # Calculate drawdown
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = (cumulative - running_max) / running_max
        max_drawdown = float(np.min(drawdowns))
        current_drawdown = float(drawdowns[-1]) if len(drawdowns) > 0 else 0
        
        # Sortino
        downside = returns[returns < 0]
        downside_std = np.std(downside) * np.sqrt(252) if len(downside) > 0 else 0
        sortino = (annualized_return - 0.02) / downside_std if downside_std > 0 else 0
        
        # Calmar
        calmar = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        return {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'volatility': volatility,
            'sharpe_ratio': float(sharpe),
            'sortino_ratio': float(sortino),
            'calmar_ratio': float(calmar),
            'max_drawdown': max_drawdown,
            'current_drawdown': current_drawdown
        }
    
    def _calculate_basic_risk_metrics(self, returns: np.ndarray) -> Dict[str, float]:
        """Calculate basic risk metrics."""
        from scipy import stats
        
        returns = np.asarray(returns)
        if len(returns) == 0:
            return {}
        
        # VaR
        var_95 = float(np.percentile(returns, 5))
        var_99 = float(np.percentile(returns, 1))
        cvar_95 = float(np.mean(returns[returns <= var_95])) if len(returns[returns <= var_95]) > 0 else var_95
        
        # Distribution stats
        skewness = float(stats.skew(returns))
        kurtosis = float(stats.kurtosis(returns))
        jb_stat, jb_p = stats.jarque_bera(returns)
        
        return {
            'var_95': var_95,
            'var_99': var_99,
            'cvar_95': cvar_95,
            'skewness': skewness,
            'kurtosis': kurtosis,
            'jarque_bera': float(jb_stat),
            'var_method': 'Historical'
        }
    
    def _calculate_benchmark_comparison(
        self,
        returns: np.ndarray,
        benchmark_returns: np.ndarray
    ) -> Dict[str, float]:
        """Calculate benchmark comparison metrics."""
        returns = np.asarray(returns)
        benchmark_returns = np.asarray(benchmark_returns)
        
        min_len = min(len(returns), len(benchmark_returns))
        returns = returns[-min_len:]
        benchmark_returns = benchmark_returns[-min_len:]
        
        port_total = float(np.prod(1 + returns) - 1)
        bench_total = float(np.prod(1 + benchmark_returns) - 1)
        excess = port_total - bench_total
        
        # Volatility
        port_vol = float(np.std(returns) * np.sqrt(252))
        bench_vol = float(np.std(benchmark_returns) * np.sqrt(252))
        
        # Annualized returns
        port_ann = float((1 + port_total) ** (252 / min_len) - 1) if min_len > 0 else 0
        bench_ann = float((1 + bench_total) ** (252 / min_len) - 1) if min_len > 0 else 0
        
        # Sharpe
        port_sharpe = (port_ann - 0.02) / port_vol if port_vol > 0 else 0
        bench_sharpe = (bench_ann - 0.02) / bench_vol if bench_vol > 0 else 0
        
        # Beta
        cov = np.cov(returns, benchmark_returns)[0, 1]
        var = np.var(benchmark_returns)
        beta = cov / var if var > 0 else 1.0
        alpha = port_ann - 0.02 - beta * (bench_ann - 0.02)
        
        # R-squared
        corr = np.corrcoef(returns, benchmark_returns)[0, 1]
        r_squared = corr ** 2
        
        # Tracking error
        tracking_diff = returns - benchmark_returns
        tracking_error = float(np.std(tracking_diff) * np.sqrt(252))
        
        # Information ratio
        info_ratio = (np.mean(tracking_diff) * 252) / tracking_error if tracking_error > 0 else 0
        
        # Capture ratios
        up_market = benchmark_returns > 0
        down_market = benchmark_returns < 0
        
        up_capture = 1.0
        if np.any(up_market) and np.mean(benchmark_returns[up_market]) != 0:
            up_capture = np.mean(returns[up_market]) / np.mean(benchmark_returns[up_market])
        
        down_capture = 1.0
        if np.any(down_market) and np.mean(benchmark_returns[down_market]) != 0:
            down_capture = np.mean(returns[down_market]) / np.mean(benchmark_returns[down_market])
        
        return {
            'portfolio_return': port_total,
            'benchmark_return': bench_total,
            'excess_return': excess,
            'portfolio_sharpe': float(port_sharpe),
            'benchmark_sharpe': float(bench_sharpe),
            'tracking_error': tracking_error,
            'information_ratio': float(info_ratio),
            'alpha': float(alpha),
            'beta': float(beta),
            'r_squared': float(r_squared),
            'up_capture': float(up_capture),
            'down_capture': float(down_capture),
            'capture_ratio': float(up_capture / down_capture) if down_capture != 0 else 1.0
        }
    
    # Schedule Management
    
    def create_schedule(
        self,
        portfolio_id: int,
        report_type: ReportType,
        frequency: ReportFrequency,
        format: ReportFormat = ReportFormat.JSON,
        recipients: Optional[List[str]] = None
    ) -> ReportSchedule:
        """Create a new report schedule."""
        schedule_id = f"SCHED-{portfolio_id}-{len(self._schedules) + 1}"
        
        schedule = ReportSchedule(
            schedule_id=schedule_id,
            portfolio_id=portfolio_id,
            report_type=report_type,
            frequency=frequency,
            format=format,
            recipients=recipients or [],
            enabled=True,
            next_scheduled=self._calculate_next_run(frequency)
        )
        
        self._schedules[schedule_id] = schedule
        logger.info(f"Created report schedule: {schedule_id}")
        
        return schedule
    
    def _calculate_next_run(self, frequency: ReportFrequency) -> datetime:
        """Calculate next scheduled run time."""
        now = datetime.now()
        
        if frequency == ReportFrequency.DAILY:
            return now.replace(hour=6, minute=0, second=0) + timedelta(days=1)
        elif frequency == ReportFrequency.WEEKLY:
            days_until_monday = (7 - now.weekday()) % 7 or 7
            return now.replace(hour=6, minute=0, second=0) + timedelta(days=days_until_monday)
        elif frequency == ReportFrequency.MONTHLY:
            if now.month == 12:
                return now.replace(year=now.year + 1, month=1, day=1, hour=6, minute=0, second=0)
            return now.replace(month=now.month + 1, day=1, hour=6, minute=0, second=0)
        elif frequency == ReportFrequency.QUARTERLY:
            current_quarter = (now.month - 1) // 3
            next_quarter_month = ((current_quarter + 1) % 4) * 3 + 1
            year = now.year if next_quarter_month > now.month else now.year + 1
            return datetime(year, next_quarter_month, 1, 6, 0, 0)
        elif frequency == ReportFrequency.YEARLY:
            return now.replace(year=now.year + 1, month=1, day=1, hour=6, minute=0, second=0)
        
        return now
    
    def get_schedule(self, schedule_id: str) -> Optional[ReportSchedule]:
        """Get a report schedule by ID."""
        return self._schedules.get(schedule_id)
    
    def list_schedules(
        self,
        portfolio_id: Optional[int] = None
    ) -> List[ReportSchedule]:
        """List all report schedules."""
        schedules = list(self._schedules.values())
        if portfolio_id is not None:
            schedules = [s for s in schedules if s.portfolio_id == portfolio_id]
        return schedules
    
    def update_schedule(
        self,
        schedule_id: str,
        enabled: Optional[bool] = None,
        frequency: Optional[ReportFrequency] = None,
        recipients: Optional[List[str]] = None
    ) -> Optional[ReportSchedule]:
        """Update a report schedule."""
        schedule = self._schedules.get(schedule_id)
        if not schedule:
            return None
        
        if enabled is not None:
            schedule.enabled = enabled
        if frequency is not None:
            schedule.frequency = frequency
            schedule.next_scheduled = self._calculate_next_run(frequency)
        if recipients is not None:
            schedule.recipients = recipients
        
        return schedule
    
    def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a report schedule."""
        if schedule_id in self._schedules:
            del self._schedules[schedule_id]
            return True
        return False


# Global instance
_report_generator: Optional[ReportGenerator] = None


def get_report_generator() -> ReportGenerator:
    """Get or create global report generator instance."""
    global _report_generator
    if _report_generator is None:
        _report_generator = ReportGenerator()
    return _report_generator
