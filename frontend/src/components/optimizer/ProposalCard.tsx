// Proposal Card Component

import React from 'react';
import { 
  TrendingUp, 
  TrendingDown,
  Clock,
  CheckCircle,
  XCircle,
  Trash2,
  Eye,
  PieChart
} from 'lucide-react';
import type { PortfolioProposal } from '../../types/optimizer';

interface Props {
  proposal: PortfolioProposal;
  onView: () => void;
  onApprove: () => void;
  onReject: () => void;
  onDelete: () => void;
}

const ProposalCard: React.FC<Props> = ({
  proposal,
  onView,
  onApprove,
  onReject,
  onDelete,
}) => {
  const isExpiringSoon = proposal.expires_at && 
    new Date(proposal.expires_at).getTime() - Date.now() < 6 * 60 * 60 * 1000; // 6 hours

  const topAllocations = proposal.allocations.slice(0, 5);
  const topSectors = Object.entries(proposal.sector_weights)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 
                  dark:border-gray-700 overflow-hidden hover:shadow-lg transition-shadow">
      {/* Header */}
      <div className="p-4 border-b border-gray-100 dark:border-gray-700">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className={`px-2 py-0.5 text-xs font-medium rounded-full
                ${proposal.proposal_type === 'initial' 
                  ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                  : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'}`}>
                {proposal.proposal_type === 'initial' ? 'New Portfolio' : 'Rebalance'}
              </span>
              {isExpiringSoon && (
                <span className="px-2 py-0.5 text-xs font-medium rounded-full 
                             bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400
                             flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  Expiring soon
                </span>
              )}
            </div>
            <h3 className="text-sm font-medium text-gray-900 dark:text-white mt-2">
              {proposal.methodology}
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Created {new Date(proposal.created_at).toLocaleString()}
            </p>
          </div>
          
          <button
            onClick={onDelete}
            className="p-1.5 text-gray-400 hover:text-red-500 rounded-lg 
                     hover:bg-red-50 dark:hover:bg-red-900/20"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Metrics */}
      <div className="p-4 grid grid-cols-4 gap-4 bg-gray-50 dark:bg-gray-800/50">
        <div>
          <p className="text-xs text-gray-500 dark:text-gray-400">Expected Return</p>
          <p className={`text-lg font-semibold flex items-center gap-1
            ${proposal.expected_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {proposal.expected_return >= 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
            {(proposal.expected_return * 100).toFixed(1)}%
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 dark:text-gray-400">Volatility</p>
          <p className="text-lg font-semibold text-gray-900 dark:text-white">
            {(proposal.expected_volatility * 100).toFixed(1)}%
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 dark:text-gray-400">Sharpe Ratio</p>
          <p className="text-lg font-semibold text-gray-900 dark:text-white">
            {proposal.sharpe_ratio.toFixed(2)}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 dark:text-gray-400">Max Drawdown</p>
          <p className="text-lg font-semibold text-red-600">
            {(proposal.max_drawdown * 100).toFixed(1)}%
          </p>
        </div>
      </div>

      {/* Allocations Preview */}
      <div className="p-4 border-t border-gray-100 dark:border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
            Top Holdings ({proposal.allocations.length} total)
          </p>
          <div className="flex items-center gap-2">
            <PieChart className="w-4 h-4 text-gray-400" />
            <span className="text-xs text-gray-500">
              {topSectors.map(([sector, weight]) => 
                `${sector}: ${(weight * 100).toFixed(0)}%`
              ).join(' · ')}
            </span>
          </div>
        </div>
        
        <div className="space-y-2">
          {topAllocations.map((alloc) => (
            <div key={alloc.symbol} className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-gray-100 dark:bg-gray-700 
                              flex items-center justify-center text-xs font-medium 
                              text-gray-700 dark:text-gray-300">
                  {alloc.symbol.slice(0, 2)}
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {alloc.symbol}
                  </p>
                  <p className="text-xs text-gray-500 truncate max-w-[150px]">
                    {alloc.sector}
                  </p>
                </div>
              </div>
              
              <div className="text-right">
                <p className="text-sm font-medium text-gray-900 dark:text-white">
                  {(alloc.weight * 100).toFixed(1)}%
                </p>
                {alloc.change !== 0 && (
                  <p className={`text-xs ${alloc.change > 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {alloc.change > 0 ? '+' : ''}{(alloc.change * 100).toFixed(1)}%
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Summary */}
      <div className="px-4 py-3 bg-blue-50 dark:bg-blue-900/20 border-t border-blue-100 dark:border-blue-800">
        <p className="text-xs text-blue-700 dark:text-blue-400 line-clamp-2">
          {proposal.summary}
        </p>
      </div>

      {/* Actions */}
      <div className="p-4 border-t border-gray-100 dark:border-gray-700 flex gap-2">
        <button
          onClick={onView}
          className="flex-1 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 
                   bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 
                   dark:hover:bg-gray-600 flex items-center justify-center gap-2"
        >
          <Eye className="w-4 h-4" />
          View Details
        </button>
        <button
          onClick={onReject}
          className="px-4 py-2 text-sm font-medium text-red-600 dark:text-red-400 
                   bg-red-50 dark:bg-red-900/20 rounded-lg hover:bg-red-100 
                   dark:hover:bg-red-900/40 flex items-center justify-center gap-2"
        >
          <XCircle className="w-4 h-4" />
          Reject
        </button>
        <button
          onClick={onApprove}
          className="px-4 py-2 text-sm font-medium text-white bg-green-600 
                   rounded-lg hover:bg-green-700 flex items-center justify-center gap-2"
        >
          <CheckCircle className="w-4 h-4" />
          Approve
        </button>
      </div>
    </div>
  );
};

export default ProposalCard;
