/**
 * Position Table Component
 * 
 * Displays portfolio positions with current values, P&L,
 * and quick action buttons.
 */
import { useState } from 'react';
import { clsx } from 'clsx';
import {
  TrendingUp,
  TrendingDown,
  MoreVertical,
  ChevronUp,
  ChevronDown,
  Search,
  X
} from 'lucide-react';

export interface Position {
  symbol: string;
  exchange?: string;
  quantity: number;
  average_cost: number;
  current_price?: number;
  current_value?: number;
  unrealized_pnl?: number;
  unrealized_pnl_pct?: number;
  day_change?: number;
  day_change_pct?: number;
  weight_pct?: number;
  native_currency?: string;  // Currency the symbol is quoted in
}

// Currency symbols for display
const CURRENCY_SYMBOLS: Record<string, string> = {
  USD: '$', EUR: '€', GBP: '£', JPY: '¥', CHF: 'CHF', CAD: 'C$', AUD: 'A$'
};

interface PositionTableProps {
  positions: Position[];
  isLoading?: boolean;
  onSell?: (symbol: string, quantity: number) => void;
  onViewDetails?: (symbol: string) => void;
  className?: string;
  baseCurrency?: string;  // Portfolio base currency for values display
}

type SortField = 'symbol' | 'value' | 'pnl' | 'pnl_pct' | 'weight';
type SortDirection = 'asc' | 'desc';

