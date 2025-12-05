/**
 * Risk Profile Selector Component
 * 
 * Allows users to select between Aggressive, Balanced, and Prudent profiles
 * with visual indicators of risk/return characteristics.
 */
import { useState } from 'react';
import { TrendingUp, Scale, Shield, Check, ChevronRight } from 'lucide-react';
import { cn } from '../../utils/cn';

export interface RiskProfileOption {
  name: string;
  value: string;
  description: string;
  equity_allocation: number;
  fixed_income_allocation: number;
  cash_allocation: number;
  max_volatility: number;
  max_drawdown: number;
  max_position_size: number;
  min_positions: number;
  max_positions: number;
  rebalance_frequency_days: number;
}

interface RiskProfileSelectorProps {
  value: string;
  onChange: (value: string) => void;
  profiles?: RiskProfileOption[];
  showDetails?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  disabled?: boolean;
}

// Default profiles if not provided from API
const DEFAULT_PROFILES: RiskProfileOption[] = [
  {
    name: 'Aggressive',
    value: 'aggressive',
    description: 'High growth focus with higher volatility tolerance',
    equity_allocation: 95,
    fixed_income_allocation: 0,
    cash_allocation: 0,
    max_volatility: 30,
    max_drawdown: 35,
    max_position_size: 15,
    min_positions: 8,
    max_positions: 30,
    rebalance_frequency_days: 180,
  },
  {
    name: 'Balanced',
    value: 'balanced',
    description: 'Mix of growth and stability for moderate risk',
    equity_allocation: 70,
    fixed_income_allocation: 20,
    cash_allocation: 5,
    max_volatility: 18,
    max_drawdown: 20,
    max_position_size: 10,
    min_positions: 15,
    max_positions: 40,
    rebalance_frequency_days: 90,
  },
  {
    name: 'Prudent',
    value: 'prudent',
    description: 'Capital preservation with steady income',
    equity_allocation: 40,
    fixed_income_allocation: 45,
    cash_allocation: 15,
    max_volatility: 10,
    max_drawdown: 12,
    max_position_size: 7,
    min_positions: 20,
    max_positions: 50,
    rebalance_frequency_days: 60,
  },
];

const getProfileIcon = (value: string) => {
  switch (value) {
    case 'aggressive':
      return TrendingUp;
    case 'balanced':
      return Scale;
    case 'prudent':
      return Shield;
    default:
      return Scale;
  }
};

const getProfileColor = (value: string) => {
  switch (value) {
    case 'aggressive':
      return {
        bg: 'bg-red-500/10',
        border: 'border-red-500/50',
        activeBorder: 'border-red-500',
        icon: 'text-red-400',
        bar: 'bg-red-500',
      };
    case 'balanced':
      return {
        bg: 'bg-primary-500/10',
        border: 'border-primary-500/50',
        activeBorder: 'border-primary-500',
        icon: 'text-primary-400',
        bar: 'bg-primary-500',
      };
    case 'prudent':
      return {
        bg: 'bg-green-500/10',
        border: 'border-green-500/50',
        activeBorder: 'border-green-500',
        icon: 'text-green-400',
        bar: 'bg-green-500',
      };
    default:
      return {
        bg: 'bg-surface-700',
        border: 'border-surface-600',
        activeBorder: 'border-primary-500',
        icon: 'text-surface-400',
        bar: 'bg-surface-500',
      };
  }
};

