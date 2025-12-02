/**
 * PredictionCard Component
 * 
 * Displays ML model prediction for a stock
 */
import React from 'react';
import { clsx } from 'clsx';
import { 
  TrendingUp, 
  TrendingDown, 
  Minus,
  Brain,
  Clock,
} from 'lucide-react';

export type PredictionDirection = 'bullish' | 'bearish' | 'neutral';

interface PredictionCardProps {
  symbol: string;
  direction: PredictionDirection;
  confidence: number; // 0-1
  predictedChange: number; // predicted % change
  timeHorizon: string; // e.g., "1 Day", "1 Week"
  modelName?: string;
  lastUpdated?: Date;
  className?: string;
}

export const PredictionCard: React.FC<PredictionCardProps> = ({
  symbol,
  direction,
  confidence,
  predictedChange,
  timeHorizon,
  modelName = 'LSTM Predictor',
  lastUpdated,
  className,
}) => {
  const directionConfig = {
    bullish: {
      icon: TrendingUp,
      color: 'text-green-600',
      bg: 'bg-green-50 dark:bg-green-900/20',
      border: 'border-green-200 dark:border-green-800',
      label: 'Bullish',
    },
    bearish: {
      icon: TrendingDown,
      color: 'text-red-600',
      bg: 'bg-red-50 dark:bg-red-900/20',
      border: 'border-red-200 dark:border-red-800',
      label: 'Bearish',
    },
    neutral: {
      icon: Minus,
      color: 'text-gray-600',
      bg: 'bg-gray-50 dark:bg-gray-700',
      border: 'border-gray-200 dark:border-gray-600',
      label: 'Neutral',
    },
  };

  const config = directionConfig[direction];
  const Icon = config.icon;

  // Confidence level text
  const getConfidenceLabel = (conf: number) => {
    if (conf >= 0.8) return 'High';
    if (conf >= 0.6) return 'Medium';
    return 'Low';
  };

  const confidencePercent = Math.round(confidence * 100);

  return (
    <div
      className={clsx(
        'rounded-lg border p-4 transition-shadow hover:shadow-md',
        config.bg,
        config.border,
        className
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className={clsx('p-2 rounded-lg', config.bg)}>
            <Icon className={clsx('w-5 h-5', config.color)} />
          </div>
          <div>
            <h3 className="font-bold text-gray-900 dark:text-white">{symbol}</h3>
            <span className={clsx('text-sm font-medium', config.color)}>
              {config.label}
            </span>
          </div>
        </div>
        <div className="text-right">
          <span className={clsx('text-2xl font-bold', config.color)}>
            {predictedChange >= 0 ? '+' : ''}{predictedChange.toFixed(1)}%
          </span>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {timeHorizon} forecast
          </p>
        </div>
      </div>

      {/* Confidence Bar */}
      <div className="mb-3">
        <div className="flex justify-between text-xs mb-1">
          <span className="text-gray-500 dark:text-gray-400">Confidence</span>
          <span className={clsx('font-medium', config.color)}>
            {confidencePercent}% ({getConfidenceLabel(confidence)})
          </span>
        </div>
        <div className="h-2 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
          <div
            className={clsx(
              'h-full rounded-full transition-all duration-500',
              direction === 'bullish' && 'bg-green-500',
              direction === 'bearish' && 'bg-red-500',
              direction === 'neutral' && 'bg-gray-500'
            )}
            style={{ width: `${confidencePercent}%` }}
          />
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
        <div className="flex items-center gap-1">
          <Brain className="w-3 h-3" />
          <span>{modelName}</span>
        </div>
        {lastUpdated && (
          <div className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            <span>{lastUpdated.toLocaleTimeString()}</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default PredictionCard;
