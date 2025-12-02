/**
 * TimeRangeSelector Component
 * 
 * Buttons for selecting analysis time range
 */
import React from 'react';
import { clsx } from 'clsx';

type TimeRange = '1W' | '1M' | '3M' | '6M' | '1Y' | 'YTD' | 'ALL';

interface TimeRangeSelectorProps {
  value: TimeRange;
  onChange: (range: TimeRange) => void;
  className?: string;
  size?: 'sm' | 'md';
  options?: TimeRange[];
}

const defaultOptions: TimeRange[] = ['1W', '1M', '3M', '6M', '1Y', 'YTD', 'ALL'];

export const TimeRangeSelector: React.FC<TimeRangeSelectorProps> = ({
  value,
  onChange,
  className,
  size = 'md',
  options = defaultOptions,
}) => {
  const sizeClasses = {
    sm: 'px-2 py-1 text-xs',
    md: 'px-3 py-1.5 text-sm',
  };

  return (
    <div className={clsx('inline-flex rounded-lg bg-gray-100 dark:bg-gray-700 p-1', className)}>
      {options.map((range) => (
        <button
          key={range}
          type="button"
          onClick={() => onChange(range)}
          className={clsx(
            'font-medium rounded-md transition-colors',
            sizeClasses[size],
            value === range
              ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm'
              : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
          )}
        >
          {range}
        </button>
      ))}
    </div>
  );
};

export default TimeRangeSelector;
