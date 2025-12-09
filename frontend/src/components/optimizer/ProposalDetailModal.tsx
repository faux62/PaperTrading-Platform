// Proposal Detail Modal - Full view of optimization proposal

import React from 'react';
import { 
  X, 
  TrendingUp, 
  TrendingDown,
  PieChart,
  BarChart3,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Info,
  Clock,
  DollarSign,
  Percent,
  Activity
} from 'lucide-react';
import type { PortfolioProposal } from '../../types/optimizer';

interface Props {
  proposal: PortfolioProposal;
  onApprove: () => void;
  onReject: () => void;
  onClose: () => void;
}

const ProposalDetailModal: React.FC<Props> = ({
  proposal,
  onApprove,
  onReject,
  onClose,
}) => {
  const isPending = proposal.status === 'pending';
  const sectorColors = [
    'bg-blue-500', 'bg-green-500', 'bg-purple-500', 'bg-amber-500',
    'bg-pink-500', 'bg-cyan-500', 'bg-red-500', 'bg-indigo-500'
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative bg-white dark:bg-gray-800 rounded-2xl shadow-2xl 
                    w-full max-w-4xl mx-4 max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b 
                      border-gray-200 dark:border-gray-700 flex-shrink-0">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Portfolio Proposal
              </h2>
              <span className={`px-2 py-0.5 text-xs font-medium rounded-full
                ${proposal.status === 'pending' ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400' :
                  proposal.status === 'approved' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' :
                  proposal.status === 'rejected' ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' :
                  'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-400'}`}>
                {proposal.status}
              </span>
            </div>
            <p className="text-sm text-gray-500">{proposal.methodology}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 
                     rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {/* Summary */}
          <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-xl">
            <div className="flex items-start gap-3">
              <Info className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-blue-700 dark:text-blue-400">
                {proposal.summary}
              </p>
            </div>
          </div>

          {/* Key Metrics */}
          <div className="grid grid-cols-4 gap-4">
            <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-xl">
              <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400 mb-1">
                <TrendingUp className="w-4 h-4" />
                <span className="text-xs">Expected Return</span>
              </div>
              <p className={`text-2xl font-bold ${proposal.expected_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {(proposal.expected_return * 100).toFixed(1)}%
              </p>
              <p className="text-xs text-gray-500 mt-1">annualized</p>
            </div>
            
            <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-xl">
              <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400 mb-1">
                <Activity className="w-4 h-4" />
                <span className="text-xs">Volatility</span>
              </div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {(proposal.expected_volatility * 100).toFixed(1)}%
              </p>
              <p className="text-xs text-gray-500 mt-1">annualized</p>
            </div>
            
            <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-xl">
              <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400 mb-1">
                <BarChart3 className="w-4 h-4" />
                <span className="text-xs">Sharpe Ratio</span>
              </div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {proposal.sharpe_ratio.toFixed(2)}
              </p>
              <p className="text-xs text-gray-500 mt-1">risk-adjusted</p>
            </div>
            
            <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-xl">
              <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400 mb-1">
                <TrendingDown className="w-4 h-4" />
                <span className="text-xs">Max Drawdown</span>
              </div>
              <p className="text-2xl font-bold text-red-600">
                {(proposal.max_drawdown * 100).toFixed(1)}%
              </p>
              <p className="text-xs text-gray-500 mt-1">historical</p>
            </div>
          </div>

          {/* Sector Allocation */}
          <div>
            <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
              <PieChart className="w-4 h-4" />
              Sector Allocation
            </h3>
            <div className="space-y-2">
              {Object.entries(proposal.sector_weights)
                .sort((a, b) => b[1] - a[1])
                .map(([sector, weight], idx) => (
                  <div key={sector} className="flex items-center gap-3">
                    <div className={`w-3 h-3 rounded-full ${sectorColors[idx % sectorColors.length]}`} />
                    <span className="text-sm text-gray-700 dark:text-gray-300 flex-1">
                      {sector}
                    </span>
                    <div className="w-32 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                      <div 
                        className={`h-full ${sectorColors[idx % sectorColors.length]}`}
                        style={{ width: `${weight * 100}%` }}
                      />
                    </div>
                    <span className="text-sm font-medium text-gray-900 dark:text-white w-12 text-right">
                      {(weight * 100).toFixed(0)}%
                    </span>
                  </div>
              ))}
            </div>
          </div>

          {/* Holdings */}
          <div>
            <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
              Proposed Allocations ({proposal.allocations.length} positions)
            </h3>
            <div className="bg-gray-50 dark:bg-gray-700/50 rounded-xl overflow-hidden">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-gray-600">
                    <th className="text-left text-xs font-medium text-gray-500 dark:text-gray-400 p-3">Symbol</th>
                    <th className="text-left text-xs font-medium text-gray-500 dark:text-gray-400 p-3">Sector</th>
                    <th className="text-right text-xs font-medium text-gray-500 dark:text-gray-400 p-3">Weight</th>
                    <th className="text-right text-xs font-medium text-gray-500 dark:text-gray-400 p-3">Shares</th>
                    <th className="text-right text-xs font-medium text-gray-500 dark:text-gray-400 p-3">Value</th>
                    <th className="text-right text-xs font-medium text-gray-500 dark:text-gray-400 p-3">Change</th>
                  </tr>
                </thead>
                <tbody>
                  {proposal.allocations.map((alloc) => (
                    <tr key={alloc.symbol} className="border-b border-gray-100 dark:border-gray-700 last:border-0">
                      <td className="p-3">
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 rounded-lg bg-white dark:bg-gray-600 
                                        flex items-center justify-center text-xs font-bold 
                                        text-gray-700 dark:text-gray-300 shadow-sm">
                            {alloc.symbol.slice(0, 2)}
                          </div>
                          <div>
                            <p className="text-sm font-medium text-gray-900 dark:text-white">
                              {alloc.symbol}
                            </p>
                            <p className="text-xs text-gray-500 truncate max-w-[120px]">
                              {alloc.name}
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="p-3">
                        <span className="text-sm text-gray-600 dark:text-gray-400">
                          {alloc.sector || '-'}
                        </span>
                      </td>
                      <td className="p-3 text-right">
                        <span className="text-sm font-medium text-gray-900 dark:text-white">
                          {(alloc.weight * 100).toFixed(1)}%
                        </span>
                      </td>
                      <td className="p-3 text-right">
                        <span className="text-sm text-gray-600 dark:text-gray-400">
                          {alloc.shares?.toLocaleString() || '-'}
                        </span>
                      </td>
                      <td className="p-3 text-right">
                        <span className="text-sm text-gray-600 dark:text-gray-400">
                          {alloc.value ? `$${alloc.value.toLocaleString()}` : '-'}
                        </span>
                      </td>
                      <td className="p-3 text-right">
                        {alloc.change !== 0 ? (
                          <span className={`text-sm font-medium ${alloc.change > 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {alloc.change > 0 ? '+' : ''}{(alloc.change * 100).toFixed(1)}%
                          </span>
                        ) : (
                          <span className="text-sm text-gray-400">-</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Considerations */}
          {proposal.considerations.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-500" />
                Important Considerations
              </h3>
              <ul className="space-y-2">
                {proposal.considerations.map((consideration, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm text-gray-600 dark:text-gray-400">
                    <span className="text-amber-500 mt-1">•</span>
                    {consideration}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Turnover & Costs */}
          {(proposal.turnover > 0 || proposal.estimated_costs > 0) && (
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-xl">
                <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400 mb-1">
                  <Percent className="w-4 h-4" />
                  <span className="text-xs">Portfolio Turnover</span>
                </div>
                <p className="text-xl font-semibold text-gray-900 dark:text-white">
                  {(proposal.turnover * 100).toFixed(1)}%
                </p>
              </div>
              <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-xl">
                <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400 mb-1">
                  <DollarSign className="w-4 h-4" />
                  <span className="text-xs">Estimated Costs</span>
                </div>
                <p className="text-xl font-semibold text-gray-900 dark:text-white">
                  ${proposal.estimated_costs.toLocaleString()}
                </p>
              </div>
            </div>
          )}

          {/* Expiration */}
          {proposal.expires_at && isPending && (
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
              <Clock className="w-4 h-4" />
              Expires: {new Date(proposal.expires_at).toLocaleString()}
            </div>
          )}
        </div>

        {/* Footer Actions */}
        {isPending && (
          <div className="p-4 border-t border-gray-200 dark:border-gray-700 
                        bg-gray-50 dark:bg-gray-800/50 flex gap-3 flex-shrink-0">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-2.5 text-sm font-medium text-gray-700 
                       dark:text-gray-300 bg-white dark:bg-gray-700 border 
                       border-gray-300 dark:border-gray-600 rounded-lg 
                       hover:bg-gray-50 dark:hover:bg-gray-600"
            >
              Close
            </button>
            <button
              onClick={onReject}
              className="px-6 py-2.5 text-sm font-medium text-red-600 dark:text-red-400 
                       bg-red-50 dark:bg-red-900/20 rounded-lg hover:bg-red-100 
                       dark:hover:bg-red-900/40 flex items-center gap-2"
            >
              <XCircle className="w-4 h-4" />
              Reject
            </button>
            <button
              onClick={onApprove}
              className="px-6 py-2.5 text-sm font-medium text-white bg-green-600 
                       rounded-lg hover:bg-green-700 flex items-center gap-2"
            >
              <CheckCircle className="w-4 h-4" />
              Approve Proposal
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default ProposalDetailModal;
