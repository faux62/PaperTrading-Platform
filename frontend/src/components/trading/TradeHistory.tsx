/**
 * Trade History Component
 * Complete trade log with filters and export
 */
import { useState, useEffect, useCallback } from 'react';
import {
  History,
  Download,
  Filter,
  Search,
  TrendingUp,
  TrendingDown,
  CheckCircle,
  Clock,
  XCircle,
  ChevronRight,
} from 'lucide-react';
import Card, { CardContent, CardHeader } from '../common/Card';
import Button from '../common/Button';

// Types
interface Trade {
  id: number;
  portfolio_id: number;
  symbol: string;
  trade_type: 'buy' | 'sell';
  order_type: string;
  status: 'pending' | 'filled' | 'partial' | 'cancelled' | 'rejected';
  quantity: number;
  price: number | null;
  executed_price: number | null;
  executed_quantity: number | null;
  total_value: number | null;
  commission: number | null;
  realized_pnl: number | null;
  native_currency?: string;  // Currency the symbol is quoted in
  exchange_rate?: number;    // FX rate at execution
  created_at: string;
  executed_at: string | null;
  notes: string | null;
}

// Currency symbols for display
const CURRENCY_SYMBOLS: Record<string, string> = {
  USD: '$', EUR: '€', GBP: '£', JPY: '¥', CHF: 'CHF', CAD: 'C$', AUD: 'A$'
};

interface TradeHistoryProps {
  portfolioId: number | string;
  onTradeClick?: (trade: Trade) => void;
  baseCurrency?: string;  // Portfolio base currency
}

