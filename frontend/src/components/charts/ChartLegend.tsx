/**
 * ChartLegend Component
 * 
 * Reusable legend component for charts
 */
import React from 'react';
import { clsx } from 'clsx';
import type { LegendItem } from './types';

interface ChartLegendProps {
  items: LegendItem[];
  orientation?: 'horizontal' | 'vertical';
  onClick?: (item: LegendItem, index: number) => void;
  className?: string;
}

export const ChartLegend: React.FC<ChartLegendProps> = ({
  items,
  orientation = 'horizontal',
  onClick,
  className,
}) => {
  return (
    <div
      className={clsx(
        'flex gap-4',
        orientation === 'vertical' ? 'flex-col' : 'flex-row flex-wrap',
        className
      )}
    >
      {items.map((item, index) => (
        <button
          key={`${item.label}-${index}`}
          type="button"
          className={clsx(
            'flex items-center gap-2 text-sm transition-opacity',
            onClick && 'cursor-pointer hover:opacity-80',
            !onClick && 'cursor-default',
            item.active === false && 'opacity-40'
          )}
          onClick={() => onClick?.(item, index)}
          disabled={!onClick}
        >
          <span
            className="w-3 h-3 rounded-sm flex-shrink-0"
            style={{ backgroundColor: item.color }}
          />
          <span className="text-gray-700 dark:text-gray-300">{item.label}</span>
          {item.value !== undefined && (
            <span className="font-medium text-gray-900 dark:text-white">
              {typeof item.value === 'number'
                ? item.value.toLocaleString()
                : item.value}
            </span>
          )}
        </button>
      ))}
    </div>
  );
};

export default ChartLegend;
