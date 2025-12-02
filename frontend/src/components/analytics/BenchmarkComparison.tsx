/**
 * BenchmarkComparison Component
 * 
 * Visual comparison of portfolio vs benchmark performance
 */
import React from 'react';
import { clsx } from 'clsx';
import { 
  TrendingUp, 
  TrendingDown,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
} from 'lucide-react';

interface BenchmarkData {
  benchmarkSymbol: string;
  portfolioReturn: number;
  benchmarkReturn: number;
  excessReturn: number;
  alpha: number;
  beta: number;
  trackingError: number;
  informationRatio: number;
  upCapture: number;
  downCapture: number;
}

interface BenchmarkComparisonProps {
  data: BenchmarkData;
  loading?: boolean;
  className?: string;
}

// Comparison bar component
const ComparisonBar: React.FC<{
  label: string;
  portfolioValue: number;
  benchmarkValue: number;
  format?: 'percent' | 'number';
}> = ({ label, portfolioValue, benchmarkValue, format = 'percent' }) => {
  const formatValue = (val: number) => {
    if (format === 'percent') {
      return `${(val * 100).toFixed(2)}%`;
    }
    return val.toFixed(2);
  };

  const maxValue = Math.max(Math.abs(portfolioValue), Math.abs(benchmarkValue));
  const scale = maxValue > 0 ? 100 / maxValue : 1;

  const portfolioWidth = Math.abs(portfolioValue) * scale;
  const benchmarkWidth = Math.abs(benchmarkValue) * scale;

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm">
        <span className="text-gray-600 dark:text-gray-400">{label}</span>
      </div>
      
      {/* Portfolio bar */}
      <div className="flex items-center gap-3">
        <span className="w-20 text-xs text-gray-500">Portfolio</span>
        <div className="flex-1 h-6 bg-gray-100 dark:bg-gray-700 rounded overflow-hidden">
          <div
            className={clsx(
              'h-full rounded transition-all duration-500',
              portfolioValue >= 0 ? 'bg-blue-500' : 'bg-red-500'
            )}
            style={{ width: `${portfolioWidth}%` }}
          />
        </div>
        <span className={clsx(
          'w-20 text-sm font-medium text-right',
          portfolioValue >= 0 ? 'text-blue-600' : 'text-red-600'
        )}>
          {portfolioValue >= 0 ? '+' : ''}{formatValue(portfolioValue)}
        </span>
      </div>

      {/* Benchmark bar */}
      <div className="flex items-center gap-3">
        <span className="w-20 text-xs text-gray-500">Benchmark</span>
        <div className="flex-1 h-6 bg-gray-100 dark:bg-gray-700 rounded overflow-hidden">
          <div
            className={clsx(
              'h-full rounded transition-all duration-500',
              benchmarkValue >= 0 ? 'bg-gray-400' : 'bg-red-400'
            )}
            style={{ width: `${benchmarkWidth}%` }}
          />
        </div>
        <span className={clsx(
          'w-20 text-sm font-medium text-right',
          benchmarkValue >= 0 ? 'text-gray-600' : 'text-red-600'
        )}>
          {benchmarkValue >= 0 ? '+' : ''}{formatValue(benchmarkValue)}
        </span>
      </div>
    </div>
  );
};