export const RiskProfileSelector = ({
  value,
  onChange,
  profiles = DEFAULT_PROFILES,
  showDetails = true,
  size = 'md',
  className,
  disabled = false,
}: RiskProfileSelectorProps) => {
  const [expandedProfile, setExpandedProfile] = useState<string | null>(null);

  const sizeClasses = {
    sm: 'p-3',
    md: 'p-4',
    lg: 'p-5',
  };

  return (
    <div className={cn('space-y-3', className)}>
      {profiles.map((profile) => {
        const isSelected = value === profile.value;
        const isExpanded = expandedProfile === profile.value;
        const Icon = getProfileIcon(profile.value);
        const colors = getProfileColor(profile.value);

        return (
          <div
            key={profile.value}
            className={cn(
              'rounded-lg border-2 transition-all',
              colors.bg,
              isSelected ? colors.activeBorder : colors.border,
              disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:border-opacity-100'
            )}
            onClick={() => !disabled && onChange(profile.value)}
          >
            <div className={cn('flex items-center gap-4', sizeClasses[size])}>
              {/* Icon */}
              <div
                className={cn(
                  'w-12 h-12 rounded-full flex items-center justify-center',
                  colors.bg
                )}
              >
                <Icon className={cn('w-6 h-6', colors.icon)} />
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold text-white">{profile.name}</h3>
                  {isSelected && (
                    <span className={cn('p-0.5 rounded-full', colors.bg)}>
                      <Check className={cn('w-4 h-4', colors.icon)} />
                    </span>
                  )}
                </div>
                <p className="text-sm text-surface-400 mt-0.5">{profile.description}</p>

                {/* Quick Stats */}
                {showDetails && (
                  <div className="flex items-center gap-4 mt-2">
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs text-surface-500">Equity</span>
                      <span className="text-sm font-medium text-white">
                        {profile.equity_allocation}%
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs text-surface-500">Max Vol</span>
                      <span className="text-sm font-medium text-white">
                        {profile.max_volatility}%
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs text-surface-500">Positions</span>
                      <span className="text-sm font-medium text-white">
                        {profile.min_positions}-{profile.max_positions}
                      </span>
                    </div>
                  </div>
                )}
              </div>

              {/* Expand Button */}
              {showDetails && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setExpandedProfile(isExpanded ? null : profile.value);
                  }}
                  className="p-2 hover:bg-surface-700 rounded-lg transition-colors"
                >
                  <ChevronRight
                    className={cn(
                      'w-5 h-5 text-surface-400 transition-transform',
                      isExpanded && 'rotate-90'
                    )}
                  />
                </button>
              )}
            </div>

            {/* Expanded Details */}
            {showDetails && isExpanded && (
              <div className="px-4 pb-4 border-t border-surface-700 mt-2 pt-4">
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div>
                    <p className="text-xs text-surface-500 mb-1">Asset Allocation</p>
                    <div className="h-2 bg-surface-700 rounded-full overflow-hidden flex">
                      <div
                        className="bg-blue-500 h-full"
                        style={{ width: `${profile.equity_allocation}%` }}
                        title={`Equity: ${profile.equity_allocation}%`}
                      />
                      <div
                        className="bg-amber-500 h-full"
                        style={{ width: `${profile.fixed_income_allocation}%` }}
                        title={`Fixed Income: ${profile.fixed_income_allocation}%`}
                      />
                      <div
                        className="bg-green-500 h-full"
                        style={{ width: `${profile.cash_allocation}%` }}
                        title={`Cash: ${profile.cash_allocation}%`}
                      />
                    </div>
                    <div className="flex gap-3 mt-1 text-xs">
                      <span className="flex items-center gap-1">
                        <span className="w-2 h-2 bg-blue-500 rounded-full" />
                        Equity
                      </span>
                      <span className="flex items-center gap-1">
                        <span className="w-2 h-2 bg-amber-500 rounded-full" />
                        Bonds
                      </span>
                      <span className="flex items-center gap-1">
                        <span className="w-2 h-2 bg-green-500 rounded-full" />
                        Cash
                      </span>
                    </div>
                  </div>

                  <div>
                    <p className="text-xs text-surface-500 mb-1">Risk Limits</p>
                    <div className="space-y-1 text-sm">
                      <div className="flex justify-between">
                        <span className="text-surface-400">Max Drawdown</span>
                        <span className="text-white">{profile.max_drawdown}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-surface-400">Max Position</span>
                        <span className="text-white">{profile.max_position_size}%</span>
                      </div>
                    </div>
                  </div>

                  <div>
                    <p className="text-xs text-surface-500 mb-1">Rebalancing</p>
                    <div className="space-y-1 text-sm">
                      <div className="flex justify-between">
                        <span className="text-surface-400">Frequency</span>
                        <span className="text-white">
                          {profile.rebalance_frequency_days} days
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

export default RiskProfileSelector;
