/**
 * Analytics Page
 * 
 * Comprehensive portfolio analytics dashboard:
 * - Performance metrics
 * - Risk analysis
 * - Benchmark comparison
 * - Interactive charts
 */
import React, { useState, useMemo } from 'react';
import { Layout } from '../components/layout';
import { Card } from '../components/common';
import { 
  BarChart3, 
  TrendingUp, 
  ShieldAlert, 
  Target,
  RefreshCw,
} from 'lucide-react';

import { ChartContainer } from '../components/charts/ChartContainer';
import { PerformanceChart } from '../components/charts/PerformanceChart';
import { AllocationChart } from '../components/charts/AllocationChart';
import { DrawdownChart } from '../components/charts/DrawdownChart';
import { RiskChart } from '../components/charts/RiskChart';

import { 
  MetricsCard,
  PerformanceMetrics, 
  RiskMetrics,
  BenchmarkComparison,
  TimeRangeSelector,
} from '../components/analytics';

type TimeRange = '1W' | '1M' | '3M' | '6M' | '1Y' | 'YTD' | 'ALL';

// Generate sample data for demonstration
const generateSampleData = (days: number, startValue: number = 100000) => {
  const performance = [];
  const drawdown = [];
  const risk = [];
  
  let value = startValue;
  let benchmarkValue = startValue;
  let peak = startValue;
  
  const startDate = new Date();
  startDate.setDate(startDate.getDate() - days);
  
  for (let i = 0; i < days; i++) {
    const date = new Date(startDate);
    date.setDate(date.getDate() + i);
    const dateStr = date.toISOString().split('T')[0];
    
    // Random daily returns
    const dailyReturn = (Math.random() - 0.48) * 0.03;
    const benchmarkReturn = (Math.random() - 0.48) * 0.02;
    
    value *= (1 + dailyReturn);
    benchmarkValue *= (1 + benchmarkReturn);
    
    peak = Math.max(peak, value);
    const currentDrawdown = (value - peak) / peak;
    
    performance.push({
      date: dateStr,
      value: Math.round(value),
      benchmark: Math.round(benchmarkValue),
    });
    
    drawdown.push({
      date: dateStr,
      drawdown: currentDrawdown,
      peak: Math.round(peak),
      value: Math.round(value),
    });
    
    // VaR and risk data (simulated)
    const var95 = -Math.abs(dailyReturn) * 2 - 0.01;
    const var99 = var95 * 1.5;
    
    risk.push({
      date: dateStr,
      var95: var95,
      var99: var99,
      cvar: var95 * 1.3,
      volatility: 0.15 + Math.random() * 0.1,
    });
  }
  
  return { performance, drawdown, risk };
};

// Sample allocation data
const allocationData = [
  { name: 'US Equities', value: 45000, color: '#3b82f6' },
  { name: 'International', value: 25000, color: '#10b981' },
  { name: 'Bonds', value: 15000, color: '#f59e0b' },
  { name: 'Real Estate', value: 10000, color: '#8b5cf6' },
  { name: 'Cash', value: 5000, color: '#6b7280' },
];

