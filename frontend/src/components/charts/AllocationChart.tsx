/**
 * AllocationChart Component
 * 
 * Pie/Donut chart for portfolio allocation visualization:
 * - Asset allocation breakdown
 * - Sector allocation
 * - Interactive hover states
 * - Customizable colors
 */
import React, { useState, useMemo } from 'react';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
  Sector,
} from 'recharts';
import { clsx } from 'clsx';
import type { AllocationChartProps, AllocationData } from './types';

// Default color palette
const DEFAULT_COLORS = [
  '#3b82f6', // blue
  '#10b981', // emerald
  '#f59e0b', // amber
  '#ef4444', // red
  '#8b5cf6', // violet
  '#ec4899', // pink
  '#06b6d4', // cyan
  '#84cc16', // lime
  '#f97316', // orange
  '#6366f1', // indigo
];

// Format percentage
const formatPercent = (value: number, total: number): string => {
  return `${((value / total) * 100).toFixed(1)}%`;
};

// Format currency
const formatCurrency = (value: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
};

// Active shape for hover effect
const renderActiveShape = (props: any) => {
  const {
    cx,
    cy,
    innerRadius,
    outerRadius,
    startAngle,
    endAngle,
    fill,
    payload,
    percent,
    value,
  } = props;

  return (
    <g>
      <text
        x={cx}
        y={cy - 10}
        textAnchor="middle"
        fill={fill}
        className="text-lg font-semibold"
      >
        {payload.name}
      </text>
      <text
        x={cx}
        y={cy + 15}
        textAnchor="middle"
        fill="#6b7280"
        className="text-sm"
      >
        {formatCurrency(value)}
      </text>
      <text
        x={cx}
        y={cy + 35}
        textAnchor="middle"
        fill="#9ca3af"
        className="text-xs"
      >
        {`${(percent * 100).toFixed(1)}%`}
      </text>
      <Sector
        cx={cx}
        cy={cy}
        innerRadius={innerRadius}
        outerRadius={outerRadius + 8}
        startAngle={startAngle}
        endAngle={endAngle}
        fill={fill}
      />
      <Sector
        cx={cx}
        cy={cy}
        startAngle={startAngle}
        endAngle={endAngle}
        innerRadius={outerRadius + 10}
        outerRadius={outerRadius + 14}
        fill={fill}
      />
    </g>
  );
};

// Custom tooltip
const CustomTooltip: React.FC<any> = ({ active, payload }) => {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  const data = payload[0];
  const { name, value, payload: itemPayload } = data;
  const color = itemPayload.color || data.color;
  const percentage = itemPayload.percentage;

  return (
    <div className="bg-white dark:bg-gray-800 shadow-lg rounded-lg border border-gray-200 dark:border-gray-700 p-3">
      <div className="flex items-center gap-2 mb-1">
        <span
          className="w-3 h-3 rounded-sm"
          style={{ backgroundColor: color }}
        />
        <span className="font-medium text-gray-900 dark:text-white">{name}</span>
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-300">
        <div>{formatCurrency(value)}</div>
        {percentage !== undefined && (
          <div className="text-gray-500">{percentage.toFixed(1)}%</div>
        )}
      </div>
    </div>
  );
};

// Custom legend
const CustomLegend: React.FC<{
  payload?: Array<{
    value: string;
    color: string;
    payload: AllocationData;
  }>;
  total: number;
}> = ({ payload, total }) => {
  if (!payload) return null;

  return (
    <div className="flex flex-wrap justify-center gap-x-4 gap-y-2 mt-4">
      {payload.map((entry, index) => (
        <div key={`legend-${index}`} className="flex items-center gap-2 text-sm">
          <span
            className="w-3 h-3 rounded-sm flex-shrink-0"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-gray-700 dark:text-gray-300">{entry.value}</span>
          <span className="text-gray-500">
            {formatPercent(entry.payload.value, total)}
          </span>
        </div>
      ))}
    </div>
  );
};

export const AllocationChart: React.FC<AllocationChartProps> = ({
  data,
  width = '100%',
  height = 300,
  theme: _theme = 'light',
  loading = false,
  error,
  className,
  showLabels = false,
  showLegend = true,
  innerRadius = 60,
  outerRadius = 100,
  animate = true,
}) => {
  const [activeIndex, setActiveIndex] = useState<number | undefined>(undefined);

  // Calculate total and add colors
  const { chartData, total } = useMemo(() => {
    const sum = data.reduce((acc, item) => acc + item.value, 0);
    const processed = data.map((item, index) => ({
      ...item,
      color: item.color || DEFAULT_COLORS[index % DEFAULT_COLORS.length],
      percentage: (item.value / sum) * 100,
    }));
    return { chartData: processed, total: sum };
  }, [data]);

  const onPieEnter = (_: any, index: number) => {
    setActiveIndex(index);
  };

  const onPieLeave = () => {
    setActiveIndex(undefined);
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
              d="M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z"
            />
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z"
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

  return (
    <div className={clsx('w-full', className)}>
      <ResponsiveContainer width={width} height={height}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius={innerRadius}
            outerRadius={outerRadius}
            dataKey="value"
            nameKey="name"
            activeIndex={activeIndex}
            activeShape={renderActiveShape}
            onMouseEnter={onPieEnter}
            onMouseLeave={onPieLeave}
            isAnimationActive={animate}
            label={
              showLabels
                ? ({ name, percent }) =>
                    `${name} ${(percent * 100).toFixed(0)}%`
                : undefined
            }
            labelLine={showLabels}
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          
          <Tooltip content={<CustomTooltip />} />
          
          {showLegend && (
            <Legend
              content={<CustomLegend total={total} />}
              verticalAlign="bottom"
            />
          )}
        </PieChart>
      </ResponsiveContainer>

      {/* Center text when no segment is active */}
      {activeIndex === undefined && innerRadius > 0 && (
        <div
          className="absolute inset-0 flex items-center justify-center pointer-events-none"
          style={{ marginTop: -height * 0.15 }}
        >
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {formatCurrency(total)}
            </div>
            <div className="text-sm text-gray-500">Total</div>
          </div>
        </div>
      )}
    </div>
  );
};

// Simple donut variant for smaller displays
export const MiniAllocationChart: React.FC<{
  data: AllocationData[];
  size?: number;
  className?: string;
}> = ({ data, size = 120, className }) => {
  const chartData = useMemo(() => {
    return data.map((item, index) => ({
      ...item,
      color: item.color || DEFAULT_COLORS[index % DEFAULT_COLORS.length],
    }));
  }, [data]);

  return (
    <div className={clsx('relative', className)} style={{ width: size, height: size }}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius={size * 0.3}
            outerRadius={size * 0.45}
            dataKey="value"
            isAnimationActive={false}
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
};

export default AllocationChart;