export function PositionTable({
  positions,
  isLoading = false,
  onSell,
  onViewDetails,
  className,
  baseCurrency = 'USD'
}: PositionTableProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [sortField, setSortField] = useState<SortField>('value');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [openMenu, setOpenMenu] = useState<string | null>(null);

  // Filter positions by search term
  const filteredPositions = positions.filter(pos =>
    pos.symbol.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Sort positions
  const sortedPositions = [...filteredPositions].sort((a, b) => {
    let comparison = 0;
    
    switch (sortField) {
      case 'symbol':
        comparison = a.symbol.localeCompare(b.symbol);
        break;
      case 'value':
        comparison = (a.current_value || 0) - (b.current_value || 0);
        break;
      case 'pnl':
        comparison = (a.unrealized_pnl || 0) - (b.unrealized_pnl || 0);
        break;
      case 'pnl_pct':
        comparison = (a.unrealized_pnl_pct || 0) - (b.unrealized_pnl_pct || 0);
        break;
      case 'weight':
        comparison = (a.weight_pct || 0) - (b.weight_pct || 0);
        break;
    }
    
    return sortDirection === 'asc' ? comparison : -comparison;
  });

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const SortHeader = ({ field, children }: { field: SortField; children: React.ReactNode }) => (
    <button
      onClick={() => handleSort(field)}
      className="flex items-center gap-1 hover:text-gray-900 dark:hover:text-white transition-colors ml-auto"
    >
      {children}
      {sortField === field && (
        sortDirection === 'asc' 
          ? <ChevronUp className="w-3 h-3" />
          : <ChevronDown className="w-3 h-3" />
      )}
    </button>
  );

  // Format currency in portfolio BASE currency (for values, P&L, etc.)
  const formatBaseCurrency = (value: number | undefined) => {
    if (value === undefined) return '-';
    const symbol = CURRENCY_SYMBOLS[baseCurrency] || baseCurrency + ' ';
    return `${symbol}${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  // Format price in NATIVE currency (current price only)
  const formatNativePrice = (value: number | undefined, nativeCurrency?: string) => {
    if (value === undefined) return '-';
    const currency = nativeCurrency || 'USD';
    const symbol = CURRENCY_SYMBOLS[currency] || currency + ' ';
    return `${symbol}${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatPercent = (value: number | undefined) => {
    if (value === undefined) return '-';
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  // Calculate totals
  const totalValue = positions.reduce((sum, pos) => sum + (pos.current_value || 0), 0);
  const totalPnL = positions.reduce((sum, pos) => sum + (pos.unrealized_pnl || 0), 0);
  const totalCost = positions.reduce((sum, pos) => sum + (pos.quantity * pos.average_cost), 0);
  const totalPnLPct = totalCost > 0 ? (totalPnL / totalCost) * 100 : 0;

  if (isLoading) {
    return (
      <div className={clsx('animate-pulse', className)}>
        <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded mb-4" />
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map(i => (
            <div key={i} className="h-16 bg-gray-200 dark:bg-gray-700 rounded" />
          ))}
        </div>
      </div>
    );
  }

  if (positions.length === 0) {
    return (
      <div className={clsx(
        'text-center py-12 bg-gray-50 dark:bg-gray-800 rounded-lg',
        className
      )}>
        <TrendingUp className="w-12 h-12 mx-auto text-gray-400 mb-4" />
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
          No positions yet
        </h3>
        <p className="text-gray-500 dark:text-gray-400">
          Start trading to build your portfolio
        </p>
      </div>
    );
  }

  return (
    <div className={className}>
      {/* Search and Filter */}
      <div className="flex items-center gap-4 mb-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search positions..."
            className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg
                       bg-white dark:bg-gray-700 text-gray-900 dark:text-white
                       focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          {searchTerm && (
            <button
              onClick={() => setSearchTerm('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
        <span className="text-sm text-gray-500 dark:text-gray-400">
          {filteredPositions.length} position{filteredPositions.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider border-b border-gray-200 dark:border-gray-700">
              <th className="pb-3 pr-4">
                <SortHeader field="symbol">Symbol</SortHeader>
              </th>
              <th className="pb-3 px-4 text-right">Qty</th>
              <th className="pb-3 px-4 text-right">Avg Cost</th>
              <th className="pb-3 px-4 text-right">Price</th>
              <th className="pb-3 px-4 text-right">
                <SortHeader field="value">Value</SortHeader>
              </th>
              <th className="pb-3 px-4 text-right">
                <SortHeader field="pnl">P&L</SortHeader>
              </th>
              <th className="pb-3 px-4 text-right">
                <SortHeader field="pnl_pct">P&L %</SortHeader>
              </th>
              <th className="pb-3 px-4 text-right">
                <SortHeader field="weight">Weight</SortHeader>
              </th>
              <th className="pb-3 pl-4 w-10"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {sortedPositions.map((position) => (
              <tr 
                key={position.symbol}
                className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
              >
                <td className="py-4 pr-4">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900 
                                    flex items-center justify-center text-xs font-bold
                                    text-blue-600 dark:text-blue-300">
                      {position.symbol.slice(0, 2)}
                    </div>
                    <div>
                      <div className="font-medium text-gray-900 dark:text-white">
                        {position.symbol}
                      </div>
                      {position.exchange && (
                        <div className="text-xs text-gray-500 dark:text-gray-400">
                          {position.exchange}
                        </div>
                      )}
                    </div>
                  </div>
                </td>
                <td className="py-4 px-4 text-right font-mono text-gray-900 dark:text-white">
                  {position.quantity.toLocaleString()}
                </td>
                <td className="py-4 px-4 text-right font-mono text-gray-600 dark:text-gray-400">
                  {formatBaseCurrency(position.average_cost)}
                </td>
                <td className="py-4 px-4 text-right font-mono text-gray-900 dark:text-white">
                  {formatNativePrice(position.current_price, position.native_currency)}
                </td>
                <td className="py-4 px-4 text-right font-mono font-medium text-gray-900 dark:text-white">
                  {formatBaseCurrency(position.current_value)}
                </td>
                <td className="py-4 px-4 text-right">
                  <span className={clsx(
                    'font-mono font-medium',
                    (position.unrealized_pnl || 0) >= 0 
                      ? 'text-green-600 dark:text-green-400' 
                      : 'text-red-600 dark:text-red-400'
                  )}>
                    {(position.unrealized_pnl || 0) >= 0 ? '+' : ''}
                    {formatBaseCurrency(position.unrealized_pnl)}
                  </span>
                </td>
                <td className="py-4 px-4 text-right">
                  <div className={clsx(
                    'inline-flex items-center gap-1 px-2 py-1 rounded text-sm font-medium',
                    (position.unrealized_pnl_pct || 0) >= 0
                      ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                      : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'
                  )}>
                    {(position.unrealized_pnl_pct || 0) >= 0 
                      ? <TrendingUp className="w-3 h-3" />
                      : <TrendingDown className="w-3 h-3" />
                    }
                    {formatPercent(position.unrealized_pnl_pct)}
                  </div>
                </td>
                <td className="py-4 px-4 text-right font-mono text-gray-600 dark:text-gray-400">
                  {(position.weight_pct !== undefined && position.weight_pct !== null) 
                    ? `${position.weight_pct.toFixed(1)}%` 
                    : '0.0%'}
                </td>
                <td className="py-4 pl-4 relative">
                  <button
                    onClick={() => setOpenMenu(openMenu === position.symbol ? null : position.symbol)}
                    className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                  >
                    <MoreVertical className="w-4 h-4 text-gray-500" />
                  </button>
                  
                  {openMenu === position.symbol && (
                    <div className="absolute right-0 top-full mt-1 w-36 bg-white dark:bg-gray-800 
                                    rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 
                                    py-1 z-10">
                      {onViewDetails && (
                        <button
                          onClick={() => {
                            onViewDetails(position.symbol);
                            setOpenMenu(null);
                          }}
                          className="w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 
                                     hover:bg-gray-100 dark:hover:bg-gray-700"
                        >
                          View Details
                        </button>
                      )}
                      {onSell && (
                        <button
                          onClick={() => {
                            onSell(position.symbol, position.quantity);
                            setOpenMenu(null);
                          }}
                          className="w-full px-4 py-2 text-left text-sm text-red-600 dark:text-red-400 
                                     hover:bg-gray-100 dark:hover:bg-gray-700"
                        >
                          Sell Position
                        </button>
                      )}
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
          
          {/* Totals Row */}
          <tfoot>
            <tr className="border-t-2 border-gray-300 dark:border-gray-600 font-medium">
              <td className="pt-4 pr-4 text-gray-900 dark:text-white">
                Total ({positions.length} positions)
              </td>
              <td className="pt-4 px-4" colSpan={3}></td>
              <td className="pt-4 px-4 text-right font-mono text-gray-900 dark:text-white">
                {formatBaseCurrency(totalValue)}
              </td>
              <td className="pt-4 px-4 text-right">
                <span className={clsx(
                  'font-mono',
                  totalPnL >= 0 
                    ? 'text-green-600 dark:text-green-400' 
                    : 'text-red-600 dark:text-red-400'
                )}>
                  {totalPnL >= 0 ? '+' : ''}{formatBaseCurrency(totalPnL)}
                </span>
              </td>
              <td className="pt-4 px-4 text-right">
                <span className={clsx(
                  'font-mono',
                  totalPnLPct >= 0 
                    ? 'text-green-600 dark:text-green-400' 
                    : 'text-red-600 dark:text-red-400'
                )}>
                  {formatPercent(totalPnLPct)}
                </span>
              </td>
              <td className="pt-4 px-4 text-right text-gray-600 dark:text-gray-400">
                100%
              </td>
              <td className="pt-4 pl-4"></td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}

export default PositionTable;
