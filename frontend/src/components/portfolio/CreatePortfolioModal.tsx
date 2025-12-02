/**
 * Create Portfolio Modal Component
 * 
 * Modal form for creating a new portfolio with risk profile selection.
 */
import { useState } from 'react';
import { X, Briefcase, DollarSign, AlertCircle } from 'lucide-react';
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
  }) => Promise<void>;
  isLoading?: boolean;
  error?: string | null;
}

const CURRENCIES = ['USD', 'EUR', 'GBP', 'JPY', 'CHF'];

export const CreatePortfolioModal = ({
  isOpen,
  onClose,
  onSubmit,
  isLoading = false,
  error = null,
}: CreatePortfolioModalProps) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [riskProfile, setRiskProfile] = useState('balanced');
  const [initialCapital, setInitialCapital] = useState('100000');
  const [currency, setCurrency] = useState('USD');
  const [validationError, setValidationError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    // Validation
    if (!name.trim()) {
      setValidationError('Portfolio name is required');
      return;
    }

    const capital = parseFloat(initialCapital);
    if (isNaN(capital) || capital < 1000) {
      setValidationError('Initial capital must be at least 1,000');
      return;
    }

    if (capital > 100000000) {
      setValidationError('Initial capital cannot exceed 100,000,000');
      return;
    }

    await onSubmit({
      name: name.trim(),
      description: description.trim() || undefined,
      risk_profile: riskProfile,
      initial_capital: capital,
      currency,
    });
  };

  const handleClose = () => {
    if (!isLoading) {
      setName('');
      setDescription('');
      setRiskProfile('balanced');
      setInitialCapital('100000');
      setCurrency('USD');
      setValidationError(null);
      onClose();
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
                  onChange={(e) => setInitialCapital(e.target.value)}
                  min={1000}
                  max={100000000}
                  step={1000}
                  className="w-full pl-10 pr-4 py-2.5 bg-surface-900 border border-surface-700 rounded-lg text-white focus:outline-none focus:border-primary-500 transition-colors"
                  disabled={isLoading}
                />
              </div>
              <p className="text-xs text-surface-500 mt-1">Min: 1,000 - Max: 100,000,000</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-surface-300 mb-2">
                Currency
              </label>
              <select
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                className="w-full px-4 py-2.5 bg-surface-900 border border-surface-700 rounded-lg text-white focus:outline-none focus:border-primary-500 transition-colors"
                disabled={isLoading}
              >
                {CURRENCIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
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
