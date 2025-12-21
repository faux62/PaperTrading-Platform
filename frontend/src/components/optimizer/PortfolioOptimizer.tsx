// Portfolio Optimizer - Main Component

import React, { useState, useEffect } from 'react';
import { 
  Sparkles, 
  TrendingUp, 
  Shield, 
  Zap,
  Target,
  PieChart,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  RefreshCw,
  ChevronRight
} from 'lucide-react';
import { optimizerService } from '../../services/optimizerService';
import type { 
  OptimizationMethod, 
  OptimizationMethodInfo,
  PortfolioProposal,
  OptimizationRequest 
} from '../../types/optimizer';
import ProposalCard from './ProposalCard';
import OptimizationModal from './OptimizationModal';
import ProposalDetailModal from './ProposalDetailModal';

// Currency symbols mapping
const CURRENCY_SYMBOLS: Record<string, string> = {
  USD: '$', EUR: '€', GBP: '£', JPY: '¥', CHF: 'CHF',
  CAD: 'C$', AUD: 'A$', HKD: 'HK$', SGD: 'S$', CNY: '¥',
};

interface Props {
  portfolioId: string;
  portfolioName: string;
  riskProfile: string;
  capital: number;
  currency: string;
  strategyPeriodWeeks: number;
  onTradesExecuted?: () => void;  // Callback when trades are executed
}

const methodIcons: Record<OptimizationMethod, React.ReactNode> = {
  mean_variance: <TrendingUp className="w-5 h-5" />,
  min_variance: <Shield className="w-5 h-5" />,
  max_sharpe: <Zap className="w-5 h-5" />,
  risk_parity: <PieChart className="w-5 h-5" />,
  hrp: <Target className="w-5 h-5" />,
  black_litterman: <Sparkles className="w-5 h-5" />,
};

