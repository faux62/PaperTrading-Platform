/**
 * SignalIndicator Component
 * 
 * Compact trading signal indicator (Buy/Sell/Hold)
 */
import React from 'react';
import { clsx } from 'clsx';
import { 
  ArrowUpCircle, 
  ArrowDownCircle, 
  MinusCircle,
} from 'lucide-react';

export type SignalType = 'strong_buy' | 'buy' | 'hold' | 'sell' | 'strong_sell';

interface SignalIndicatorProps {
  signal: SignalType;
  showLabel?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const signalConfig: Record<SignalType, {
  icon: React.FC<{ className?: string }>;
  label: string;
  color: string;
  bgColor: string;
}> = {
  strong_buy: {
    icon: ArrowUpCircle,
    label: 'Strong Buy',
    color: 'text-green-600 dark:text-green-400',
    bgColor: 'bg-green-100 dark:bg-green-900/30',
  },
  buy: {
    icon: ArrowUpCircle,
    label: 'Buy',
    color: 'text-green-500 dark:text-green-400',
    bgColor: 'bg-green-50 dark:bg-green-900/20',
  },
  hold: {
    icon: MinusCircle,
    label: 'Hold',
    color: 'text-gray-500 dark:text-gray-400',
    bgColor: 'bg-gray-100 dark:bg-gray-700',
  },
  sell: {
    icon: ArrowDownCircle,
    label: 'Sell',
    color: 'text-red-500 dark:text-red-400',
    bgColor: 'bg-red-50 dark:bg-red-900/20',
  },
  strong_sell: {
    icon: ArrowDownCircle,
    label: 'Strong Sell',
    color: 'text-red-600 dark:text-red-400',
    bgColor: 'bg-red-100 dark:bg-red-900/30',
  },
};

const sizeConfig = {
  sm: {
    icon: 'w-4 h-4',
    text: 'text-xs',
    padding: 'px-2 py-0.5',
  },
  md: {
    icon: 'w-5 h-5',
    text: 'text-sm',
    padding: 'px-2.5 py-1',
  },
  lg: {
    icon: 'w-6 h-6',
    text: 'text-base',
    padding: 'px-3 py-1.5',
  },
};

export const SignalIndicator: React.FC<SignalIndicatorProps> = ({
  signal,
  showLabel = true,
  size = 'md',
  className,
}) => {
  const config = signalConfig[signal];
  const sizes = sizeConfig[size];
  const Icon = config.icon;

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1 rounded-full font-medium',
        config.bgColor,
        config.color,
        sizes.padding,
        sizes.text,
        className
      )}
    >
      <Icon className={sizes.icon} />
      {showLabel && <span>{config.label}</span>}
    </span>
  );
};

// Signal strength meter component
interface SignalMeterProps {
  value: number; // -1 to 1 (sell to buy)
  showLabels?: boolean;
  className?: string;
}

export const SignalMeter: React.FC<SignalMeterProps> = ({
  value,
  showLabels = true,
  className,
}) => {
  // Clamp value between -1 and 1
  const clampedValue = Math.max(-1, Math.min(1, value));
  
  // Convert to 0-100 scale for positioning
  const position = ((clampedValue + 1) / 2) * 100;
  
  // Determine signal type
  let signalType: SignalType;
  if (clampedValue >= 0.6) signalType = 'strong_buy';
  else if (clampedValue >= 0.2) signalType = 'buy';
  else if (clampedValue >= -0.2) signalType = 'hold';
  else if (clampedValue >= -0.6) signalType = 'sell';
  else signalType = 'strong_sell';

  return (
    <div className={clsx('space-y-2', className)}>
      {/* Gradient bar */}
      <div className="relative h-3 rounded-full bg-gradient-to-r from-red-500 via-gray-300 to-green-500">
        {/* Marker */}
        <div
          className="absolute top-1/2 -translate-y-1/2 w-4 h-4 bg-white border-2 border-gray-800 rounded-full shadow-md transition-all duration-300"
          style={{ left: `calc(${position}% - 8px)` }}
        />
      </div>
      
      {/* Labels */}
      {showLabels && (
        <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
          <span>Strong Sell</span>
          <span>Neutral</span>
          <span>Strong Buy</span>
        </div>
      )}
      
      {/* Current signal */}
      <div className="flex justify-center">
        <SignalIndicator signal={signalType} size="sm" />
      </div>
    </div>
  );
};

export default SignalIndicator;
