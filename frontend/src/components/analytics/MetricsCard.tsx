/**
 * MetricsCard Component
 * 
 * Reusable card for displaying a single metric with optional trend indicator
 */
import React from 'react';
import { clsx } from 'clsx';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface MetricsCardProps {
  label: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
  format?: 'number' | 'currency' | 'percent';
  currency?: string;  // Currency for 'currency' format
  icon?: React.ReactNode;
  trend?: 'up' | 'down' | 'neutral';
  description?: string;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const MetricsCard: React.FC<MetricsCardProps> = ({
  label,
  value,
  change,
  changeLabel,
  format = 'number',
  currency = 'USD',
  icon,
  trend,
  description,
  className,
  size = 'md',
}) => {
  // Format the main value
  const formattedValue = React.useMemo(() => {
    if (typeof value === 'string') return value;

    switch (format) {
      case 'currency':
        return new Intl.NumberFormat('en-US', {
          style: 'currency',
          currency: currency,
          minimumFractionDigits: 0,
          maximumFractionDigits: 0,
        }).format(value);
      case 'percent':
        return `${(value * 100).toFixed(2)}%`;
      default:
        return value.toLocaleString(undefined, {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        });
    }
  }, [value, format]);

  // Determine trend from change value if not provided
  const actualTrend = trend ?? (change !== undefined ? (change > 0 ? 'up' : change < 0 ? 'down' : 'neutral') : undefined);

  // Trend colors
  const trendColors = {
    up: 'text-green-600 bg-green-50 dark:text-green-400 dark:bg-green-900/20',
    down: 'text-red-600 bg-red-50 dark:text-red-400 dark:bg-red-900/20',
    neutral: 'text-gray-600 bg-gray-50 dark:text-gray-400 dark:bg-gray-700/50',
  };

  // Size variants
  const sizes = {
    sm: {
      container: 'p-3',
      label: 'text-xs',
      value: 'text-lg',
      change: 'text-xs',
    },
    md: {
      container: 'p-4',
      label: 'text-sm',
      value: 'text-2xl',
      change: 'text-sm',
    },
    lg: {
      container: 'p-6',
      label: 'text-base',
      value: 'text-3xl',
      change: 'text-sm',
    },
  };

  const sizeClasses = sizes[size];

  return (
    <div
      className={clsx(
        'bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700',
        sizeClasses.container,
        className
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className={clsx('font-medium text-gray-500 dark:text-gray-400', sizeClasses.label)}>
            {label}
          </p>
          <p className={clsx('font-bold text-gray-900 dark:text-white mt-1', sizeClasses.value)}>
            {formattedValue}
          </p>
          {description && (
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{description}</p>
          )}
        </div>
        {icon && (
          <div className="flex-shrink-0 p-2 bg-gray-50 dark:bg-gray-700 rounded-lg">
            {icon}
          </div>
        )}
      </div>

      {change !== undefined && (
        <div className="mt-3 flex items-center gap-2">
          <span
            className={clsx(
              'inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-medium',
              sizeClasses.change,
              actualTrend && trendColors[actualTrend]
            )}
          >
            {actualTrend === 'up' && <TrendingUp className="w-3 h-3" />}
            {actualTrend === 'down' && <TrendingDown className="w-3 h-3" />}
            {actualTrend === 'neutral' && <Minus className="w-3 h-3" />}
            {change > 0 ? '+' : ''}{(change * 100).toFixed(2)}%
          </span>
          {changeLabel && (
            <span className="text-xs text-gray-500 dark:text-gray-400">{changeLabel}</span>
          )}
        </div>
      )}
    </div>
  );
};

export default MetricsCard;