const PortfolioOptimizer: React.FC<Props> = ({
  portfolioId,
  portfolioName,
  riskProfile,
  capital,
  currency,
  strategyPeriodWeeks,
  onTradesExecuted,
}) => {
  const [methods, setMethods] = useState<OptimizationMethodInfo[]>([]);
  const [proposals, setProposals] = useState<PortfolioProposal[]>([]);
  const [loading, setLoading] = useState(true);
  const [optimizing, setOptimizing] = useState(false);
  const [showOptimizeModal, setShowOptimizeModal] = useState(false);
  const [selectedProposal, setSelectedProposal] = useState<PortfolioProposal | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, [portfolioId]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [methodsData, proposalsData] = await Promise.all([
        optimizerService.getMethods(),
        optimizerService.getProposals(portfolioId),
      ]);
      setMethods(methodsData);
      setProposals(proposalsData);
      setError(null);
    } catch (err) {
      setError('Failed to load optimizer data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleOptimize = async (request: OptimizationRequest) => {
    try {
      setOptimizing(true);
      setError(null);
      
      const response = await optimizerService.optimize({
        ...request,
        portfolio_id: portfolioId,
      });

      if (response.success && response.proposal) {
        setProposals(prev => [response.proposal!, ...prev]);
        setSelectedProposal(response.proposal);
      } else {
        setError(response.error || 'Optimization failed');
      }
    } catch (err) {
      setError('Failed to run optimization');
      console.error(err);
    } finally {
      setOptimizing(false);
      setShowOptimizeModal(false);
    }
  };

  const handleAction = async (proposalId: string, action: 'approve' | 'reject') => {
    try {
      const updated = await optimizerService.actionProposal(proposalId, action);
      setProposals(prev => 
        prev.map(p => p.id === proposalId ? updated : p)
      );
      if (selectedProposal?.id === proposalId) {
        setSelectedProposal(updated);
      }
    } catch (err) {
      setError(`Failed to ${action} proposal`);
    }
  };

  const handleDelete = async (proposalId: string) => {
    try {
      await optimizerService.deleteProposal(proposalId);
      setProposals(prev => prev.filter(p => p.id !== proposalId));
      if (selectedProposal?.id === proposalId) {
        setSelectedProposal(null);
      }
    } catch (err) {
      setError('Failed to delete proposal');
    }
  };

  const handleExecute = async (proposalId: string) => {
    try {
      setOptimizing(true);
      setError(null);
      
      const result = await optimizerService.executeProposal(proposalId);
      
      // Close the modal first
      setSelectedProposal(null);
      
      // Show success message
      alert(`Successfully created ${result.total_trades} trades!\n\n${result.message}`);
      
      // Reload optimizer data
      await loadData();
      
      // Notify parent to refresh portfolio data (positions, etc.)
      if (onTradesExecuted) {
        onTradesExecuted();
      }
    } catch (err: any) {
      const errorMsg = err?.response?.data?.detail || 'Failed to execute proposal';
      setError(errorMsg);
      console.error('Execute error:', err);
    } finally {
      setOptimizing(false);
    }
  };

  const handleCheckRebalance = async () => {
    try {
      setOptimizing(true);
      const response = await optimizerService.checkRebalance(portfolioId, 0.05);
      
      if (response.success && response.proposal) {
        setProposals(prev => [response.proposal!, ...prev]);
        setSelectedProposal(response.proposal);
      } else if (response.error?.includes('within threshold')) {
        setError('Portfolio is balanced - no rebalancing needed');
      } else {
        setError(response.error || 'Rebalance check failed');
      }
    } catch (err) {
      setError('Failed to check rebalancing');
    } finally {
      setOptimizing(false);
    }
  };

  const pendingProposals = proposals.filter(p => p.status === 'pending');
  const historyProposals = proposals.filter(p => p.status !== 'pending');

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-purple-500" />
            Portfolio Optimizer
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            AI-powered portfolio optimization for {portfolioName}
          </p>
        </div>
        
        <div className="flex gap-2">
          <button
            onClick={handleCheckRebalance}
            disabled={optimizing}
            className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 
                     bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 
                     rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 
                     disabled:opacity-50 flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${optimizing ? 'animate-spin' : ''}`} />
            Check Rebalance
          </button>
          
          <button
            onClick={() => setShowOptimizeModal(true)}
            disabled={optimizing}
            className="px-4 py-2 text-sm font-medium text-white bg-purple-600 
                     rounded-lg hover:bg-purple-700 disabled:opacity-50 
                     flex items-center gap-2"
          >
            <Sparkles className="w-4 h-4" />
            New Optimization
          </button>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 
                      rounded-lg p-4 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
            <button 
              onClick={() => setError(null)}
              className="text-xs text-red-600 dark:text-red-500 underline mt-1"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {/* Portfolio Info */}
      <div className="bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900/20 
                    dark:to-blue-900/20 rounded-xl p-4 border border-purple-100 dark:border-purple-800">
        <div className="grid grid-cols-4 gap-4">
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400">Capital</p>
            <p className="text-lg font-semibold text-gray-900 dark:text-white">
              {CURRENCY_SYMBOLS[currency] || currency}{capital.toLocaleString()}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400">Risk Profile</p>
            <p className="text-lg font-semibold text-gray-900 dark:text-white capitalize">
              {riskProfile}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400">Time Horizon</p>
            <p className="text-lg font-semibold text-gray-900 dark:text-white">
              {strategyPeriodWeeks} weeks
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400">Recommended Method</p>
            <p className="text-lg font-semibold text-gray-900 dark:text-white">
              {riskProfile === 'prudent' ? 'Min Variance' : 
               riskProfile === 'aggressive' ? 'Max Sharpe' : 'Risk Parity'}
            </p>
          </div>
        </div>
      </div>

      {/* Optimization Methods */}
      <div>
        <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
          Available Optimization Methods
        </h3>
        <div className="grid grid-cols-3 gap-3">
          {methods.map((method) => {
            const isRecommended = method.risk_profiles.includes(riskProfile as any);
            return (
              <div
                key={method.id}
                className={`p-3 rounded-lg border cursor-pointer transition-all
                  ${isRecommended 
                    ? 'border-purple-300 dark:border-purple-700 bg-purple-50 dark:bg-purple-900/20' 
                    : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800'}
                  hover:shadow-md`}
                onClick={() => {
                  setShowOptimizeModal(true);
                }}
              >
                <div className="flex items-start gap-3">
                  <div className={`p-2 rounded-lg ${isRecommended ? 'bg-purple-100 dark:bg-purple-800' : 'bg-gray-100 dark:bg-gray-700'}`}>
                    {methodIcons[method.id]}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                        {method.name}
                      </p>
                      {isRecommended && (
                        <span className="text-xs bg-purple-100 dark:bg-purple-800 text-purple-700 
                                       dark:text-purple-300 px-2 py-0.5 rounded-full">
                          Recommended
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">
                      {method.description}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Pending Proposals */}
      {pendingProposals.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
            <Clock className="w-4 h-4" />
            Pending Proposals ({pendingProposals.length})
          </h3>
          <div className="space-y-3">
            {pendingProposals.map((proposal) => (
              <ProposalCard
                key={proposal.id}
                proposal={proposal}
                onView={() => setSelectedProposal(proposal)}
                onApprove={() => handleAction(proposal.id, 'approve')}
                onReject={() => handleAction(proposal.id, 'reject')}
                onDelete={() => handleDelete(proposal.id)}
              />
            ))}
          </div>
        </div>
      )}

      {/* History */}
      {historyProposals.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
            Proposal History
          </h3>
          <div className="space-y-2">
            {historyProposals.slice(0, 5).map((proposal) => (
              <div
                key={proposal.id}
                onClick={() => setSelectedProposal(proposal)}
                className="flex items-center justify-between p-3 bg-white dark:bg-gray-800 
                         rounded-lg border border-gray-200 dark:border-gray-700 
                         cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-750"
              >
                <div className="flex items-center gap-3">
                  {proposal.status === 'approved' && <CheckCircle className="w-4 h-4 text-green-500" />}
                  {proposal.status === 'rejected' && <XCircle className="w-4 h-4 text-red-500" />}
                  {proposal.status === 'expired' && <Clock className="w-4 h-4 text-gray-400" />}
                  {proposal.status === 'executed' && <CheckCircle className="w-4 h-4 text-blue-500" />}
                  
                  <div>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      {proposal.methodology}
                    </p>
                    <p className="text-xs text-gray-500">
                      {new Date(proposal.created_at).toLocaleDateString()} · 
                      {proposal.allocations.length} positions
                    </p>
                  </div>
                </div>
                
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      {(proposal.expected_return * 100).toFixed(1)}% return
                    </p>
                    <p className="text-xs text-gray-500">
                      {(proposal.expected_volatility * 100).toFixed(1)}% vol
                    </p>
                  </div>
                  <ChevronRight className="w-4 h-4 text-gray-400" />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {proposals.length === 0 && (
        <div className="text-center py-12 bg-gray-50 dark:bg-gray-800/50 rounded-xl">
          <Sparkles className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            No optimization proposals yet
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            Generate your first portfolio optimization to get AI-powered allocation recommendations
          </p>
          <button
            onClick={() => setShowOptimizeModal(true)}
            className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
          >
            Start Optimization
          </button>
        </div>
      )}

      {/* Modals */}
      {showOptimizeModal && (
        <OptimizationModal
          methods={methods}
          riskProfile={riskProfile}
          isOptimizing={optimizing}
          onOptimize={handleOptimize}
          onClose={() => setShowOptimizeModal(false)}
        />
      )}

      {selectedProposal && (
        <ProposalDetailModal
          proposal={selectedProposal}
          onApprove={() => handleAction(selectedProposal.id, 'approve')}
          onReject={() => handleAction(selectedProposal.id, 'reject')}
          onExecute={() => handleExecute(selectedProposal.id)}
          onClose={() => setSelectedProposal(null)}
        />
      )}
    </div>
  );
};

export default PortfolioOptimizer;
