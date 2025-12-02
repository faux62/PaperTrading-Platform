/**
 * FeatureImportanceChart Component
 * 
 * Horizontal bar chart for feature importance visualization
 */
import React, { useMemo } from 'react';
import { clsx } from 'clsx';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from 'recharts';

interface Feature {
  name: string;
  importance: number;
  category?: string;
}

interface FeatureImportanceChartProps {
  features: Feature[];
  maxFeatures?: number;
  title?: string;
  height?: number;
  showCategories?: boolean;
  loading?: boolean;
  className?: string;
}

// Category colors
const categoryColors: Record<string, string> = {
  price: '#3b82f6',
  volume: '#10b981',
  technical: '#8b5cf6',
  fundamental: '#f59e0b',
  sentiment: '#ec4899',
  market: '#06b6d4',
  default: '#6b7280',
};

// Custom tooltip
const CustomTooltip: React.FC<any> = ({ active, payload }) => {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  const feature = payload[0].payload as Feature;

  return (
    <div className="bg-white dark:bg-gray-800 shadow-lg rounded-lg border border-gray-200 dark:border-gray-700 p-3">
      <p className="font-medium text-gray-900 dark:text-white mb-1">{feature.name}</p>
      <div className="space-y-1 text-sm">
        <div className="flex justify-between gap-4">
          <span className="text-gray-500">Importance:</span>
          <span className="font-medium text-blue-600">
            {(feature.importance * 100).toFixed(2)}%
          </span>
        </div>
        {feature.category && (
          <div className="flex justify-between gap-4">
            <span className="text-gray-500">Category:</span>
            <span className="font-medium capitalize">{feature.category}</span>
          </div>
        )}
      </div>
    </div>
  );
};

export const FeatureImportanceChart: React.FC<FeatureImportanceChartProps> = ({
  features,
  maxFeatures = 15,
  title = 'Feature Importance',
  height = 400,
  showCategories = true,
  loading = false,
  className,
}) => {
  // Sort and limit features
  const chartData = useMemo(() => {
    return [...features]
      .sort((a, b) => b.importance - a.importance)
      .slice(0, maxFeatures)
      .reverse(); // Reverse for horizontal bar chart (top to bottom)
  }, [features, maxFeatures]);

  // Get color for feature based on category
  const getFeatureColor = (feature: Feature) => {
    if (!showCategories || !feature.category) {
      return '#3b82f6';
    }
    return categoryColors[feature.category] || categoryColors.default;
  };

  // Calculate dynamic height based on number of features
  const dynamicHeight = Math.max(height, chartData.length * 30 + 80);

  if (loading) {
    return (
      <div className={clsx('bg-white dark:bg-gray-800 rounded-lg p-6 animate-pulse', className)}>
        <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-6" />
        <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded" />
      </div>
    );
  }

  return (
    <div className={clsx(
      'bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700',
      className
    )}>
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
        <h3 className="font-semibold text-gray-900 dark:text-white">{title}</h3>
        <span className="text-sm text-gray-500 dark:text-gray-400">
          Top {chartData.length} features
        </span>
      </div>

      {/* Chart */}
      <div className="p-4">
        <ResponsiveContainer width="100%" height={dynamicHeight}>
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ top: 5, right: 30, left: 100, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" horizontal={false} />
            
            <XAxis
              type="number"
              domain={[0, 'dataMax']}
              tickFormatter={(value) => `${(value * 100).toFixed(0)}%`}
              stroke="#9ca3af"
              fontSize={12}
            />
            
            <YAxis
              type="category"
              dataKey="name"
              stroke="#9ca3af"
              fontSize={11}
              width={90}
              tick={{ fill: '#6b7280' }}
            />
            
            <Tooltip content={<CustomTooltip />} />
            
            <ReferenceLine x={0} stroke="#9ca3af" />
            
            <Bar dataKey="importance" radius={[0, 4, 4, 0]}>
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={getFeatureColor(entry)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Category Legend */}
      {showCategories && (
        <div className="px-4 pb-4 flex flex-wrap items-center justify-center gap-4 text-sm">
          {Object.entries(categoryColors)
            .filter(([key]) => key !== 'default')
            .map(([category, color]) => (
              <div key={category} className="flex items-center gap-1.5">
                <div
                  className="w-3 h-3 rounded"
                  style={{ backgroundColor: color }}
                />
                <span className="text-gray-600 dark:text-gray-400 capitalize">
                  {category}
                </span>
              </div>
            ))}
        </div>
      )}
    </div>
  );
};

export default FeatureImportanceChart;
