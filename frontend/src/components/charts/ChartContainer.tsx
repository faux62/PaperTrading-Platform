/**
 * ChartContainer Component
 * 
 * Wrapper component for all charts with common functionality:
 * - Loading state
 * - Error handling
 * - Responsive sizing
 * - Consistent styling
 */
import React from 'react';
import { clsx } from 'clsx';
import { Spinner } from '../common/Loading';

interface ChartContainerProps {
  title?: string;
  subtitle?: string;
  children: React.ReactNode;
  loading?: boolean;
  error?: string;
  height?: number | string;
  className?: string;
  headerRight?: React.ReactNode;
  footer?: React.ReactNode;
}

export const ChartContainer: React.FC<ChartContainerProps> = ({
  title,
  subtitle,
  children,
  loading = false,
  error,
  height = 400,
  className,
  headerRight,
  footer,
}) => {
  return (
    <div
      className={clsx(
        'bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700',
        className
      )}
    >
      {/* Header */}
      {(title || headerRight) && (
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
          <div>
            {title && (
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                {title}
              </h3>
            )}
            {subtitle && (
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {subtitle}
              </p>
            )}
          </div>
          {headerRight && <div>{headerRight}</div>}
        </div>
      )}

      {/* Chart Area */}
      <div
        className="relative p-4"
        style={{ height: typeof height === 'number' ? `${height}px` : height }}
      >
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/80 dark:bg-gray-800/80 z-10">
            <Spinner size="lg" />
          </div>
        )}

        {error && !loading && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
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
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
              <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                {error}
              </p>
            </div>
          </div>
        )}

        {!loading && !error && children}
      </div>

      {/* Footer */}
      {footer && (
        <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-700">
          {footer}
        </div>
      )}
    </div>
  );
};

export default ChartContainer;