// Metric row component
const MetricRow: React.FC<{
  label: string;
  value: number;
  format?: 'percent' | 'number' | 'ratio';
  description?: string;
  showTrend?: boolean;
}> = ({ label, value, format = 'number', description, showTrend = false }) => {
  const formatValue = () => {
    switch (format) {
      case 'percent':
        return `${(value * 100).toFixed(2)}%`;
      case 'ratio':
        return `${value.toFixed(2)}x`;
      default:
        return value.toFixed(2);
    }
  };

  const isPositive = value > 0;
  const isNeutral = value === 0;

  return (
    <div className="flex items-center justify-between py-3 border-b border-gray-100 dark:border-gray-700 last:border-0">
      <div>
        <span className="text-sm text-gray-700 dark:text-gray-300">{label}</span>
        {description && (
          <p className="text-xs text-gray-500 dark:text-gray-400">{description}</p>
        )}
      </div>
      <div className="flex items-center gap-2">
        {showTrend && !isNeutral && (
          isPositive ? (
            <ArrowUpRight className="w-4 h-4 text-green-500" />
          ) : (
            <ArrowDownRight className="w-4 h-4 text-red-500" />
          )
        )}
        {showTrend && isNeutral && <Minus className="w-4 h-4 text-gray-400" />}
        <span className={clsx(
          'font-semibold',
          showTrend && isPositive && 'text-green-600',
          showTrend && !isPositive && !isNeutral && 'text-red-600',
          (!showTrend || isNeutral) && 'text-gray-900 dark:text-white'
        )}>
          {formatValue()}
        </span>
      </div>
    </div>
  );
};

export const BenchmarkComparison: React.FC<BenchmarkComparisonProps> = ({
  data,
  loading = false,
  className,
}) => {
  if (loading) {
    return (
      <div className={clsx('bg-white dark:bg-gray-800 rounded-lg p-6 animate-pulse', className)}>
        <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-6" />
        <div className="space-y-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-16 bg-gray-200 dark:bg-gray-700 rounded" />
          ))}
        </div>
      </div>
    );
  }

  const outperformed = data.excessReturn > 0;

  return (
    <div className={clsx('bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700', className)}>
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">
              vs {data.benchmarkSymbol}
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Benchmark Comparison
            </p>
          </div>
          <div className={clsx(
            'flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium',
            outperformed 
              ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
              : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
          )}>
            {outperformed ? (
              <>
                <TrendingUp className="w-4 h-4" />
                Outperforming
              </>
            ) : (
              <>
                <TrendingDown className="w-4 h-4" />
                Underperforming
              </>
            )}
          </div>
        </div>
      </div>

      {/* Return Comparison */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <ComparisonBar
          label="Total Return"
          portfolioValue={data.portfolioReturn}
          benchmarkValue={data.benchmarkReturn}
          format="percent"
        />
      </div>

      {/* Excess Return Highlight */}
      <div className={clsx(
        'p-4 border-b border-gray-200 dark:border-gray-700',
        outperformed ? 'bg-green-50 dark:bg-green-900/10' : 'bg-red-50 dark:bg-red-900/10'
      )}>
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Excess Return
          </span>
          <span className={clsx(
            'text-2xl font-bold',
            outperformed ? 'text-green-600' : 'text-red-600'
          )}>
            {data.excessReturn > 0 ? '+' : ''}{(data.excessReturn * 100).toFixed(2)}%
          </span>
        </div>
      </div>

      {/* Detailed Metrics */}
      <div className="p-4">
        <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3">
          Relative Metrics
        </h4>
        
        <MetricRow
          label="Alpha"
          value={data.alpha}
          format="percent"
          description="Risk-adjusted excess return"
          showTrend
        />
        
        <MetricRow
          label="Beta"
          value={data.beta}
          format="number"
          description="Market sensitivity"
        />
        
        <MetricRow
          label="Tracking Error"
          value={data.trackingError}
          format="percent"
          description="Return deviation from benchmark"
        />
        
        <MetricRow
          label="Information Ratio"
          value={data.informationRatio}
          format="number"
          description="Risk-adjusted active return"
          showTrend
        />

        <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400 mt-6 mb-3">
          Capture Ratios
        </h4>
        
        <MetricRow
          label="Up Capture"
          value={data.upCapture}
          format="ratio"
          description="Performance in up markets"
        />
        
        <MetricRow
          label="Down Capture"
          value={data.downCapture}
          format="ratio"
          description="Performance in down markets"
        />
      </div>
    </div>
  );
};

export default BenchmarkComparison;
