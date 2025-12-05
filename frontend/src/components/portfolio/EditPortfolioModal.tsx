/**
 * Edit Portfolio Modal Component
 * 
 * Modal form for editing an existing portfolio.
 */
import { useState, useEffect } from 'react';
import { X, Briefcase, AlertCircle } from 'lucide-react';
import { RiskProfileSelector } from './RiskProfileSelector';
import { cn } from '../../utils/cn';
import { PortfolioSummary } from './PortfolioCard';

interface EditPortfolioModalProps {
  isOpen: boolean;
  portfolio: PortfolioSummary | null;
  onClose: () => void;
  onSubmit: (id: number, data: {
    name: string;
    description?: string;
    risk_profile: string;
  }) => Promise<void>;
  isLoading?: boolean;
  error?: string | null;
}

export const EditPortfolioModal = ({
  isOpen,
  portfolio,
  onClose,
  onSubmit,
  isLoading = false,
  error = null,
}: EditPortfolioModalProps) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [riskProfile, setRiskProfile] = useState('balanced');
  const [validationError, setValidationError] = useState<string | null>(null);

  // Populate form when portfolio changes
  useEffect(() => {
    if (portfolio) {
      setName(portfolio.name);
      setDescription(''); // Description not in summary, could be fetched
      setRiskProfile(portfolio.risk_profile);
      setValidationError(null);
    }
  }, [portfolio]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    if (!portfolio) return;

    // Validation
    if (!name.trim()) {
      setValidationError('Portfolio name is required');
      return;
    }

    await onSubmit(portfolio.id, {
      name: name.trim(),
      description: description.trim() || undefined,
      risk_profile: riskProfile,
    });
  };

  const handleClose = () => {
    if (!isLoading) {
      setValidationError(null);
      onClose();
    }
  };

  if (!isOpen || !portfolio) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-lg max-h-[90vh] overflow-y-auto bg-surface-800 border border-surface-700 rounded-xl shadow-2xl mx-4">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-surface-700">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary-500/20 rounded-lg flex items-center justify-center">
              <Briefcase className="w-5 h-5 text-primary-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">Edit Portfolio</h2>
              <p className="text-sm text-surface-400">Update portfolio settings</p>
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

          {/* Risk Profile */}
          <div>
            <label className="block text-sm font-medium text-surface-300 mb-2">
              Risk Profile
            </label>
            <RiskProfileSelector
              value={riskProfile}
              onChange={setRiskProfile}
              disabled={isLoading}
            />
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-surface-700">
            <button
              type="button"
              onClick={handleClose}
              disabled={isLoading}
              className="px-4 py-2 text-surface-300 hover:text-white hover:bg-surface-700 rounded-lg transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className={cn(
                'px-6 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg transition-colors',
                'disabled:opacity-50 disabled:cursor-not-allowed',
                'flex items-center gap-2'
              )}
            >
              {isLoading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Saving...
                </>
              ) : (
                'Save Changes'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
