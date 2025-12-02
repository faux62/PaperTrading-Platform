/**
 * ConfusionMatrix Component
 * 
 * Visualize ML model confusion matrix
 */
import React from 'react';
import { clsx } from 'clsx';

interface ConfusionMatrixData {
  truePositive: number;
  falsePositive: number;
  trueNegative: number;
  falseNegative: number;
}

interface ConfusionMatrixProps {
  data: ConfusionMatrixData;
  labels?: { positive: string; negative: string };
  title?: string;
  loading?: boolean;
  className?: string;
}

export const ConfusionMatrix: React.FC<ConfusionMatrixProps> = ({
  data,
  labels = { positive: 'UP', negative: 'DOWN' },
  title = 'Confusion Matrix',
  loading = false,
  className,
}) => {
  const total = data.truePositive + data.falsePositive + data.trueNegative + data.falseNegative;
  
  // Calculate metrics
  const accuracy = total > 0 
    ? (data.truePositive + data.trueNegative) / total 
    : 0;
  const precision = (data.truePositive + data.falsePositive) > 0
    ? data.truePositive / (data.truePositive + data.falsePositive)
    : 0;
  const recall = (data.truePositive + data.falseNegative) > 0
    ? data.truePositive / (data.truePositive + data.falseNegative)
    : 0;
  const f1Score = (precision + recall) > 0
    ? (2 * precision * recall) / (precision + recall)
    : 0;

  // Get percentage
  const getPercentage = (value: number) => 
    total > 0 ? ((value / total) * 100).toFixed(1) : '0.0';

  // Cell color intensity based on percentage
  const getCellColor = (value: number, isCorrect: boolean) => {
    const pct = total > 0 ? value / total : 0;
    const intensity = Math.min(pct * 3, 1); // Scale up for visibility
    
    if (isCorrect) {
      return `rgba(34, 197, 94, ${0.2 + intensity * 0.6})`; // Green
    }
    return `rgba(239, 68, 68, ${0.2 + intensity * 0.6})`; // Red
  };

  if (loading) {
    return (
      <div className={clsx('bg-white dark:bg-gray-800 rounded-lg p-6 animate-pulse', className)}>
        <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-6" />
        <div className="h-48 bg-gray-200 dark:bg-gray-700 rounded" />
      </div>
    );
  }

  return (
    <div className={clsx(
      'bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700',
      className
    )}>
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <h3 className="font-semibold text-gray-900 dark:text-white">{title}</h3>
      </div>

      {/* Matrix */}
      <div className="p-4">
        <div className="flex">
          {/* Y-axis label */}
          <div className="flex flex-col justify-center items-center w-12 -mr-2">
            <span className="text-xs text-gray-500 dark:text-gray-400 transform -rotate-90 whitespace-nowrap">
              Actual
            </span>
          </div>

          <div className="flex-1">
            {/* X-axis label */}
            <div className="text-center mb-2">
              <span className="text-xs text-gray-500 dark:text-gray-400">Predicted</span>
            </div>

            {/* Header row */}
            <div className="grid grid-cols-3 gap-1 mb-1">
              <div /> {/* Empty corner */}
              <div className="text-center text-xs font-medium text-gray-600 dark:text-gray-400 py-1">
                {labels.positive}
              </div>
              <div className="text-center text-xs font-medium text-gray-600 dark:text-gray-400 py-1">
                {labels.negative}
              </div>
            </div>

            {/* Actual Positive row */}
            <div className="grid grid-cols-3 gap-1 mb-1">
              <div className="text-right text-xs font-medium text-gray-600 dark:text-gray-400 pr-2 flex items-center justify-end">
                {labels.positive}
              </div>
              <div
                className="rounded-lg p-3 text-center transition-colors"
                style={{ backgroundColor: getCellColor(data.truePositive, true) }}
              >
                <div className="text-lg font-bold text-gray-900 dark:text-white">
                  {data.truePositive}
                </div>
                <div className="text-xs text-gray-600 dark:text-gray-400">
                  {getPercentage(data.truePositive)}%
                </div>
                <div className="text-xs text-green-600 mt-1">TP</div>
              </div>
              <div
                className="rounded-lg p-3 text-center transition-colors"
                style={{ backgroundColor: getCellColor(data.falseNegative, false) }}
              >
                <div className="text-lg font-bold text-gray-900 dark:text-white">
                  {data.falseNegative}
                </div>
                <div className="text-xs text-gray-600 dark:text-gray-400">
                  {getPercentage(data.falseNegative)}%
                </div>
                <div className="text-xs text-red-600 mt-1">FN</div>
              </div>
            </div>

            {/* Actual Negative row */}
            <div className="grid grid-cols-3 gap-1">
              <div className="text-right text-xs font-medium text-gray-600 dark:text-gray-400 pr-2 flex items-center justify-end">
                {labels.negative}
              </div>
              <div
                className="rounded-lg p-3 text-center transition-colors"
                style={{ backgroundColor: getCellColor(data.falsePositive, false) }}
              >
                <div className="text-lg font-bold text-gray-900 dark:text-white">
                  {data.falsePositive}
                </div>
                <div className="text-xs text-gray-600 dark:text-gray-400">
                  {getPercentage(data.falsePositive)}%
                </div>
                <div className="text-xs text-red-600 mt-1">FP</div>
              </div>
              <div
                className="rounded-lg p-3 text-center transition-colors"
                style={{ backgroundColor: getCellColor(data.trueNegative, true) }}
              >
                <div className="text-lg font-bold text-gray-900 dark:text-white">
                  {data.trueNegative}
                </div>
                <div className="text-xs text-gray-600 dark:text-gray-400">
                  {getPercentage(data.trueNegative)}%
                </div>
                <div className="text-xs text-green-600 mt-1">TN</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Metrics Summary */}
      <div className="p-4 bg-gray-50 dark:bg-gray-700/50 border-t border-gray-200 dark:border-gray-700 grid grid-cols-4 gap-4">
        <div className="text-center">
          <div className="text-xs text-gray-500 dark:text-gray-400">Accuracy</div>
          <div className="text-lg font-bold text-gray-900 dark:text-white">
            {(accuracy * 100).toFixed(1)}%
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-500 dark:text-gray-400">Precision</div>
          <div className="text-lg font-bold text-gray-900 dark:text-white">
            {(precision * 100).toFixed(1)}%
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-500 dark:text-gray-400">Recall</div>
          <div className="text-lg font-bold text-gray-900 dark:text-white">
            {(recall * 100).toFixed(1)}%
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-500 dark:text-gray-400">F1 Score</div>
          <div className="text-lg font-bold text-gray-900 dark:text-white">
            {(f1Score * 100).toFixed(1)}%
          </div>
        </div>
      </div>
    </div>
  );
};

export default ConfusionMatrix;
