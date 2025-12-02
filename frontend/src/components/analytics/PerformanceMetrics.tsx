/**
 * PerformanceMetrics Component
 * 
 * Displays key portfolio performance metrics in a grid
 */
import React from 'react';
import { clsx } from 'clsx';
import { 
  TrendingUp, 
  TrendingDown, 
  Activity, 
  Target,
  Award,
  BarChart3,
} from 'lucide-react';
import { MetricsCard } from './MetricsCard';

interface PerformanceData {
  totalReturn: number;
  annualizedReturn: number;
  volatility: number;
  sharpeRatio: number;
  sortinoRatio: number;
  calmarRatio?: number;
  maxDrawdown: number;
  winRate?: number;
  profitFactor?: number;
}

interface PerformanceMetricsProps {
  data: PerformanceData;
  previousPeriodData?: Partial<PerformanceData>;
  loading?: boolean;
  className?: string;
}

export const PerformanceMetrics: React.FC<PerformanceMetricsProps> = ({
  data,
  previousPeriodData,
  loading = false,
  className,
}) => {
  // Calculate changes if previous period data is available
  const calculateChange = (current: number, previous?: number) => {
    if (previous === undefined) return undefined;
    return current - previous;
  };

  if (loading) {
    return (
      <div className={clsx('grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4', className)}>
        {Array.from({ length: 8 }).map((_, i) => (
          <div
            key={i}
            className="bg-white dark:bg-gray-800 rounded-lg p-4 animate-pulse"
          >
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2 mb-2" />
            <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-3/4" />
          </div>
        ))}
      </div>
    );
  }

  const metrics = [
    {
      label: 'Total Return',
      value: data.totalReturn,
      format: 'percent' as const,
      change: calculateChange(data.totalReturn, previousPeriodData?.totalReturn),
      icon: <TrendingUp className="w-5 h-5 text-blue-600" />,
      trend: data.totalReturn >= 0 ? 'up' : 'down' as const,
    },
    {
      label: 'Annualized Return',
      value: data.annualizedReturn,
      format: 'percent' as const,
      change: calculateChange(data.annualizedReturn, previousPeriodData?.annualizedReturn),
      icon: <BarChart3 className="w-5 h-5 text-green-600" />,
    },
    {
      label: 'Volatility',
      value: data.volatility,
      format: 'percent' as const,
      change: calculateChange(data.volatility, previousPeriodData?.volatility),
      icon: <Activity className="w-5 h-5 text-orange-600" />,
      // Lower volatility is better
      trend: data.volatility <= (previousPeriodData?.volatility ?? data.volatility) ? 'up' : 'down' as const,
    },
    {
      label: 'Sharpe Ratio',
      value: data.sharpeRatio,
      format: 'number' as const,
      change: calculateChange(data.sharpeRatio, previousPeriodData?.sharpeRatio),
      icon: <Award className="w-5 h-5 text-purple-600" />,
      description: data.sharpeRatio >= 1 ? 'Good' : data.sharpeRatio >= 2 ? 'Excellent' : 'Below average',
    },
    {
      label: 'Sortino Ratio',
      value: data.sortinoRatio,
      format: 'number' as const,
      change: calculateChange(data.sortinoRatio, previousPeriodData?.sortinoRatio),
      icon: <Target className="w-5 h-5 text-indigo-600" />,
    },
    {
      label: 'Max Drawdown',
      value: data.maxDrawdown,
      format: 'percent' as const,
      icon: <TrendingDown className="w-5 h-5 text-red-600" />,
      trend: 'down' as const,
    },
  ];

  // Add optional metrics
  if (data.calmarRatio !== undefined) {
    metrics.push({
      label: 'Calmar Ratio',
      value: data.calmarRatio,
      format: 'number' as const,
      change: calculateChange(data.calmarRatio, previousPeriodData?.calmarRatio),
      icon: <BarChart3 className="w-5 h-5 text-cyan-600" />,
    });
  }

  if (data.winRate !== undefined) {
    metrics.push({
      label: 'Win Rate',
      value: data.winRate,
      format: 'percent' as const,
      change: calculateChange(data.winRate, previousPeriodData?.winRate),
      icon: <Award className="w-5 h-5 text-emerald-600" />,
    });
  }

  return (
    <div className={clsx('grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4', className)}>
      {metrics.map((metric, index) => (
        <MetricsCard
          key={metric.label}
          label={metric.label}
          value={metric.value}
          format={metric.format}
          change={metric.change}
          icon={metric.icon}
          trend={metric.trend}
          description={metric.description}
        />
      ))}
    </div>
  );
};

export default PerformanceMetrics;
