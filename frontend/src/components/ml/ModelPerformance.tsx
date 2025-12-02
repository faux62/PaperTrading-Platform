/**
 * ModelPerformance Component
 * 
 * Display ML model performance metrics
 */
import React from 'react';
import { clsx } from 'clsx';
import { 
  Brain,
  Target,
  TrendingUp,
  Clock,
  CheckCircle,
  XCircle,
} from 'lucide-react';

interface ModelMetrics {
  modelName: string;
  version: string;
  accuracy: number;
  precision: number;
  recall: number;
  f1Score: number;
  mse?: number;
  mae?: number;
  directionalAccuracy?: number;
  lastTrained?: Date;
  totalPredictions: number;
  correctPredictions: number;
}

interface ModelPerformanceProps {
  metrics: ModelMetrics;
  loading?: boolean;
  className?: string;
}

// Metric bar with label
const MetricBar: React.FC<{
  label: string;
  value: number;
  format?: 'percent' | 'decimal';
  showValue?: boolean;
}> = ({ label, value, format = 'percent', showValue = true }) => {
  const displayValue = format === 'percent' 
    ? `${(value * 100).toFixed(1)}%` 
    : value.toFixed(4);
  
  const barColor = value >= 0.8 
    ? 'bg-green-500' 
    : value >= 0.6 
    ? 'bg-yellow-500' 
    : 'bg-red-500';

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-gray-600 dark:text-gray-400">{label}</span>
        {showValue && (
          <span className="font-medium text-gray-900 dark:text-white">
            {displayValue}
          </span>
        )}
      </div>
      <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div
          className={clsx('h-full rounded-full transition-all duration-500', barColor)}
          style={{ width: `${Math.min(value * 100, 100)}%` }}
        />
      </div>
    </div>
  );
};

export const ModelPerformance: React.FC<ModelPerformanceProps> = ({
  metrics,
  loading = false,
  className,
}) => {
  if (loading) {
    return (
      <div className={clsx('bg-white dark:bg-gray-800 rounded-lg p-6 animate-pulse', className)}>
        <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-6" />
        <div className="space-y-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-8 bg-gray-200 dark:bg-gray-700 rounded" />
          ))}
        </div>
      </div>
    );
  }

  const successRate = metrics.totalPredictions > 0 
    ? metrics.correctPredictions / metrics.totalPredictions 
    : 0;

  return (
    <div className={clsx(
      'bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700',
      className
    )}>
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
              <Brain className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 dark:text-white">
                {metrics.modelName}
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                v{metrics.version}
              </p>
            </div>
          </div>
          {metrics.lastTrained && (
            <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
              <Clock className="w-3 h-3" />
              <span>
                Trained {metrics.lastTrained.toLocaleDateString()}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Overall Score */}
      <div className="p-4 bg-gray-50 dark:bg-gray-700/50 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Target className="w-5 h-5 text-blue-600" />
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Overall Accuracy
            </span>
          </div>
          <span className={clsx(
            'text-2xl font-bold',
            metrics.accuracy >= 0.7 ? 'text-green-600' : 
            metrics.accuracy >= 0.5 ? 'text-yellow-600' : 'text-red-600'
          )}>
            {(metrics.accuracy * 100).toFixed(1)}%
          </span>
        </div>
      </div>

      {/* Classification Metrics */}
      <div className="p-4 space-y-4">
        <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">
          Classification Metrics
        </h4>
        
        <MetricBar label="Precision" value={metrics.precision} />
        <MetricBar label="Recall" value={metrics.recall} />
        <MetricBar label="F1 Score" value={metrics.f1Score} />
        
        {metrics.directionalAccuracy !== undefined && (
          <MetricBar 
            label="Directional Accuracy" 
            value={metrics.directionalAccuracy} 
          />
        )}
      </div>

      {/* Regression Metrics (if available) */}
      {(metrics.mse !== undefined || metrics.mae !== undefined) && (
        <div className="p-4 border-t border-gray-200 dark:border-gray-700 space-y-4">
          <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400">
            Regression Metrics
          </h4>
          
          {metrics.mse !== undefined && (
            <div className="flex justify-between text-sm">
              <span className="text-gray-600 dark:text-gray-400">MSE</span>
              <span className="font-medium text-gray-900 dark:text-white">
                {metrics.mse.toFixed(6)}
              </span>
            </div>
          )}
          
          {metrics.mae !== undefined && (
            <div className="flex justify-between text-sm">
              <span className="text-gray-600 dark:text-gray-400">MAE</span>
              <span className="font-medium text-gray-900 dark:text-white">
                {metrics.mae.toFixed(6)}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Prediction Stats */}
      <div className="p-4 border-t border-gray-200 dark:border-gray-700">
        <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3">
          Production Statistics
        </h4>
        
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
            <div className="flex items-center gap-2 mb-1">
              <TrendingUp className="w-4 h-4 text-blue-600" />
              <span className="text-xs text-gray-500 dark:text-gray-400">
                Total Predictions
              </span>
            </div>
            <p className="text-lg font-bold text-gray-900 dark:text-white">
              {metrics.totalPredictions.toLocaleString()}
            </p>
          </div>
          
          <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
            <div className="flex items-center gap-2 mb-1">
              <CheckCircle className="w-4 h-4 text-green-600" />
              <span className="text-xs text-gray-500 dark:text-gray-400">
                Success Rate
              </span>
            </div>
            <p className="text-lg font-bold text-green-600">
              {(successRate * 100).toFixed(1)}%
            </p>
          </div>
        </div>
        
        <div className="mt-3 flex items-center justify-between text-sm">
          <div className="flex items-center gap-1 text-green-600">
            <CheckCircle className="w-4 h-4" />
            <span>{metrics.correctPredictions.toLocaleString()} correct</span>
          </div>
          <div className="flex items-center gap-1 text-red-600">
            <XCircle className="w-4 h-4" />
            <span>{(metrics.totalPredictions - metrics.correctPredictions).toLocaleString()} incorrect</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ModelPerformance;
