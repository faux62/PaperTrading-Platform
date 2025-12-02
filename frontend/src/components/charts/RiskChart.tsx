/**
 * RiskChart Component
 * 
 * Visualization of risk metrics over time:
 * - VaR (95% and 99%)
 * - CVaR/Expected Shortfall
 * - Rolling volatility
 */
import React, { useMemo } from 'react';
import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { clsx } from 'clsx';
import type { RiskChartProps, RiskData } from './types';

// Format percentage
const formatPercent = (value: number): string => {
  return `${(value * 100).toFixed(2)}%`;
};

// Format date
const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
};

// Custom tooltip
const CustomTooltip: React.FC<any> = ({ active, payload, label }) => {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  return (
    <div className="bg-white dark:bg-gray-800 shadow-lg rounded-lg border border-gray-200 dark:border-gray-700 p-3">
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">
        {formatDate(label)}
      </p>
      <div className="space-y-1">
        {payload.map((entry: any, index: number) => (
          <div key={index} className="flex items-center gap-2">
            <span
              className="w-3 h-3 rounded-sm flex-shrink-0"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-sm text-gray-600 dark:text-gray-300">
              {entry.name}:
            </span>
            <span className="text-sm font-semibold text-gray-900 dark:text-white">
              {formatPercent(entry.value)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export const RiskChart: React.FC<RiskChartProps> = ({
  data,
  width = '100%',
  height = 300,
  theme = 'light',
  loading = false,
  error,
  className,
  showVar99 = true,
  showCvar = true,
  showVolatility = false,
}) => {
  const isDark = theme === 'dark';

  const colors = useMemo(
    () => ({
      var95: '#ef4444',
      var99: '#dc2626',
      cvar: '#f97316',
      volatility: '#8b5cf6',
      grid: isDark ? '#374151' : '#e5e7eb',
      text: isDark ? '#9ca3af' : '#6b7280',
    }),
    [isDark]
  );

  // Calculate y-axis domain
  const yDomain = useMemo(() => {
    if (data.length === 0) return [-0.1, 0];
    
    const allValues = data.flatMap((d) => {
      const vals = [d.var95];
      if (d.var99 !== undefined) vals.push(d.var99);
      if (d.cvar !== undefined) vals.push(d.cvar);
      if (d.volatility !== undefined) vals.push(d.volatility);
      return vals;
    });
    
    const min = Math.min(...allValues);
    const max = Math.max(...allValues);
    const padding = Math.abs(max - min) * 0.1;
    
    return [min - padding, max + padding];
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
        <ComposedChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
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
            domain={yDomain}
          />

          <Tooltip content={<CustomTooltip />} />
          
          <Legend
            wrapperStyle={{ paddingTop: 10 }}
            formatter={(value) => (
              <span className={isDark ? 'text-gray-300' : 'text-gray-700'}>{value}</span>
            )}
          />

          {/* CVaR area */}
          {showCvar && (
            <Area
              type="monotone"
              dataKey="cvar"
              name="CVaR (95%)"
              stroke={colors.cvar}
              fill={`${colors.cvar}20`}
              strokeWidth={2}
            />
          )}

          {/* VaR 95% line */}
          <Line
            type="monotone"
            dataKey="var95"
            name="VaR (95%)"
            stroke={colors.var95}
            strokeWidth={2}
            dot={false}
          />

          {/* VaR 99% line */}
          {showVar99 && (
            <Line
              type="monotone"
              dataKey="var99"
              name="VaR (99%)"
              stroke={colors.var99}
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={false}
            />
          )}

          {/* Volatility line */}
          {showVolatility && (
            <Line
              type="monotone"
              dataKey="volatility"
              name="Volatility"
              stroke={colors.volatility}
              strokeWidth={2}
              dot={false}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
};

export default RiskChart;
