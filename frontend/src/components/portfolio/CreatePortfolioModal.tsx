/**
 * Create Portfolio Modal Component
 * 
 * Modal form for creating a new portfolio with risk profile selection.
 */
import { useState } from 'react';
import { X, Briefcase, DollarSign, AlertCircle, Calendar, Power } from 'lucide-react';
import { RiskProfileSelector } from './RiskProfileSelector';
import { cn } from '../../utils/cn';

interface CreatePortfolioModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: {
    name: string;
    description?: string;
    risk_profile: string;
    initial_capital: number;
    currency: string;
    strategy_period_weeks: number;
    is_active: boolean;
  }) => Promise<void>;
  isLoading?: boolean;
  error?: string | null;
  userBaseCurrency: string; // User's base currency - read-only for portfolio
}

// Currency symbols for display
const CURRENCY_SYMBOLS: Record<string, string> = {
  USD: '$', EUR: '€', GBP: '£', JPY: '¥', CHF: 'CHF', CAD: 'C$', AUD: 'A$'
};

// Strategy period options (in weeks)
const STRATEGY_PERIODS = [
  { value: 4, label: '4 weeks (1 month)' },
  { value: 8, label: '8 weeks (2 months)' },
  { value: 12, label: '12 weeks (3 months)' },
  { value: 26, label: '26 weeks (6 months)' },
  { value: 52, label: '52 weeks (1 year)' },
];