const STATUS_CONFIG = {
  pending: { icon: Clock, color: 'text-yellow-500', bg: 'bg-yellow-500/10' },
  filled: { icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-500/10' },
  partial: { icon: Clock, color: 'text-blue-500', bg: 'bg-blue-500/10' },
  cancelled: { icon: XCircle, color: 'text-gray-500', bg: 'bg-gray-500/10' },
  rejected: { icon: XCircle, color: 'text-red-500', bg: 'bg-red-500/10' },
};

export function TradeHistory({ portfolioId, onTradeClick, baseCurrency = 'USD' }: TradeHistoryProps) {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  
  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [symbolFilter, setSymbolFilter] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  const ITEMS_PER_PAGE = 20;

  const fetchTrades = useCallback(async (reset = false) => {
    setLoading(true);
    try {
      const token = localStorage.getItem('accessToken');
      const offset = reset ? 0 : page * ITEMS_PER_PAGE;
      
      let url = `/api/v1/trades/?portfolio_id=${portfolioId}&limit=${ITEMS_PER_PAGE}&offset=${offset}`;
      if (statusFilter) url += `&status=${statusFilter}`;
      if (typeFilter) url += `&trade_type=${typeFilter}`;
      if (symbolFilter) url += `&symbol=${symbolFilter.toUpperCase()}`;
      
      const response = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      if (response.ok) {
        const data = await response.json();
        if (reset) {
          setTrades(data);
          setPage(0);
        } else {
          setTrades(prev => [...prev, ...data]);
        }
        setHasMore(data.length === ITEMS_PER_PAGE);
      }
    } catch (error) {
      console.error('Failed to fetch trades:', error);
    } finally {
      setLoading(false);
    }
  }, [portfolioId, page, statusFilter, typeFilter, symbolFilter]);

  useEffect(() => {
    fetchTrades(true);
  }, [statusFilter, typeFilter, symbolFilter]); // eslint-disable-line react-hooks/exhaustive-deps

  const loadMore = () => {
    setPage(p => p + 1);
    fetchTrades(false);
  };

  const exportCSV = async () => {
    try {
      const token = localStorage.getItem('accessToken');
      let url = `/api/v1/trades/export/${portfolioId}`;
      if (statusFilter) url += `?status=${statusFilter}`;
      
      const response = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      if (response.ok) {
        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = `trades_${portfolioId}_${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(downloadUrl);
      }
    } catch (error) {
      console.error('Failed to export:', error);
    }
  };

  // Format currency in portfolio BASE currency (for totals, P&L)
  const formatCurrency = (value: number | null) => {
    if (value === null) return '-';
    const symbol = CURRENCY_SYMBOLS[baseCurrency] || baseCurrency + ' ';
    return `${symbol}${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  // Format price in NATIVE currency (executed price)
  const formatNativePrice = (value: number | null, nativeCurrency?: string) => {
    if (value === null) return '-';
    const currency = nativeCurrency || 'USD';
    const symbol = CURRENCY_SYMBOLS[currency] || currency + ' ';
    return `${symbol}${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <History className="h-5 w-5 text-primary-500" />
            <h2 className="text-lg font-semibold text-white">Trade History</h2>
          </div>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setShowFilters(!showFilters)}
            >
              <Filter className="h-4 w-4" />
            </Button>
            <Button size="sm" variant="outline" onClick={exportCSV}>
              <Download className="h-4 w-4 mr-2" />
              Export
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* Filters */}
        {showFilters && (
          <div className="mb-4 p-4 rounded-lg bg-surface-800 space-y-3">
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="text-xs text-surface-400">Status</label>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="w-full mt-1 px-3 py-2 bg-surface-900 border border-surface-700 rounded-lg text-white text-sm"
                >
                  <option value="">All Statuses</option>
                  <option value="pending">Pending</option>
                  <option value="filled">Filled</option>
                  <option value="partial">Partial</option>
                  <option value="cancelled">Cancelled</option>
                  <option value="rejected">Rejected</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-surface-400">Type</label>
                <select
                  value={typeFilter}
                  onChange={(e) => setTypeFilter(e.target.value)}
                  className="w-full mt-1 px-3 py-2 bg-surface-900 border border-surface-700 rounded-lg text-white text-sm"
                >
                  <option value="">All Types</option>
                  <option value="buy">Buy</option>
                  <option value="sell">Sell</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-surface-400">Symbol</label>
                <div className="relative mt-1">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-surface-500" />
                  <input
                    type="text"
                    value={symbolFilter}
                    onChange={(e) => setSymbolFilter(e.target.value)}
                    placeholder="AAPL..."
                    className="w-full pl-9 pr-3 py-2 bg-surface-900 border border-surface-700 rounded-lg text-white text-sm"
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Trade List */}
        <div className="space-y-2">
          {loading && trades.length === 0 ? (
            <div className="space-y-2">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-16 bg-surface-800 animate-pulse rounded-lg" />
              ))}
            </div>
          ) : trades.length === 0 ? (
            <div className="text-center py-8 text-surface-400">
              No trades found
            </div>
          ) : (
            <>
              {trades.map((trade) => {
                const statusColor = STATUS_CONFIG[trade.status]?.color || 'text-gray-500';
                const statusBg = STATUS_CONFIG[trade.status]?.bg || 'bg-gray-500/10';
                
                return (
                  <div
                    key={trade.id}
                    onClick={() => onTradeClick?.(trade)}
                    className="flex items-center justify-between p-4 rounded-lg bg-surface-800 hover:bg-surface-700/50 cursor-pointer transition-colors"
                  >
                    <div className="flex items-center gap-4">
                      {/* Type Icon */}
                      <div className={`p-2 rounded-lg ${
                        trade.trade_type === 'buy' ? 'bg-green-500/10' : 'bg-red-500/10'
                      }`}>
                        {trade.trade_type === 'buy' ? (
                          <TrendingUp className="h-4 w-4 text-green-500" />
                        ) : (
                          <TrendingDown className="h-4 w-4 text-red-500" />
                        )}
                      </div>
                      
                      {/* Details */}
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-white">{trade.symbol}</span>
                          <span className={`px-2 py-0.5 rounded text-xs ${statusBg} ${statusColor}`}>
                            {trade.status.toUpperCase()}
                          </span>
                          {trade.native_currency && trade.native_currency !== baseCurrency && (
                            <span className="text-xs text-surface-500">
                              ({trade.native_currency})
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-surface-400">
                          {trade.trade_type.toUpperCase()} {trade.quantity} shares
                          {trade.executed_price && ` @ ${formatNativePrice(trade.executed_price, trade.native_currency)}`}
                        </p>
                      </div>
                    </div>
                    
                    <div className="text-right">
                      <p className="font-mono text-white">
                        {formatCurrency(trade.total_value)}
                      </p>
                      {trade.realized_pnl !== null && trade.realized_pnl !== 0 && (
                        <p className={`text-sm ${
                          trade.realized_pnl >= 0 ? 'text-green-500' : 'text-red-500'
                        }`}>
                          P&L: {formatCurrency(trade.realized_pnl)}
                        </p>
                      )}
                      <p className="text-xs text-surface-500">
                        {formatDate(trade.created_at)}
                      </p>
                    </div>
                  </div>
                );
              })}
              
              {/* Load More */}
              {hasMore && (
                <div className="text-center pt-4">
                  <Button
                    variant="ghost"
                    onClick={loadMore}
                    disabled={loading}
                  >
                    {loading ? 'Loading...' : 'Load More'}
                    <ChevronRight className="h-4 w-4 ml-2" />
                  </Button>
                </div>
              )}
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default TradeHistory;
