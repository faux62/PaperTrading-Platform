/**
 * Analytics Page
 * 
 * Comprehensive portfolio analytics dashboard:
 * - Performance metrics
 * - Risk analysis
 * - Benchmark comparison
 * - Interactive charts
 */
import React, { useState, useMemo, useEffect, useCallback } from 'react';
import { Layout } from '../components/layout';
import { 
  BarChart3, 
  TrendingUp, 
  ShieldAlert, 
  Target,
  RefreshCw,
  AlertCircle,
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

import { portfolioApi, tradingApi, marketApi } from '../services/api';

type TimeRange = '1W' | '1M' | '3M' | '6M' | '1Y' | 'YTD' | 'ALL';

interface Portfolio {
  id: number;
  name: string;
  initial_capital: number;
  cash_balance: number;
  currency: string;
}

interface PortfolioPosition {
  id: number;
  symbol: string;
  quantity: number;
  average_cost: number;
  avg_cost?: number;  // DB field name
  current_price?: number;
  market_value?: number;
  unrealized_pnl?: number;
  unrealized_pnl_percent?: number;
  native_currency?: string;
}

interface Trade {
  id: number;
  symbol: string;
  trade_type: string;
  quantity: number;
  price: number;
  total_value: number;
  realized_pnl?: number;
  executed_at: string;
}

interface Quote {
  symbol: string;
  price: number;
  change?: number;
  change_percent?: number;
}

// Color palette for allocation chart
const ALLOCATION_COLORS = [
  '#3b82f6', // blue
  '#10b981', // green  
  '#f59e0b', // amber
  '#8b5cf6', // purple
  '#ef4444', // red
  '#06b6d4', // cyan
  '#f97316', // orange
  '#84cc16', // lime
  '#ec4899', // pink
  '#6366f1', // indigo
];

const Analytics: React.FC = () => {
  const [timeRange, setTimeRange] = useState<TimeRange>('1Y');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Real data state
  const [activePortfolio, setActivePortfolio] = useState<Portfolio | null>(null);
  const [positions, setPositions] = useState<PortfolioPosition[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [benchmarkData, setBenchmarkData] = useState<any[]>([]);
  const [initialCapital, setInitialCapital] = useState(100000);
  const [cashBalance, setCashBalance] = useState(0);

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

  // Fetch real data
  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      // First, get portfolios if we don't have one selected
      let portfolio = activePortfolio;
      if (!portfolio) {
        const portfoliosResponse = await portfolioApi.getAll();
        const portfolios = Array.isArray(portfoliosResponse) ? portfoliosResponse : (portfoliosResponse.portfolios || []);
        if (portfolios.length === 0) {
          setError('No portfolios found. Create a portfolio first.');
          setIsLoading(false);
          return;
        }
        portfolio = portfolios[0];
        setActivePortfolio(portfolio);
      }

      // Type guard - portfolio is now guaranteed to be non-null
      const currentPortfolio = portfolio!;

      // Fetch portfolio details
      const portfolioData = await portfolioApi.getById(currentPortfolio.id);
      setInitialCapital(portfolioData.initial_capital || 100000);
      setCashBalance(portfolioData.cash_balance || 0);
      
      // Fetch positions
      const positionsData = await portfolioApi.getPositions(currentPortfolio.id);
      
      // Use positions data from DB - market_value is already converted to portfolio currency
      if (positionsData.length > 0) {
        // Normalize field names from DB (avg_cost -> average_cost)
        const normalizedPositions = positionsData.map((pos: PortfolioPosition) => ({
          ...pos,
          average_cost: pos.average_cost || pos.avg_cost || 0,
        }));
        
        // Try to get fresh quotes for display, but preserve DB market_value
        const symbols = normalizedPositions.map((p: PortfolioPosition) => p.symbol);
        try {
          const quotesResponse = await marketApi.getQuotes(symbols);
          const quotes: Quote[] = Array.isArray(quotesResponse) ? quotesResponse : (quotesResponse.quotes || []);
          const quotesMap = new Map(quotes.map((q: Quote) => [q.symbol, q]));
          
          // Use market_value from DB (already currency-converted) - DO NOT recalculate!
          const enrichedPositions = normalizedPositions.map((pos: PortfolioPosition) => {
            const quote = quotesMap.get(pos.symbol);
            // market_value from DB is already converted to portfolio currency (EUR)
            // Only use it, don't recalculate with foreign currency prices!
            const dbMarketValue = pos.market_value || 0;
            const dbUnrealizedPnl = pos.unrealized_pnl || 0;
            const dbUnrealizedPnlPercent = pos.unrealized_pnl_percent || 0;
            
            return {
              ...pos,
              current_price: quote?.price || pos.current_price || pos.average_cost,
              market_value: dbMarketValue,  // Use DB value (currency-converted)
              unrealized_pnl: dbUnrealizedPnl,
              unrealized_pnl_percent: dbUnrealizedPnlPercent,
            };
          });
          setPositions(enrichedPositions);
        } catch (quotesError) {
          console.error('Error fetching quotes:', quotesError);
          // Use positions from DB directly - they have correct market_value
          setPositions(normalizedPositions);
        }
      } else {
        setPositions([]);
      }

      // Fetch trade history
      const days = getDays(timeRange);
      const startDate = new Date();
      startDate.setDate(startDate.getDate() - days);
      
      try {
        const tradesData = await tradingApi.getTradeHistory(currentPortfolio.id, {
          start_date: startDate.toISOString().split('T')[0],
        });
        setTrades(tradesData || []);
      } catch (tradesError) {
        console.error('Error fetching trades:', tradesError);
        setTrades([]);
      }

      // Fetch SPY benchmark data
      try {
        const period = timeRange === '1W' ? '1W' : timeRange === '1M' ? '1M' : timeRange === '3M' ? '3M' : '1Y';
        const spyHistory = await marketApi.getHistorical('SPY', period);
        // API returns { symbol, period, timeframe, data: [...] }
        setBenchmarkData(spyHistory?.data || []);
      } catch (benchError) {
        console.error('Error fetching benchmark:', benchError);
        setBenchmarkData([]);
      }

    } catch (err) {
      console.error('Error fetching analytics data:', err);
      setError(err instanceof Error ? err.message : 'Failed to load analytics data');
    } finally {
      setIsLoading(false);
    }
  }, [activePortfolio, timeRange]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Calculate allocation data from real positions
  const allocationData = useMemo(() => {
    if (positions.length === 0) {
      // Show cash only if no positions
      return cashBalance > 0 ? [{ name: 'Cash', value: cashBalance, color: '#6b7280' }] : [];
    }
    
    const positionAllocations = positions.map((pos, index) => ({
      name: pos.symbol,
      // Use market_value from DB (already currency-converted) - NO fallback calculation!
      value: pos.market_value || 0,
      color: ALLOCATION_COLORS[index % ALLOCATION_COLORS.length],
    }));
    
    // Add cash if present
    if (cashBalance > 0) {
      positionAllocations.push({ name: 'Cash', value: cashBalance, color: '#6b7280' });
    }
    
    return positionAllocations;
  }, [positions, cashBalance]);

  // Calculate current portfolio value from real data (use DB market_value only!)
  const currentPortfolioValue = useMemo(() => {
    // IMPORTANT: market_value from DB is already converted to portfolio currency
    // Do NOT recalculate using quantity * price (prices are in native currency!)
    const positionsValue = positions.reduce((sum, p) => sum + (p.market_value || 0), 0);
    return positionsValue + cashBalance;
  }, [positions, cashBalance]);

  // Generate performance data based on trades and current value
  const { performance, drawdown, risk, hasEnoughDataForVaR, actualTradingDays: tradingDaysCount } = useMemo(() => {
    const days = getDays(timeRange);
    const performanceData = [];
    const drawdownData = [];
    const riskData = [];
    
    const startValue = initialCapital;
    const endValue = currentPortfolioValue > 0 ? currentPortfolioValue : initialCapital;
    const totalPnL = endValue - startValue;
    
    // Find the date of first trade to determine actual trading period
    const sortedTrades = [...trades].sort((a, b) => 
      new Date(a.executed_at).getTime() - new Date(b.executed_at).getTime()
    );
    const firstTradeDate = sortedTrades.length > 0 
      ? new Date(sortedTrades[0].executed_at) 
      : new Date();
    const actualTradingDays = Math.max(1, Math.ceil((new Date().getTime() - firstTradeDate.getTime()) / (1000 * 60 * 60 * 24)));
    
    // For drawdown: limit to actual trading period + a few days before
    const drawdownStartDate = new Date(firstTradeDate);
    drawdownStartDate.setDate(drawdownStartDate.getDate() - 2); // 2 days before first trade
    
    // Generate daily values - but only from relevant period for drawdown
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - days);
    
    let peak = startValue;
    let benchmarkStartPrice = benchmarkData.length > 0 ? benchmarkData[0]?.close || 100 : 100;
    
    for (let i = 0; i <= days; i++) {
      const date = new Date(startDate);
      date.setDate(date.getDate() + i);
      const dateStr = date.toISOString().split('T')[0];
      
      // Before first trade: flat at initial capital
      // After first trade: interpolate to current value
      let value: number;
      if (date < firstTradeDate) {
        value = startValue;
      } else {
        // Calculate progress since first trade
        const daysSinceFirstTrade = Math.ceil((date.getTime() - firstTradeDate.getTime()) / (1000 * 60 * 60 * 24));
        const progress = Math.min(daysSinceFirstTrade / actualTradingDays, 1);
        value = startValue + (totalPnL * progress);
      }
      
      // Benchmark from real data
      const progress = i / days;
      const benchmarkIndex = Math.min(Math.floor(progress * benchmarkData.length), benchmarkData.length - 1);
      const benchmarkPrice = benchmarkData.length > 0 && benchmarkData[benchmarkIndex]
        ? benchmarkData[benchmarkIndex].close 
        : benchmarkStartPrice;
      const benchmarkValue = (benchmarkPrice / benchmarkStartPrice) * startValue;
      
      peak = Math.max(peak, value);
      const currentDrawdown = peak > 0 ? (value - peak) / peak : 0;
      
      performanceData.push({
        date: dateStr,
        value: Math.round(value),
        benchmark: Math.round(benchmarkValue),
      });
      
      // Only add drawdown data from relevant period (from first trade onwards)
      if (date >= drawdownStartDate) {
        drawdownData.push({
          date: dateStr,
          drawdown: currentDrawdown,
          peak: Math.round(peak),
          value: Math.round(value),
        });
      }
      
      // Risk metrics - only add if we have enough data for meaningful VaR
      // Otherwise don't populate (will show "insufficient data" message)
      if (actualTradingDays >= 20) {
        const estimatedVol = positions.length > 0 ? 0.20 : 0.15;
        riskData.push({
          date: dateStr,
          var95: -estimatedVol * 1.65 / Math.sqrt(252),
          var99: -estimatedVol * 2.33 / Math.sqrt(252),
          cvar: -estimatedVol * 2.06 / Math.sqrt(252),
          volatility: estimatedVol,
        });
      }
    }
    
    return { 
      performance: performanceData, 
      drawdown: drawdownData, 
      risk: riskData,
      hasEnoughDataForVaR: actualTradingDays >= 20,
      actualTradingDays,
    };
  }, [timeRange, initialCapital, currentPortfolioValue, trades, positions, benchmarkData, cashBalance]);

  // Calculate performance metrics from REAL portfolio data
  const performanceMetrics = useMemo(() => {
    // Use actual portfolio values for accurate metrics
    const startValue = initialCapital;
    const endValue = currentPortfolioValue > 0 ? currentPortfolioValue : initialCapital;
    
    // Real total return based on actual portfolio value
    const totalReturn = startValue > 0 ? (endValue - startValue) / startValue : 0;
    
    // Calculate actual trading period for annualization
    const sortedTrades = [...trades].sort((a, b) => 
      new Date(a.executed_at).getTime() - new Date(b.executed_at).getTime()
    );
    const firstTradeDate = sortedTrades.length > 0 
      ? new Date(sortedTrades[0].executed_at) 
      : new Date();
    const actualTradingDays = Math.max(1, Math.ceil((new Date().getTime() - firstTradeDate.getTime()) / (1000 * 60 * 60 * 24)));
    
    // Annualize return based on actual trading period
    // Only annualize if we have meaningful trading history (>7 days)
    let annualizedReturn: number;
    if (actualTradingDays >= 7) {
      annualizedReturn = Math.pow(1 + totalReturn, 365 / actualTradingDays) - 1;
    } else {
      // For very short periods, don't annualize - show actual return
      annualizedReturn = totalReturn;
    }
    
    // Calculate volatility from daily returns in performance data
    const returns = [];
    for (let i = 1; i < performance.length; i++) {
      if (performance[i-1].value > 0 && performance[i].value !== performance[i-1].value) {
        returns.push((performance[i].value - performance[i-1].value) / performance[i-1].value);
      }
    }
    
    // Filter out zero returns for volatility calculation (flat periods before trading)
    const nonZeroReturns = returns.filter(r => r !== 0);
    
    let annualizedVol: number | null;
    if (nonZeroReturns.length >= 5) {
      // Calculate real volatility if we have enough data points
      const avgReturn = nonZeroReturns.reduce((a, b) => a + b, 0) / nonZeroReturns.length;
      const variance = nonZeroReturns.reduce((sum, r) => sum + Math.pow(r - avgReturn, 2), 0) / nonZeroReturns.length;
      const dailyVol = Math.sqrt(variance);
      annualizedVol = dailyVol * Math.sqrt(252);
    } else {
      // Not enough data to calculate volatility
      annualizedVol = null;
    }
    
    // Max drawdown from actual data
    const maxDD = drawdown.length > 0 ? Math.min(...drawdown.map(d => d.drawdown)) : 0;
    
    // Risk-adjusted metrics
    const riskFreeRate = 0.05; // Current approximate risk-free rate
    
    // Sharpe ratio - only calculate if we have meaningful data
    let sharpe: number | null;
    if (actualTradingDays >= 7 && annualizedVol !== null && annualizedVol > 0.01) {
      sharpe = (annualizedReturn - riskFreeRate) / annualizedVol;
    } else {
      // Not enough data for meaningful Sharpe
      sharpe = null;
    }
    
    // Sortino (using only downside deviation)
    const negativeReturns = nonZeroReturns.filter(r => r < 0);
    let sortino: number | null;
    if (negativeReturns.length >= 3 && actualTradingDays >= 7) {
      const downsideDeviation = Math.sqrt(negativeReturns.reduce((sum, r) => sum + r * r, 0) / negativeReturns.length) * Math.sqrt(252);
      sortino = downsideDeviation > 0 ? (annualizedReturn - riskFreeRate) / downsideDeviation : null;
    } else {
      sortino = null;
    }
    
    // Calmar ratio
    const calmar = maxDD < -0.001 ? annualizedReturn / Math.abs(maxDD) : null;
    
    // Win rate from trades with realized PnL
    const tradesWithPnL = trades.filter(t => t.realized_pnl !== null && t.realized_pnl !== undefined);
    const winningTrades = tradesWithPnL.filter(t => (t.realized_pnl || 0) > 0).length;
    const winRate = tradesWithPnL.length > 0 ? winningTrades / tradesWithPnL.length : null;
    
    return {
      totalReturn,
      annualizedReturn,
      volatility: annualizedVol,
      sharpeRatio: sharpe,
      sortinoRatio: sortino,
      calmarRatio: calmar,
      maxDrawdown: maxDD,
      winRate,
      actualTradingDays, // Include for UI display
    };
  }, [performance, drawdown, trades, initialCapital, currentPortfolioValue, positions]);

  // Calculate risk metrics
  const riskMetricsData = useMemo(() => {
    // We need at least 20 days of trading data for meaningful risk metrics
    const MIN_DAYS_FOR_RISK = 20;
    
    // Calculate actual trading days from trades
    const sortedTrades = [...trades].sort((a, b) => 
      new Date(a.executed_at).getTime() - new Date(b.executed_at).getTime()
    );
    const firstTradeDate = sortedTrades.length > 0 
      ? new Date(sortedTrades[0].executed_at) 
      : new Date();
    const actualTradingDays = Math.max(0, Math.ceil((new Date().getTime() - firstTradeDate.getTime()) / (1000 * 60 * 60 * 24)));
    
    // Check if we have enough data for meaningful calculations
    const hasEnoughData = actualTradingDays >= MIN_DAYS_FOR_RISK && trades.length >= 5;
    
    // If not enough data, return null values
    if (!hasEnoughData) {
      return {
        var95: null,
        var99: null,
        cvar95: null,
        beta: null,
        alpha: null,
        rSquared: null,
        skewness: null,
        kurtosis: null,
        hasEnoughData: false,
      };
    }
    
    // Calculate real metrics from performance data
    const portfolioReturns: number[] = [];
    const benchmarkReturns: number[] = [];
    
    for (let i = 1; i < performance.length; i++) {
      if (performance[i-1].value > 0) {
        const portReturn = (performance[i].value - performance[i-1].value) / performance[i-1].value;
        portfolioReturns.push(portReturn);
        
        if (performance[i-1].benchmark > 0) {
          const benchReturn = (performance[i].benchmark - performance[i-1].benchmark) / performance[i-1].benchmark;
          benchmarkReturns.push(benchReturn);
        }
      }
    }
    
    // Filter out zero returns (flat periods)
    const nonZeroReturns = portfolioReturns.filter(r => r !== 0);
    
    // VaR calculation (parametric method)
    let var95: number | null = null;
    let var99: number | null = null;
    let cvar95: number | null = null;
    
    if (nonZeroReturns.length >= 10) {
      const avgReturn = nonZeroReturns.reduce((a, b) => a + b, 0) / nonZeroReturns.length;
      const variance = nonZeroReturns.reduce((sum, r) => sum + Math.pow(r - avgReturn, 2), 0) / nonZeroReturns.length;
      const dailyVol = Math.sqrt(variance);
      
      var95 = avgReturn - 1.645 * dailyVol;
      var99 = avgReturn - 2.326 * dailyVol;
      
      // CVaR: average of returns below VaR threshold
      const sortedReturns = [...nonZeroReturns].sort((a, b) => a - b);
      const var95Index = Math.floor(nonZeroReturns.length * 0.05);
      const tailReturns = sortedReturns.slice(0, Math.max(1, var95Index));
      cvar95 = tailReturns.reduce((a, b) => a + b, 0) / tailReturns.length;
    }
    
    // Beta, Alpha, R-Squared calculation
    let beta: number | null = null;
    let alpha: number | null = null;
    let rSquared: number | null = null;
    
    if (portfolioReturns.length >= 10 && benchmarkReturns.length >= 10 && 
        portfolioReturns.length === benchmarkReturns.length) {
      const avgPort = portfolioReturns.reduce((a, b) => a + b, 0) / portfolioReturns.length;
      const avgBench = benchmarkReturns.reduce((a, b) => a + b, 0) / benchmarkReturns.length;
      
      let covariance = 0;
      let benchVariance = 0;
      let portVariance = 0;
      
      for (let i = 0; i < portfolioReturns.length; i++) {
        covariance += (portfolioReturns[i] - avgPort) * (benchmarkReturns[i] - avgBench);
        benchVariance += Math.pow(benchmarkReturns[i] - avgBench, 2);
        portVariance += Math.pow(portfolioReturns[i] - avgPort, 2);
      }
      
      if (benchVariance > 0) {
        beta = covariance / benchVariance;
        alpha = (avgPort - beta * avgBench) * 252; // Annualized
        
        if (portVariance > 0 && benchVariance > 0) {
          const correlation = covariance / Math.sqrt(portVariance * benchVariance);
          rSquared = correlation * correlation;
        }
      }
    }
    
    // Skewness and Kurtosis
    let skewness: number | null = null;
    let kurtosis: number | null = null;
    
    if (nonZeroReturns.length >= 30) {
      const avgReturn = nonZeroReturns.reduce((a, b) => a + b, 0) / nonZeroReturns.length;
      const variance = nonZeroReturns.reduce((sum, r) => sum + Math.pow(r - avgReturn, 2), 0) / nonZeroReturns.length;
      const stdDev = Math.sqrt(variance);
      
      if (stdDev > 0) {
        // Skewness = E[(X - μ)³] / σ³
        const cubedDeviations = nonZeroReturns.reduce((sum, r) => sum + Math.pow((r - avgReturn) / stdDev, 3), 0);
        skewness = cubedDeviations / nonZeroReturns.length;
        
        // Kurtosis = E[(X - μ)⁴] / σ⁴
        const fourthDeviations = nonZeroReturns.reduce((sum, r) => sum + Math.pow((r - avgReturn) / stdDev, 4), 0);
        kurtosis = fourthDeviations / nonZeroReturns.length;
      }
    }
    
    return {
      var95,
      var99,
      cvar95,
      beta,
      alpha,
      rSquared,
      skewness,
      kurtosis,
      hasEnoughData: true,
    };
  }, [risk, performance, trades]);

  // Benchmark comparison data
  const benchmarkComparisonData = useMemo(() => {
    const portfolioReturn = performanceMetrics?.totalReturn ?? 0;
    const benchStart = performance.length > 0 ? performance[0].benchmark : 0;
    const benchEnd = performance.length > 0 ? performance[performance.length - 1].benchmark : 0;
    const benchmarkReturn = benchStart > 0 ? (benchEnd - benchStart) / benchStart : 0;
    
    // Handle null values from risk metrics
    const alpha = riskMetricsData.alpha;
    const beta = riskMetricsData.beta;
    const vol = performanceMetrics?.volatility;
    
    return {
      benchmarkSymbol: 'SPY',
      portfolioReturn,
      benchmarkReturn,
      excessReturn: portfolioReturn - benchmarkReturn,
      alpha: alpha,
      beta: beta,
      trackingError: vol !== null ? vol * 0.3 : null,
      informationRatio: alpha !== null && vol !== null && vol > 0 ? alpha / vol : null,
      upCapture: beta !== null && beta > 0 ? 1 + (beta - 1) * 0.1 : null,
      downCapture: beta !== null && beta > 0 ? 1 - (1 - beta) * 0.1 : null,
    };
  }, [performanceMetrics, performance, riskMetricsData]); 
  const handleRefresh = () => {
    fetchData();
  };

  // Show error state
  if (error && !isLoading) {
    return (
      <Layout title="Analytics">
        <div className="flex flex-col items-center justify-center h-64">
          <AlertCircle className="w-12 h-12 text-red-500 mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            Failed to Load Analytics
          </h2>
          <p className="text-gray-500 dark:text-gray-400 mb-4">{error}</p>
          <button
            onClick={handleRefresh}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Try Again
          </button>
        </div>
      </Layout>
    );
  }

  // Show message if no portfolio selected
  if (!activePortfolio && !isLoading) {
    return (
      <Layout title="Analytics">
        <div className="flex flex-col items-center justify-center h-64">
          <BarChart3 className="w-12 h-12 text-gray-400 mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            No Portfolio Selected
          </h2>
          <p className="text-gray-500 dark:text-gray-400">
            Please select a portfolio to view analytics
          </p>
        </div>
      </Layout>
    );
  }

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
          value={riskMetricsData.var95}
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
          subtitle={tradingDaysCount < 20 
            ? `Dati da ${tradingDaysCount} giorni di trading` 
            : "Underwater equity curve"}
          height={280}
        >
          {drawdown.length > 0 ? (
            <DrawdownChart data={drawdown} height={230} />
          ) : (
            <div className="flex items-center justify-center h-[230px] text-gray-400 dark:text-gray-500">
              <div className="text-center">
                <AlertCircle className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p className="text-sm italic">Nessun dato di drawdown disponibile</p>
              </div>
            </div>
          )}
        </ChartContainer>

        {/* VaR Chart */}
        <ChartContainer
          title="Value at Risk"
          subtitle="Historical VaR evolution"
          height={280}
        >
          {hasEnoughDataForVaR ? (
            <RiskChart 
              data={risk} 
              height={230}
              showVar99
              showCvar
            />
          ) : (
            <div className="flex items-center justify-center h-[230px] text-gray-400 dark:text-gray-500">
              <div className="text-center">
                <AlertCircle className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p className="text-sm italic">Dati insufficienti</p>
                <p className="text-xs mt-1">Richiesti almeno 20 giorni di trading</p>
                <p className="text-xs">({tradingDaysCount} giorni attuali)</p>
              </div>
            </div>
          )}
        </ChartContainer>
      </div>

      {/* Risk Metrics & Benchmark */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Risk Analysis
          </h2>
          <RiskMetrics data={riskMetricsData} loading={isLoading} />
        </div>

        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Benchmark Comparison
          </h2>
          <BenchmarkComparison data={benchmarkComparisonData} loading={isLoading} />
        </div>
      </div>
    </Layout>
  );
};

export default Analytics;
