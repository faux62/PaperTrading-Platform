/**
 * ROCCurve Component
 * 
 * ROC Curve visualization for binary classification models
 */
import React, { useMemo } from 'react';
import { clsx } from 'clsx';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
} from 'recharts';

interface ROCPoint {
  fpr: number; // False Positive Rate (x-axis)
  tpr: number; // True Positive Rate (y-axis)
  threshold?: number;
}

interface ROCCurveProps {
  data: ROCPoint[];
  auc?: number; // Area Under Curve
  title?: string;
  height?: number;
  loading?: boolean;
  className?: string;
}

// Custom tooltip
const CustomTooltip: React.FC<any> = ({ active, payload }) => {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  const point = payload[0].payload as ROCPoint;

  return (
    <div className="bg-white dark:bg-gray-800 shadow-lg rounded-lg border border-gray-200 dark:border-gray-700 p-3">
      <div className="space-y-1 text-sm">
        <div className="flex justify-between gap-4">
          <span className="text-gray-500">FPR:</span>
          <span className="font-medium">{(point.fpr * 100).toFixed(1)}%</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-gray-500">TPR:</span>
          <span className="font-medium">{(point.tpr * 100).toFixed(1)}%</span>
        </div>
        {point.threshold !== undefined && (
          <div className="flex justify-between gap-4 pt-1 border-t border-gray-200 dark:border-gray-700">
            <span className="text-gray-500">Threshold:</span>
            <span className="font-medium">{point.threshold.toFixed(2)}</span>
          </div>
        )}
      </div>
    </div>
  );
};

export const ROCCurve: React.FC<ROCCurveProps> = ({
  data,
  auc = 0,
  title = 'ROC Curve',
  height = 300,
  loading = false,
  className,
}) => {
  // Format axis ticks
  const formatPercent = (value: number) => `${(value * 100).toFixed(0)}%`;

  // Generate random baseline points
  const baselineDiagonal = useMemo(() => {
    return Array.from({ length: 11 }, (_, i) => ({
      fpr: i / 10,
      tpr: i / 10,
    }));
  }, []);

  // AUC rating
  const getAUCRating = (aucValue: number): { label: string; color: string } => {
    if (aucValue >= 0.9) return { label: 'Excellent', color: 'text-green-600' };
    if (aucValue >= 0.8) return { label: 'Good', color: 'text-blue-600' };
    if (aucValue >= 0.7) return { label: 'Fair', color: 'text-yellow-600' };
    if (aucValue >= 0.6) return { label: 'Poor', color: 'text-orange-600' };
    return { label: 'Fail', color: 'text-red-600' };
  };

  const aucRating = getAUCRating(auc);

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
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500 dark:text-gray-400">AUC:</span>
          <span className={clsx('text-lg font-bold', aucRating.color)}>
            {auc.toFixed(3)}
          </span>
          <span className={clsx('text-xs px-2 py-0.5 rounded', aucRating.color, 'bg-opacity-10')}>
            {aucRating.label}
          </span>
        </div>
      </div>

      {/* Chart */}
      <div className="p-4">
        <ResponsiveContainer width="100%" height={height}>
          <LineChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            
            <XAxis
              type="number"
              dataKey="fpr"
              domain={[0, 1]}
              tickFormatter={formatPercent}
              stroke="#9ca3af"
              fontSize={12}
              label={{
                value: 'False Positive Rate',
                position: 'bottom',
                offset: 0,
                fill: '#6b7280',
                fontSize: 12,
              }}
            />
            
            <YAxis
              type="number"
              dataKey="tpr"
              domain={[0, 1]}
              tickFormatter={formatPercent}
              stroke="#9ca3af"
              fontSize={12}
              label={{
                value: 'True Positive Rate',
                angle: -90,
                position: 'insideLeft',
                fill: '#6b7280',
                fontSize: 12,
              }}
            />
            
            <Tooltip content={<CustomTooltip />} />

            {/* Diagonal baseline */}
            <Line
              data={baselineDiagonal}
              type="linear"
              dataKey="tpr"
              stroke="#d1d5db"
              strokeDasharray="5 5"
              dot={false}
              isAnimationActive={false}
            />

            {/* ROC Curve with area */}
            <Area
              data={data}
              type="monotone"
              dataKey="tpr"
              fill="#3b82f6"
              fillOpacity={0.1}
              stroke="none"
            />
            
            <Line
              data={data}
              type="monotone"
              dataKey="tpr"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: '#3b82f6' }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Legend */}
      <div className="px-4 pb-4 flex items-center justify-center gap-6 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-4 h-0.5 bg-blue-500" />
          <span className="text-gray-600 dark:text-gray-400">ROC Curve</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-0.5 bg-gray-300" style={{ borderStyle: 'dashed' }} />
          <span className="text-gray-600 dark:text-gray-400">Random Classifier</span>
        </div>
      </div>
    </div>
  );
};

export default ROCCurve;
