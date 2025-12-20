/**
 * RiskMetrics Component
 * 
 * Displays risk metrics with visual indicators
 */
import React from 'react';
import { clsx } from 'clsx';
import { 
  ShieldAlert, 
  TrendingDown, 
  Activity,
  AlertTriangle,
  Gauge,
} from 'lucide-react';
import { MetricsCard } from './MetricsCard';

interface RiskData {
  var95: number | null;
  var99: number | null;
  cvar95: number | null;
  beta: number | null;
  alpha: number | null;
  rSquared: number | null;
  skewness?: number | null;
  kurtosis?: number | null;
  hasEnoughData?: boolean; // Flag to indicate if we have real calculated data
}

interface RiskMetricsProps {
  data: RiskData;
  loading?: boolean;
  className?: string;
}

// Risk level indicator (available for future use)
const _RiskIndicator: React.FC<{ level: 'low' | 'medium' | 'high' }> = ({ level }) => {
  const colors = {
    low: 'bg-green-500',
    medium: 'bg-yellow-500',
    high: 'bg-red-500',
  };

  return (
    <div className="flex items-center gap-1">
      <span className={clsx('w-2 h-2 rounded-full', colors[level])} />
      <span className="text-xs text-gray-500 capitalize">{level}</span>
    </div>
  );
};

// Keep for linting - exports
void _RiskIndicator;

// Determine risk level from VaR
const getRiskLevel = (var95: number | null, hasEnoughData?: boolean): 'low' | 'medium' | 'high' | 'unknown' => {
  if (var95 === null || !hasEnoughData) return 'unknown';
  const absVaR = Math.abs(var95);
  if (absVaR < 0.02) return 'low';
  if (absVaR < 0.05) return 'medium';
  return 'high';
};

export const RiskMetrics: React.FC<RiskMetricsProps> = ({
  data,
  loading = false,
  className,
}) => {
  if (loading) {
    return (
      <div className={clsx('grid grid-cols-2 md:grid-cols-3 gap-4', className)}>
        {Array.from({ length: 6 }).map((_, i) => (
          <div
            key={i}
            className="bg-white dark:bg-gray-800 rounded-lg p-4 animate-pulse"
          >
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2 mb-2" />
            <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-3/4" />
          </div>
        ))}
      </div>
    );
  }

  const riskLevel = getRiskLevel(data.var95, data.hasEnoughData);

  return (
    <div className={clsx('space-y-6', className)}>
      {/* Risk Level Summary */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={clsx(
              'p-3 rounded-lg',
              riskLevel === 'low' && 'bg-green-50 dark:bg-green-900/20',
              riskLevel === 'medium' && 'bg-yellow-50 dark:bg-yellow-900/20',
              riskLevel === 'high' && 'bg-red-50 dark:bg-red-900/20',
              riskLevel === 'unknown' && 'bg-gray-50 dark:bg-gray-700/20'
            )}>
              <ShieldAlert className={clsx(
                'w-6 h-6',
                riskLevel === 'low' && 'text-green-600',
                riskLevel === 'medium' && 'text-yellow-600',
                riskLevel === 'high' && 'text-red-600',
                riskLevel === 'unknown' && 'text-gray-400'
              )} />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 dark:text-white">
                Overall Risk Level
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Based on VaR and volatility metrics
              </p>
            </div>
          </div>
          <div className={clsx(
            'px-4 py-2 rounded-full font-semibold text-sm',
            riskLevel === 'low' && 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
            riskLevel === 'medium' && 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
            riskLevel === 'high' && 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
            riskLevel === 'unknown' && 'bg-gray-100 text-gray-600 dark:bg-gray-700/30 dark:text-gray-400'
          )}>
            {riskLevel === 'unknown' ? 'DATI INSUFFICIENTI' : `${riskLevel.toUpperCase()} RISK`}
          </div>
        </div>
      </div>

      {/* Risk Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <MetricsCard
          label="VaR (95%)"
          value={data.var95}
          format="percent"
          icon={<AlertTriangle className="w-5 h-5 text-red-600" />}
          description="Daily potential loss at 95% confidence"
        />
        
        <MetricsCard
          label="VaR (99%)"
          value={data.var99}
          format="percent"
          icon={<AlertTriangle className="w-5 h-5 text-red-700" />}
          description="Daily potential loss at 99% confidence"
        />
        
        <MetricsCard
          label="CVaR (95%)"
          value={data.cvar95}
          format="percent"
          icon={<TrendingDown className="w-5 h-5 text-orange-600" />}
          description="Expected loss beyond VaR"
        />
        
        <MetricsCard
          label="Beta"
          value={data.beta}
          format="number"
          icon={<Activity className="w-5 h-5 text-blue-600" />}
          description={data.beta !== null ? (data.beta > 1 ? 'More volatile than market' : 'Less volatile than market') : undefined}
        />
        
        <MetricsCard
          label="Alpha"
          value={data.alpha}
          format="percent"
          icon={<Gauge className="w-5 h-5 text-green-600" />}
          trend={data.alpha !== null ? (data.alpha > 0 ? 'up' : data.alpha < 0 ? 'down' : 'neutral') : undefined}
          description={data.alpha !== null ? 'Excess return vs benchmark' : undefined}
        />
        
        <MetricsCard
          label="R-Squared"
          value={data.rSquared}
          format="percent"
          icon={<Activity className="w-5 h-5 text-purple-600" />}
          description="Correlation with benchmark"
        />
      </div>

      {/* Additional Tail Risk Metrics */}
      {(data.skewness !== undefined || data.kurtosis !== undefined) && (
        <div className="grid grid-cols-2 gap-4">
          {data.skewness !== undefined && (
            <MetricsCard
              label="Skewness"
              value={data.skewness}
              format="number"
              description={data.skewness !== null ? (data.skewness < 0 ? 'Negative skew (left tail risk)' : 'Positive skew (right tail bias)') : undefined}
            />
          )}
          {data.kurtosis !== undefined && (
            <MetricsCard
              label="Kurtosis"
              value={data.kurtosis}
              format="number"
              description={data.kurtosis !== null ? (data.kurtosis > 3 ? 'Fat tails (more extreme events)' : 'Thin tails (fewer extremes)') : undefined}
            />
          )}
        </div>
      )}
    </div>
  );
};

export default RiskMetrics;
