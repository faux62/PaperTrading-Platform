/**
 * Portfolio Card Component
 * 
 * Displays portfolio summary in a card format for list views.
 */
import { TrendingUp, TrendingDown, Briefcase, MoreVertical, Trash2, Edit, Eye, Power, Calendar } from 'lucide-react';
import { cn } from '../../utils/cn';
import { Card, CardContent } from '../common';

export interface PortfolioSummary {
  id: number;
  name: string;
  risk_profile: string;
  total_value: number;
  total_return: number;
  total_return_percent: number;
  position_count: number;
  is_active: boolean;
  currency: string;
  strategy_period_weeks?: number;
}

interface PortfolioCardProps {
  portfolio: PortfolioSummary;
  onView?: (id: number) => void;
  onEdit?: (id: number) => void;
  onDelete?: (id: number) => void;
  className?: string;
}

const getRiskProfileColor = (profile: string) => {
  switch (profile.toLowerCase()) {
    case 'aggressive':
      return 'text-red-400 bg-red-500/10';
    case 'balanced':
      return 'text-primary-400 bg-primary-500/10';
    case 'prudent':
      return 'text-green-400 bg-green-500/10';
    default:
      return 'text-surface-400 bg-surface-700';
  }
};

const formatCurrency = (value: number, currency: string = 'USD') => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
};

const formatPercent = (value: number) => {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
};

export const PortfolioCard = ({
  portfolio,
  onView,
  onEdit,
  onDelete,
  className,
}: PortfolioCardProps) => {
  const isPositive = portfolio.total_return >= 0;
  const TrendIcon = isPositive ? TrendingUp : TrendingDown;
  // Handle both boolean and legacy string types for backwards compatibility
  const isActive = portfolio.is_active === true || (portfolio.is_active as unknown) === 'active';

  return (
    <Card className={cn(
      'hover:border-surface-600 transition-colors',
      !isActive && 'opacity-60',
      className
    )}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between">
          {/* Left: Portfolio Info */}
          <div className="flex items-start gap-3">
            <div className={cn(
              "w-10 h-10 rounded-lg flex items-center justify-center",
              isActive ? "bg-primary-500/20" : "bg-surface-700"
            )}>
              <Briefcase className={cn("w-5 h-5", isActive ? "text-primary-400" : "text-surface-500")} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-white">{portfolio.name}</h3>
                {!isActive && (
                  <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-surface-700 text-surface-400">
                    <Power className="w-3 h-3" />
                    Inactive
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2 mt-1">
                <span
                  className={cn(
                    'text-xs px-2 py-0.5 rounded-full capitalize',
                    getRiskProfileColor(portfolio.risk_profile)
                  )}
                >
                  {portfolio.risk_profile}
                </span>
                <span className="text-xs text-surface-500">
                  {portfolio.position_count} positions
                </span>
                {portfolio.strategy_period_weeks && (
                  <span className="flex items-center gap-1 text-xs text-surface-500">
                    <Calendar className="w-3 h-3" />
                    {portfolio.strategy_period_weeks}w
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Right: Menu */}
          <div className="relative group">
            <button className="p-1.5 hover:bg-surface-700 rounded-lg transition-colors">
              <MoreVertical className="w-4 h-4 text-surface-400" />
            </button>
            <div className="absolute right-0 top-full mt-1 w-36 bg-surface-800 border border-surface-700 rounded-lg shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10">
              {onView && (
                <button
                  onClick={() => onView(portfolio.id)}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-surface-300 hover:bg-surface-700 hover:text-white transition-colors"
                >
                  <Eye className="w-4 h-4" />
                  View
                </button>
              )}
              {onEdit && (
                <button
                  onClick={() => onEdit(portfolio.id)}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-surface-300 hover:bg-surface-700 hover:text-white transition-colors"
                >
                  <Edit className="w-4 h-4" />
                  Edit
                </button>
              )}
              {onDelete && (
                <button
                  onClick={() => onDelete(portfolio.id)}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-400 hover:bg-red-500/10 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                  Delete
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-4 mt-4 pt-4 border-t border-surface-700">
          <div>
            <p className="text-xs text-surface-500 mb-1">Total Value</p>
            <p className="text-lg font-semibold text-white">
              {formatCurrency(portfolio.total_value, portfolio.currency)}
            </p>
          </div>
          <div>
            <p className="text-xs text-surface-500 mb-1">Total Return</p>
            <div className="flex items-center gap-2">
              <TrendIcon
                className={cn('w-4 h-4', isPositive ? 'text-green-400' : 'text-red-400')}
              />
              <p
                className={cn(
                  'text-lg font-semibold',
                  isPositive ? 'text-green-400' : 'text-red-400'
                )}
              >
                {formatPercent(portfolio.total_return_percent)}
              </p>
            </div>
            <p className={cn('text-xs', isPositive ? 'text-green-400/70' : 'text-red-400/70')}>
              {formatCurrency(portfolio.total_return, portfolio.currency)}
            </p>
          </div>
        </div>

        {/* Quick Action */}
        {onView && (
          <button
            onClick={() => onView(portfolio.id)}
            className="w-full mt-4 py-2 text-sm text-primary-400 hover:text-primary-300 hover:bg-primary-500/10 rounded-lg transition-colors"
          >
            View Details →
          </button>
        )}
      </CardContent>
    </Card>
  );
};

export default PortfolioCard;