export const CreatePortfolioModal = ({
  isOpen,
  onClose,
  onSubmit,
  isLoading = false,
  error = null,
  userBaseCurrency,
}: CreatePortfolioModalProps) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [riskProfile, setRiskProfile] = useState('balanced');
  const [initialCapital, setInitialCapital] = useState('10000');
  // Currency is ALWAYS the user's base currency (read-only)
  const currency = userBaseCurrency;
  const [strategyPeriodWeeks, setStrategyPeriodWeeks] = useState(12);
  const [isActive, setIsActive] = useState(true);
  const [validationError, setValidationError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    console.log('CreatePortfolioModal: handleSubmit called');

    // Validation
    if (!name.trim()) {
      setValidationError('Portfolio name is required');
      return;
    }

    const capital = parseFloat(initialCapital);
    if (isNaN(capital) || capital < 100) {
      setValidationError('Initial capital must be at least 100');
      return;
    }

    if (capital > 100000000) {
      setValidationError('Initial capital cannot exceed 100,000,000');
      return;
    }

    // Round to nearest 100
    const roundedCapital = Math.round(capital / 100) * 100;

    console.log('CreatePortfolioModal: submitting', { name: name.trim(), roundedCapital, riskProfile });

    await onSubmit({
      name: name.trim(),
      description: description.trim() || undefined,
      risk_profile: riskProfile,
      initial_capital: roundedCapital,
      currency,
      strategy_period_weeks: strategyPeriodWeeks,
      is_active: isActive,
    });
    
    console.log('CreatePortfolioModal: submit successful');
  };

  const handleClose = () => {
    if (!isLoading) {
      setName('');
      setDescription('');
      setRiskProfile('balanced');
      setInitialCapital('10000');
      // currency is read-only from user profile
      setStrategyPeriodWeeks(12);
      setIsActive(true);
      setValidationError(null);
      onClose();
    }
  };

  // Handle capital input to enforce step of 100
  const handleCapitalChange = (value: string) => {
    setInitialCapital(value);
  };

  const handleCapitalBlur = () => {
    const capital = parseFloat(initialCapital);
    if (!isNaN(capital) && capital >= 100) {
      const rounded = Math.round(capital / 100) * 100;
      setInitialCapital(rounded.toString());
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto bg-surface-800 border border-surface-700 rounded-xl shadow-2xl mx-4">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-surface-700">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary-500/20 rounded-lg flex items-center justify-center">
              <Briefcase className="w-5 h-5 text-primary-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">Create Portfolio</h2>
              <p className="text-sm text-surface-400">Set up a new paper trading portfolio</p>
            </div>
          </div>
          <button
            onClick={handleClose}
            disabled={isLoading}
            className="p-2 hover:bg-surface-700 rounded-lg transition-colors disabled:opacity-50"
          >
            <X className="w-5 h-5 text-surface-400" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-4 space-y-6">
          {/* Error Display */}
          {(error || validationError) && (
            <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <p className="text-sm">{error || validationError}</p>
            </div>
          )}

          {/* Portfolio Name */}
          <div>
            <label className="block text-sm font-medium text-surface-300 mb-2">
              Portfolio Name *
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My Portfolio"
              className="w-full px-4 py-2.5 bg-surface-900 border border-surface-700 rounded-lg text-white placeholder-surface-500 focus:outline-none focus:border-primary-500 transition-colors"
              maxLength={255}
              disabled={isLoading}
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-surface-300 mb-2">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional description for this portfolio..."
              rows={2}
              className="w-full px-4 py-2.5 bg-surface-900 border border-surface-700 rounded-lg text-white placeholder-surface-500 focus:outline-none focus:border-primary-500 transition-colors resize-none"
              maxLength={1000}
              disabled={isLoading}
            />
          </div>

          {/* Initial Capital & Currency */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-surface-300 mb-2">
                Initial Capital *
              </label>
              <div className="relative">
                <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-surface-500" />
                <input
                  type="number"
                  value={initialCapital}
                  onChange={(e) => handleCapitalChange(e.target.value)}
                  onBlur={handleCapitalBlur}
                  min={100}
                  max={100000000}
                  step={100}
                  className="w-full pl-10 pr-4 py-2.5 bg-surface-900 border border-surface-700 rounded-lg text-white focus:outline-none focus:border-primary-500 transition-colors"
                  disabled={isLoading}
                />
              </div>
              <p className="text-xs text-surface-500 mt-1">Min: 100 - Step: 100</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-surface-300 mb-2">
                Base Currency
              </label>
              <div className="w-full px-4 py-2.5 bg-surface-900/50 border border-surface-700 rounded-lg text-white flex items-center gap-2">
                <span className="text-lg font-semibold text-primary-400">
                  {CURRENCY_SYMBOLS[currency] || currency}
                </span>
                <span>{currency}</span>
                <span className="text-xs text-surface-500 ml-auto">(from profile)</span>
              </div>
              <p className="text-xs text-surface-500 mt-1">
                All portfolio values in this currency
              </p>
            </div>
          </div>

          {/* Strategy Period */}
          <div>
            <label className="block text-sm font-medium text-surface-300 mb-2">
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4" />
                Strategy Calibration Period
              </div>
            </label>
            <select
              value={strategyPeriodWeeks}
              onChange={(e) => setStrategyPeriodWeeks(parseInt(e.target.value))}
              className="w-full px-4 py-2.5 bg-surface-900 border border-surface-700 rounded-lg text-white focus:outline-none focus:border-primary-500 transition-colors"
              disabled={isLoading}
            >
              {STRATEGY_PERIODS.map((period) => (
                <option key={period.value} value={period.value}>
                  {period.label}
                </option>
              ))}
            </select>
            <p className="text-xs text-surface-500 mt-1">
              Period used to calibrate trading strategies for maximum returns
            </p>
          </div>

          {/* Active Status */}
          <div className="flex items-center justify-between p-4 bg-surface-900 border border-surface-700 rounded-lg">
            <div className="flex items-center gap-3">
              <Power className={cn("w-5 h-5", isActive ? "text-green-400" : "text-surface-500")} />
              <div>
                <p className="text-sm font-medium text-white">Portfolio Active</p>
                <p className="text-xs text-surface-400">
                  {isActive 
                    ? "Portfolio will be processed by the platform" 
                    : "Portfolio is paused and won't be processed"}
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setIsActive(!isActive)}
              disabled={isLoading}
              className={cn(
                "relative w-12 h-6 rounded-full transition-colors",
                isActive ? "bg-green-500" : "bg-surface-600"
              )}
            >
              <span
                className={cn(
                  "absolute top-1 w-4 h-4 bg-white rounded-full transition-transform",
                  isActive ? "translate-x-7" : "translate-x-1"
                )}
              />
            </button>
          </div>

          {/* Risk Profile */}
          <div>
            <label className="block text-sm font-medium text-surface-300 mb-3">
              Risk Profile *
            </label>
            <RiskProfileSelector
              value={riskProfile}
              onChange={setRiskProfile}
              showDetails={true}
              size="md"
            />
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-surface-700">
            <button
              type="button"
              onClick={handleClose}
              disabled={isLoading}
              className="px-4 py-2 text-sm font-medium text-surface-400 hover:text-white transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className={cn(
                'px-6 py-2 text-sm font-medium bg-primary-500 hover:bg-primary-600 text-white rounded-lg transition-colors',
                'disabled:opacity-50 disabled:cursor-not-allowed',
                'flex items-center gap-2'
              )}
            >
              {isLoading ? (
                <>
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Creating...
                </>
              ) : (
                'Create Portfolio'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CreatePortfolioModal;
