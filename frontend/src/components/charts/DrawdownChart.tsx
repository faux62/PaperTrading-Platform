/**
 * DrawdownChart Component
 * 
 * Visualization of portfolio drawdowns:
 * - Underwater chart showing drawdown periods
 * - Peak-to-trough visualization
 * - Recovery periods highlighted
 */
import React, { useMemo } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { clsx } from 'clsx';
import type { DrawdownChartProps, DrawdownData } from './types';

// Format percentage
const formatPercent = (value: number): string => {
  return `${(value * 100).toFixed(1)}%`;
};

// Format date
const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
};

// Custom tooltip
const CustomTooltip: React.FC<any> = ({ active, payload }) => {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  const data = payload[0].payload as DrawdownData;

  return (
    <div className="bg-white dark:bg-gray-800 shadow-lg rounded-lg border border-gray-200 dark:border-gray-700 p-3">
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">
        {formatDate(data.date)}
      </p>
      <div className="space-y-1">
        <div className="flex items-center justify-between gap-4">
          <span className="text-sm text-gray-600 dark:text-gray-300">Drawdown:</span>
          <span className="text-sm font-semibold text-red-600">
            {formatPercent(data.drawdown)}
          </span>
        </div>
        {data.peak !== undefined && (
          <div className="flex items-center justify-between gap-4">
            <span className="text-sm text-gray-600 dark:text-gray-300">Peak:</span>
            <span className="text-sm font-medium text-gray-900 dark:text-white">
              ${data.peak.toLocaleString()}
            </span>
          </div>
        )}
        {data.value !== undefined && (
          <div className="flex items-center justify-between gap-4">
            <span className="text-sm text-gray-600 dark:text-gray-300">Current:</span>
            <span className="text-sm font-medium text-gray-900 dark:text-white">
              ${data.value.toLocaleString()}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

export const DrawdownChart: React.FC<DrawdownChartProps> = ({
  data,
  width = '100%',
  height = 200,
  theme = 'light',
  loading = false,
  error,
  className,
  fillColor = 'rgba(239, 68, 68, 0.3)',
}) => {
  const isDark = theme === 'dark';

  const colors = useMemo(
    () => ({
      stroke: '#ef4444',
      fill: fillColor,
      grid: isDark ? '#374151' : '#e5e7eb',
      text: isDark ? '#9ca3af' : '#6b7280',
    }),
    [isDark, fillColor]
  );

  // Calculate min drawdown for y-axis
  const minDrawdown = useMemo(() => {
    if (data.length === 0) return -0.1;
    const min = Math.min(...data.map((d) => d.drawdown));
    return Math.floor(min * 10) / 10 - 0.05;
  }, [data]);

  if (error) {
    return (
      <div
        className={clsx('flex items-center justify-center', className)}
        style={{ height }}
      >
        <p className="text-sm text-gray-500">{error}</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div
        className={clsx('flex items-center justify-center', className)}
        style={{ height }}
      >
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-red-600" />
      </div>
    );
  }

  return (
    <div className={clsx('w-full', className)}>
      <ResponsiveContainer width={width} height={height}>
        <AreaChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={colors.grid} vertical={false} />
          
          <XAxis
            dataKey="date"
            tickFormatter={formatDate}
            stroke={colors.text}
            tick={{ fill: colors.text, fontSize: 12 }}
            axisLine={{ stroke: colors.grid }}
            tickLine={{ stroke: colors.grid }}
          />
          
          <YAxis
            tickFormatter={formatPercent}
            stroke={colors.text}
            tick={{ fill: colors.text, fontSize: 12 }}
            axisLine={{ stroke: colors.grid }}
            tickLine={{ stroke: colors.grid }}
            domain={[minDrawdown, 0]}
          />

          <Tooltip content={<CustomTooltip />} />
          
          <ReferenceLine y={0} stroke={colors.grid} strokeWidth={2} />
          
          <Area
            type="monotone"
            dataKey="drawdown"
            stroke={colors.stroke}
            fill={colors.fill}
            strokeWidth={2}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

export default DrawdownChart;
