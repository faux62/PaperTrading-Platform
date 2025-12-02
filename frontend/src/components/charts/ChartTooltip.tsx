/**
 * ChartTooltip Component
 * 
 * Custom tooltip component for charts
 */
import React from 'react';
import { clsx } from 'clsx';
import type { TooltipData } from './types';

interface ChartTooltipProps {
  active?: boolean;
  label?: string;
  items?: TooltipData[];
  className?: string;
}

export const ChartTooltip: React.FC<ChartTooltipProps> = ({
  active,
  label,
  items = [],
  className,
}) => {
  if (!active || items.length === 0) {
    return null;
  }

  return (
    <div
      className={clsx(
        'bg-white dark:bg-gray-800 shadow-lg rounded-lg border border-gray-200 dark:border-gray-700 p-3',
        className
      )}
    >
      {label && (
        <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">
          {label}
        </p>
      )}
      <div className="space-y-1">
        {items.map((item, index) => (
          <div key={`${item.label}-${index}`} className="flex items-center gap-2">
            {item.color && (
              <span
                className="w-2 h-2 rounded-full flex-shrink-0"
                style={{ backgroundColor: item.color }}
              />
            )}
            <span className="text-sm text-gray-600 dark:text-gray-300">
              {item.label}:
            </span>
            <span className="text-sm font-semibold text-gray-900 dark:text-white">
              {typeof item.value === 'number'
                ? item.value.toLocaleString(undefined, {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })
                : item.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

// Recharts-compatible custom tooltip wrapper
interface RechartsTooltipProps {
  active?: boolean;
  payload?: Array<{
    name: string;
    value: number;
    color: string;
    dataKey: string;
  }>;
  label?: string;
  formatter?: (value: number, name: string) => string;
}

export const RechartsTooltip: React.FC<RechartsTooltipProps> = ({
  active,
  payload,
  label,
  formatter,
}) => {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  const items: TooltipData[] = payload.map((entry) => ({
    label: entry.name,
    value: formatter ? formatter(entry.value, entry.name) : entry.value,
    color: entry.color,
  }));

  return <ChartTooltip active={active} label={label} items={items} />;
};

export default ChartTooltip;
