/**
 * BacktestResults Component
 * 
 * Display ML model backtest performance results
 */
import React from 'react';
import { clsx } from 'clsx';
import {
  TrendingUp,
  Activity,
  Target,
  AlertTriangle,
  DollarSign,
  Percent,
  Calendar,
} from 'lucide-react';

interface BacktestMetrics {
  totalReturn: number;
  annualizedReturn: number;
  sharpeRatio: number;
  maxDrawdown: number;
  winRate: number;
  profitFactor: number;
  totalTrades: number;
  avgTradeReturn: number;
  bestTrade: number;
  worstTrade: number;
  startDate: string;
  endDate: string;
}

interface BacktestResultsProps {
  metrics: BacktestMetrics;
  loading?: boolean;
  className?: string;
}

// Metric display helper
const MetricItem: React.FC<{
  label: string;
  value: string | number;
  icon: React.ReactNode;
  trend?: 'positive' | 'negative' | 'neutral';
  description?: string;
}> = ({ label, value, icon, trend = 'neutral', description }) => {
  const trendColors = {
    positive: 'text-green-600',
    negative: 'text-red-600',
    neutral: 'text-gray-900 dark:text-white',
  };

  return (
    <div className="flex items-start gap-3 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
      <div className="p-2 bg-white dark:bg-gray-600 rounded-lg">
        {icon}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
        <p className={clsx('text-lg font-bold truncate', trendColors[trend])}>
          {value}
        </p>
        {description && (
          <p className="text-xs text-gray-400 mt-0.5">{description}</p>
        )}
      </div>
    </div>
  );
};

export const BacktestResults: React.FC<BacktestResultsProps> = ({
  metrics,
  loading = false,
  className,
}) => {
  if (loading) {
    return (
      <div className={clsx('bg-white dark:bg-gray-800 rounded-lg p-6 animate-pulse', className)}>
        <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-6" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-20 bg-gray-200 dark:bg-gray-700 rounded" />
          ))}
        </div>
      </div>
    );
  }

  // Format helpers
  const formatPercent = (value: number) => `${(value * 100).toFixed(2)}%`;
  const formatRatio = (value: number) => value.toFixed(2);
  const formatCurrency = (value: number) => 
    `${value >= 0 ? '+' : ''}${(value * 100).toFixed(2)}%`;

  // Determine trends
  const getTrend = (value: number, invertPositive = false): 'positive' | 'negative' | 'neutral' => {
    if (value === 0) return 'neutral';
    const isPositive = invertPositive ? value < 0 : value > 0;
    return isPositive ? 'positive' : 'negative';
  };

  return (
    <div className={clsx(
      'bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700',
      className
    )}>
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
            <Activity className="w-5 h-5 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">
              Backtest Results
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {metrics.startDate} - {metrics.endDate}
            </p>
          </div>
        </div>
        <div className={clsx(
          'px-3 py-1 rounded-full text-sm font-medium',
          metrics.totalReturn >= 0 
            ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
            : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
        )}>
          {formatPercent(metrics.totalReturn)} Total Return
        </div>
      </div>

      {/* Main Metrics */}
      <div className="p-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <MetricItem
            label="Total Return"
            value={formatPercent(metrics.totalReturn)}
            icon={<DollarSign className="w-4 h-4 text-green-600" />}
            trend={getTrend(metrics.totalReturn)}
          />
          
          <MetricItem
            label="Annualized Return"
            value={formatPercent(metrics.annualizedReturn)}
            icon={<TrendingUp className="w-4 h-4 text-blue-600" />}
            trend={getTrend(metrics.annualizedReturn)}
          />
          
          <MetricItem
            label="Sharpe Ratio"
            value={formatRatio(metrics.sharpeRatio)}
            icon={<Target className="w-4 h-4 text-purple-600" />}
            trend={metrics.sharpeRatio > 1 ? 'positive' : metrics.sharpeRatio > 0 ? 'neutral' : 'negative'}
            description={metrics.sharpeRatio > 2 ? 'Excellent' : metrics.sharpeRatio > 1 ? 'Good' : 'Needs Improvement'}
          />
          
          <MetricItem
            label="Max Drawdown"
            value={formatPercent(metrics.maxDrawdown)}
            icon={<AlertTriangle className="w-4 h-4 text-red-600" />}
            trend="negative"
          />
          
          <MetricItem
            label="Win Rate"
            value={formatPercent(metrics.winRate)}
            icon={<Percent className="w-4 h-4 text-emerald-600" />}
            trend={metrics.winRate > 0.5 ? 'positive' : metrics.winRate < 0.4 ? 'negative' : 'neutral'}
          />
          
          <MetricItem
            label="Profit Factor"
            value={formatRatio(metrics.profitFactor)}
            icon={<TrendingUp className="w-4 h-4 text-amber-600" />}
            trend={metrics.profitFactor > 1.5 ? 'positive' : metrics.profitFactor > 1 ? 'neutral' : 'negative'}
          />
          
          <MetricItem
            label="Total Trades"
            value={metrics.totalTrades.toLocaleString()}
            icon={<Calendar className="w-4 h-4 text-gray-600" />}
            trend="neutral"
          />
          
          <MetricItem
            label="Avg Trade Return"
            value={formatCurrency(metrics.avgTradeReturn)}
            icon={<Activity className="w-4 h-4 text-cyan-600" />}
            trend={getTrend(metrics.avgTradeReturn)}
          />
        </div>
      </div>

      {/* Trade Performance */}
      <div className="p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/50">
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
          Trade Performance Range
        </h4>
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <div className="flex justify-between text-xs text-gray-500 mb-1">
              <span>Worst: {formatCurrency(metrics.worstTrade)}</span>
              <span>Best: {formatCurrency(metrics.bestTrade)}</span>
            </div>
            <div className="h-3 bg-gradient-to-r from-red-500 via-gray-300 to-green-500 rounded-full relative">
              {/* Marker for average */}
              <div 
                className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-white border-2 border-gray-800 rounded-full"
                style={{
                  left: `${((metrics.avgTradeReturn - metrics.worstTrade) / (metrics.bestTrade - metrics.worstTrade)) * 100}%`,
                  transform: 'translateX(-50%) translateY(-50%)',
                }}
              />
            </div>
            <div className="text-xs text-gray-500 text-center mt-1">
              Average: {formatCurrency(metrics.avgTradeReturn)}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BacktestResults;
