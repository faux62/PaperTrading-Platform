/**
 * PerformanceChart Component
 * 
 * Line/Area chart for portfolio performance visualization:
 * - Portfolio value over time
 * - Benchmark comparison
 * - Interactive tooltip
 * - Responsive design
 */
import React, { useMemo } from 'react';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine,
} from 'recharts';
import { clsx } from 'clsx';
import type { PerformanceChartProps, PerformanceData } from './types';
import { RechartsTooltip } from './ChartTooltip';

// Format currency for axis
const formatCurrency = (value: number): string => {
  if (value >= 1000000) {
    return `$${(value / 1000000).toFixed(1)}M`;
  }
  if (value >= 1000) {
    return `$${(value / 1000).toFixed(0)}K`;
  }
  return `$${value.toFixed(0)}`;
};

// Format percentage
const formatPercent = (value: number): string => {
  return `${(value * 100).toFixed(1)}%`;
};

// Format date for axis
const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
};

export const PerformanceChart: React.FC<PerformanceChartProps> = ({
  data,
  showBenchmark = true,
  benchmarkLabel = 'Benchmark',
  valueLabel = 'Portfolio',
  width = '100%',
  height = 300,
  theme = 'light',
  loading = false,
  error,
  className,
  showGrid = true,
  showTooltip = true,
  areaFill = true,
}) => {
  const isDark = theme === 'dark';

  // Theme colors
  const colors = useMemo(
    () => ({
      primary: '#3b82f6',
      benchmark: '#9ca3af',
      grid: isDark ? '#374151' : '#e5e7eb',
      text: isDark ? '#9ca3af' : '#6b7280',
      background: isDark ? '#1f2937' : '#ffffff',
      area: isDark ? 'rgba(59, 130, 246, 0.1)' : 'rgba(59, 130, 246, 0.2)',
    }),
    [isDark]
  );

  // Calculate min/max for better axis display
  const { minValue, maxValue, hasNegative } = useMemo(() => {
    if (data.length === 0) return { minValue: 0, maxValue: 100, hasNegative: false };

    const values = data.flatMap((d) => [d.value, d.benchmark].filter(Boolean) as number[]);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const padding = (max - min) * 0.1;

    return {
      minValue: Math.floor(min - padding),
      maxValue: Math.ceil(max + padding),
      hasNegative: min < 0,
    };
  }, [data]);

  // Custom tooltip formatter
  const tooltipFormatter = (value: number, name: string) => {
    return formatCurrency(value);
  };

  if (error) {
    return (
      <div
        className={clsx('flex items-center justify-center', className)}
        style={{ height }}
      >
        <div className="text-center text-gray-500">
          <svg
            className="mx-auto h-12 w-12 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
            />
          </svg>
          <p className="mt-2 text-sm">{error}</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div
        className={clsx('flex items-center justify-center', className)}
        style={{ height }}
      >
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  const ChartComponent = areaFill ? AreaChart : LineChart;

  return (
    <div className={clsx('w-full', className)}>
      <ResponsiveContainer width={width} height={height}>
        <ChartComponent data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
          {showGrid && (
            <CartesianGrid strokeDasharray="3 3" stroke={colors.grid} vertical={false} />
          )}
          
          <XAxis
            dataKey="date"
            tickFormatter={formatDate}
            stroke={colors.text}
            tick={{ fill: colors.text, fontSize: 12 }}
            axisLine={{ stroke: colors.grid }}
            tickLine={{ stroke: colors.grid }}
          />
          
          <YAxis
            tickFormatter={formatCurrency}
            stroke={colors.text}
            tick={{ fill: colors.text, fontSize: 12 }}
            axisLine={{ stroke: colors.grid }}
            tickLine={{ stroke: colors.grid }}
            domain={[minValue, maxValue]}
          />

          {showTooltip && (
            <Tooltip
              content={
                <RechartsTooltip formatter={tooltipFormatter} />
              }
            />
          )}

          <Legend
            wrapperStyle={{ paddingTop: 10 }}
            formatter={(value) => (
              <span className={isDark ? 'text-gray-300' : 'text-gray-700'}>{value}</span>
            )}
          />

          {/* Zero reference line if needed */}
          {hasNegative && <ReferenceLine y={0} stroke={colors.grid} strokeDasharray="3 3" />}

          {/* Benchmark line (rendered first so portfolio is on top) */}
          {showBenchmark && (
            areaFill ? (
              <Area
                type="monotone"
                dataKey="benchmark"
                name={benchmarkLabel}
                stroke={colors.benchmark}
                fill="transparent"
                strokeWidth={2}
                strokeDasharray="5 5"
                dot={false}
              />
            ) : (
              <Line
                type="monotone"
                dataKey="benchmark"
                name={benchmarkLabel}
                stroke={colors.benchmark}
                strokeWidth={2}
                strokeDasharray="5 5"
                dot={false}
              />
            )
          )}

          {/* Portfolio line/area */}
          {areaFill ? (
            <Area
              type="monotone"
              dataKey="value"
              name={valueLabel}
              stroke={colors.primary}
              fill={colors.area}
              strokeWidth={2}
              dot={false}
            />
          ) : (
            <Line
              type="monotone"
              dataKey="value"
              name={valueLabel}
              stroke={colors.primary}
              strokeWidth={2}
              dot={false}
            />
          )}
        </ChartComponent>
      </ResponsiveContainer>
    </div>
  );
};

// Export a simpler line chart variant
export const SimpleLineChart: React.FC<{
  data: Array<{ date: string; value: number }>;
  height?: number;
  color?: string;
  showAxis?: boolean;
  className?: string;
}> = ({ data, height = 60, color = '#3b82f6', showAxis = false, className }) => {
  return (
    <div className={clsx('w-full', className)}>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data}>
          {showAxis && (
            <>
              <XAxis dataKey="date" hide />
              <YAxis hide />
            </>
          )}
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default PerformanceChart;