const Analytics: React.FC = () => {
  const [timeRange, setTimeRange] = useState<TimeRange>('1Y');
  const [isLoading, setIsLoading] = useState(false);
  const [selectedPortfolio] = useState(1);

  // Get number of days from time range
  const getDays = (range: TimeRange): number => {
    switch (range) {
      case '1W': return 7;
      case '1M': return 30;
      case '3M': return 90;
      case '6M': return 180;
      case '1Y': return 365;
      case 'YTD': {
        const now = new Date();
        const start = new Date(now.getFullYear(), 0, 1);
        return Math.floor((now.getTime() - start.getTime()) / (1000 * 60 * 60 * 24));
      }
      case 'ALL': return 730;
      default: return 365;
    }
  };

  // Generate data based on time range
  const { performance, drawdown, risk } = useMemo(() => {
    return generateSampleData(getDays(timeRange));
  }, [timeRange]);

  // Calculate performance metrics from data
  const performanceMetrics = useMemo(() => {
    if (performance.length < 2) return null;
    
    const startValue = performance[0].value;
    const endValue = performance[performance.length - 1].value;
    const totalReturn = (endValue - startValue) / startValue;
    
    // Annualize return
    const days = performance.length;
    const annualizedReturn = Math.pow(1 + totalReturn, 365 / days) - 1;
    
    // Calculate volatility
    const returns = [];
    for (let i = 1; i < performance.length; i++) {
      returns.push((performance[i].value - performance[i-1].value) / performance[i-1].value);
    }
    const avgReturn = returns.reduce((a, b) => a + b, 0) / returns.length;
    const variance = returns.reduce((sum, r) => sum + Math.pow(r - avgReturn, 2), 0) / returns.length;
    const dailyVol = Math.sqrt(variance);
    const annualizedVol = dailyVol * Math.sqrt(252);
    
    // Max drawdown
    const maxDD = Math.min(...drawdown.map(d => d.drawdown));
    
    // Risk-adjusted metrics
    const riskFreeRate = 0.02;
    const sharpe = (annualizedReturn - riskFreeRate) / annualizedVol;
    
    // Sortino (using only downside deviation)
    const negativeReturns = returns.filter(r => r < 0);
    const downsideDeviation = negativeReturns.length > 0 
      ? Math.sqrt(negativeReturns.reduce((sum, r) => sum + r * r, 0) / negativeReturns.length) * Math.sqrt(252)
      : annualizedVol;
    const sortino = (annualizedReturn - riskFreeRate) / downsideDeviation;
    
    // Calmar
    const calmar = maxDD !== 0 ? annualizedReturn / Math.abs(maxDD) : 0;
    
    // Win rate
    const winningDays = returns.filter(r => r > 0).length;
    const winRate = winningDays / returns.length;
    
    return {
      totalReturn,
      annualizedReturn,
      volatility: annualizedVol,
      sharpeRatio: sharpe,
      sortinoRatio: sortino,
      calmarRatio: calmar,
      maxDrawdown: maxDD,
      winRate,
    };
  }, [performance, drawdown]);

  // Sample risk metrics
  const riskData = {
    var95: risk.length > 0 ? risk[risk.length - 1].var95 : -0.02,
    var99: risk.length > 0 ? risk[risk.length - 1].var99 : -0.03,
    cvar95: risk.length > 0 ? risk[risk.length - 1].cvar! : -0.025,
    beta: 1.05,
    alpha: 0.02,
    rSquared: 0.85,
    skewness: -0.3,
    kurtosis: 3.5,
  };

  // Sample benchmark comparison
  const benchmarkData = {
    benchmarkSymbol: 'SPY',
    portfolioReturn: performanceMetrics?.totalReturn ?? 0,
    benchmarkReturn: performance.length > 0 
      ? (performance[performance.length - 1].benchmark - performance[0].benchmark) / performance[0].benchmark
      : 0,
    excessReturn: 0,
    alpha: 0.02,
    beta: 1.05,
    trackingError: 0.05,
    informationRatio: 0.4,
    upCapture: 1.1,
    downCapture: 0.9,
  };
  benchmarkData.excessReturn = benchmarkData.portfolioReturn - benchmarkData.benchmarkReturn;

  const handleRefresh = () => {
    setIsLoading(true);
    setTimeout(() => setIsLoading(false), 1000);
  };

  return (
    <Layout title="Analytics">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <BarChart3 className="w-7 h-7 text-blue-600" />
            Portfolio Analytics
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Comprehensive performance and risk analysis
          </p>
        </div>
        
        <div className="flex items-center gap-4">
          <TimeRangeSelector value={timeRange} onChange={setTimeRange} />
          <button
            onClick={handleRefresh}
            disabled={isLoading}
            className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
          >
            <RefreshCw className={`w-5 h-5 text-gray-600 dark:text-gray-400 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <MetricsCard
          label="Total Return"
          value={performanceMetrics?.totalReturn ?? 0}
          format="percent"
          icon={<TrendingUp className="w-5 h-5 text-blue-600" />}
          trend={performanceMetrics?.totalReturn && performanceMetrics.totalReturn >= 0 ? 'up' : 'down'}
          size="lg"
        />
        <MetricsCard
          label="Sharpe Ratio"
          value={performanceMetrics?.sharpeRatio ?? 0}
          format="number"
          icon={<Target className="w-5 h-5 text-purple-600" />}
          description={performanceMetrics?.sharpeRatio && performanceMetrics.sharpeRatio >= 1 ? 'Good' : 'Below average'}
          size="lg"
        />
        <MetricsCard
          label="Max Drawdown"
          value={performanceMetrics?.maxDrawdown ?? 0}
          format="percent"
          icon={<ShieldAlert className="w-5 h-5 text-red-600" />}
          trend="down"
          size="lg"
        />
        <MetricsCard
          label="VaR (95%)"
          value={riskData.var95}
          format="percent"
          icon={<ShieldAlert className="w-5 h-5 text-orange-600" />}
          description="Daily potential loss"
          size="lg"
        />
      </div>

      {/* Main Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* Performance Chart - Takes 2 columns */}
        <div className="lg:col-span-2">
          <ChartContainer
            title="Portfolio Performance"
            subtitle={`${timeRange} performance vs benchmark`}
            height={350}
          >
            <PerformanceChart
              data={performance}
              showBenchmark
              benchmarkLabel="SPY"
              valueLabel="Portfolio"
              height={300}
              areaFill
            />
          </ChartContainer>
        </div>

        {/* Allocation Chart */}
        <div>
          <ChartContainer
            title="Asset Allocation"
            subtitle="Current portfolio composition"
            height={350}
          >
            <AllocationChart
              data={allocationData}
              height={300}
              innerRadius={50}
              outerRadius={90}
            />
          </ChartContainer>
        </div>
      </div>

      {/* Performance Metrics Grid */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Performance Metrics
        </h2>
        {performanceMetrics && (
          <PerformanceMetrics data={performanceMetrics} loading={isLoading} />
        )}
      </div>

      {/* Risk Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Drawdown Chart */}
        <ChartContainer
          title="Drawdown Analysis"
          subtitle="Underwater equity curve"
          height={280}
        >
          <DrawdownChart data={drawdown} height={230} />
        </ChartContainer>

        {/* VaR Chart */}
        <ChartContainer
          title="Value at Risk"
          subtitle="Historical VaR evolution"
          height={280}
        >
          <RiskChart 
            data={risk} 
            height={230}
            showVar99
            showCvar
          />
        </ChartContainer>
      </div>

      {/* Risk Metrics & Benchmark */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Risk Analysis
          </h2>
          <RiskMetrics data={riskData} loading={isLoading} />
        </div>

        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Benchmark Comparison
          </h2>
          <BenchmarkComparison data={benchmarkData} loading={isLoading} />
        </div>
      </div>
    </Layout>
  );
};

export default Analytics;
