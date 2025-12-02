/**
 * FeatureImportance Component
 * 
 * Visualize ML model feature importance
 */
import React, { useMemo } from 'react';
import { clsx } from 'clsx';
import { 
  BarChart3,
  TrendingUp,
  TrendingDown,
  Info,
} from 'lucide-react';

interface Feature {
  name: string;
  importance: number;
  category?: string;
  description?: string;
}

interface FeatureImportanceProps {
  features: Feature[];
  title?: string;
  maxFeatures?: number;
  showCategories?: boolean;
  sortOrder?: 'asc' | 'desc';
  loading?: boolean;
  className?: string;
}

// Category colors
const categoryColors: Record<string, string> = {
  price: 'bg-blue-500',
  volume: 'bg-green-500',
  technical: 'bg-purple-500',
  fundamental: 'bg-orange-500',
  sentiment: 'bg-pink-500',
  market: 'bg-cyan-500',
  default: 'bg-gray-500',
};

// Category badge colors
const categoryBadgeColors: Record<string, string> = {
  price: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  volume: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  technical: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  fundamental: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  sentiment: 'bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-400',
  market: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400',
  default: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-400',
};

export const FeatureImportance: React.FC<FeatureImportanceProps> = ({
  features,
  title = 'Feature Importance',
  maxFeatures = 10,
  showCategories = true,
  sortOrder = 'desc',
  loading = false,
  className,
}) => {
  // Sort and limit features
  const displayFeatures = useMemo(() => {
    const sorted = [...features].sort((a, b) => 
      sortOrder === 'desc' 
        ? b.importance - a.importance 
        : a.importance - b.importance
    );
    return sorted.slice(0, maxFeatures);
  }, [features, maxFeatures, sortOrder]);

  // Calculate max importance for scaling
  const maxImportance = useMemo(() => 
    Math.max(...displayFeatures.map(f => Math.abs(f.importance)), 0.001),
    [displayFeatures]
  );

  // Group features by category
  const categoryStats = useMemo(() => {
    const stats: Record<string, { count: number; totalImportance: number }> = {};
    
    displayFeatures.forEach(feature => {
      const category = feature.category || 'default';
      if (!stats[category]) {
        stats[category] = { count: 0, totalImportance: 0 };
      }
      stats[category].count++;
      stats[category].totalImportance += Math.abs(feature.importance);
    });
    
    return stats;
  }, [displayFeatures]);

  if (loading) {
    return (
      <div className={clsx('bg-white dark:bg-gray-800 rounded-lg p-6 animate-pulse', className)}>
        <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-6" />
        <div className="space-y-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="space-y-2">
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/4" />
              <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded" />
            </div>
          ))}
        </div>
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
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-100 dark:bg-indigo-900/30 rounded-lg">
              <BarChart3 className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
            </div>
            <h3 className="font-semibold text-gray-900 dark:text-white">
              {title}
            </h3>
          </div>
          <span className="text-sm text-gray-500 dark:text-gray-400">
            Top {displayFeatures.length} features
          </span>
        </div>
      </div>

      {/* Category Summary */}
      {showCategories && Object.keys(categoryStats).length > 1 && (
        <div className="p-4 bg-gray-50 dark:bg-gray-700/50 border-b border-gray-200 dark:border-gray-700">
          <div className="flex flex-wrap gap-2">
            {Object.entries(categoryStats).map(([category, stats]) => (
              <span
                key={category}
                className={clsx(
                  'px-2 py-1 rounded-full text-xs font-medium',
                  categoryBadgeColors[category] || categoryBadgeColors.default
                )}
              >
                {category}: {stats.count}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Feature List */}
      <div className="p-4 space-y-4">
        {displayFeatures.map((feature, index) => {
          const barWidth = (Math.abs(feature.importance) / maxImportance) * 100;
          const isPositive = feature.importance >= 0;
          const barColor = feature.category 
            ? categoryColors[feature.category] || categoryColors.default
            : isPositive ? 'bg-green-500' : 'bg-red-500';

          return (
            <div key={feature.name} className="group">
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-400 dark:text-gray-500 w-4">
                    {index + 1}
                  </span>
                  <span className="text-sm font-medium text-gray-900 dark:text-white">
                    {feature.name}
                  </span>
                  {feature.description && (
                    <div className="relative group/tooltip">
                      <Info className="w-3 h-3 text-gray-400 cursor-help" />
                      <div className="absolute bottom-full left-0 mb-2 hidden group-hover/tooltip:block z-10">
                        <div className="bg-gray-900 text-white text-xs rounded py-1 px-2 max-w-xs">
                          {feature.description}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {isPositive ? (
                    <TrendingUp className="w-3 h-3 text-green-500" />
                  ) : (
                    <TrendingDown className="w-3 h-3 text-red-500" />
                  )}
                  <span className={clsx(
                    'text-sm font-medium',
                    isPositive ? 'text-green-600' : 'text-red-600'
                  )}>
                    {(feature.importance * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
              
              {/* Progress Bar */}
              <div className="relative">
                <div className="h-6 bg-gray-100 dark:bg-gray-700 rounded-lg overflow-hidden">
                  <div
                    className={clsx(
                      'h-full rounded-lg transition-all duration-500',
                      barColor
                    )}
                    style={{ width: `${barWidth}%` }}
                  />
                </div>
                
                {/* Category badge on bar */}
                {showCategories && feature.category && (
                  <span className={clsx(
                    'absolute right-2 top-1/2 -translate-y-1/2 px-2 py-0.5 rounded text-xs font-medium',
                    barWidth < 50 
                      ? categoryBadgeColors[feature.category] || categoryBadgeColors.default
                      : 'bg-white/20 text-white'
                  )}>
                    {feature.category}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Summary Stats */}
      <div className="p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/50">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-500 dark:text-gray-400">
            Total features analyzed
          </span>
          <span className="font-medium text-gray-900 dark:text-white">
            {features.length}
          </span>
        </div>
        <div className="flex items-center justify-between text-sm mt-1">
          <span className="text-gray-500 dark:text-gray-400">
            Top {maxFeatures} contribution
          </span>
          <span className="font-medium text-gray-900 dark:text-white">
            {((displayFeatures.reduce((sum, f) => sum + Math.abs(f.importance), 0)) * 100).toFixed(1)}%
          </span>
        </div>
      </div>
    </div>
  );
};

export default FeatureImportance;
