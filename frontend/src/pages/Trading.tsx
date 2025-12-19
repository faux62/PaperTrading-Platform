/**
 * Trading Page
 * 
 * Main trading interface with order form and position table.
 */
import { useState, useEffect } from 'react';
import { Layout } from '../components/layout';
import { Card, CardContent, CardHeader } from '../components/common';
import { OrderForm, PositionTable } from '../components/trading';
import type { Position } from '../components/trading';
import { portfolioApi, tradingApi } from '../services/api';
import { 
  TrendingUp, 
  Wallet, 
  BarChart3, 
  History,
  RefreshCw,
  AlertCircle,
  Download,
  Filter
} from 'lucide-react';
import { clsx } from 'clsx';

// Currency symbols
const CURRENCY_SYMBOLS: Record<string, string> = {
  USD: '$', EUR: '€', GBP: '£', JPY: '¥', CHF: 'CHF', CAD: 'C$', AUD: 'A$'
};

interface Portfolio {
  id: number;
  name: string;
  cash_balance: number;
  initial_capital: number;
  currency: string;
}

interface Trade {
  id: number;
  symbol: string;
  trade_type: string;
  order_type: string;
  quantity: number;
  price: number;
  executed_price: number | null;
  total_value: number | null;
  native_currency: string;
  exchange_rate: number | null;
  status: string;
  executed_at: string | null;
  created_at: string;
}

const Trading = () => {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [selectedPortfolio, setSelectedPortfolio] = useState<Portfolio | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [recentTrades, setRecentTrades] = useState<Trade[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'trade' | 'positions' | 'history'>('trade');
  const [isRefreshingPrices, setIsRefreshingPrices] = useState(false);
  
  // Trade filters state
  const [filterSymbol, setFilterSymbol] = useState('');
  const [filterStartDate, setFilterStartDate] = useState('');
  const [filterEndDate, setFilterEndDate] = useState('');
  const [isExporting, setIsExporting] = useState(false);

  // Load portfolios on mount
  useEffect(() => {
    loadPortfolios();
  }, []);

  // Load positions when portfolio changes
  useEffect(() => {
    if (selectedPortfolio) {
      loadPositions();
      loadRecentTrades();
    }
  }, [selectedPortfolio?.id]);

  const loadPortfolios = async () => {
    try {
      setIsLoading(true);
      const data = await portfolioApi.getAll();
      // portfolioApi.getAll() returns array directly
      const portfolioList = Array.isArray(data) ? data : (data.portfolios || []);
      setPortfolios(portfolioList);
      if (portfolioList.length > 0 && !selectedPortfolio) {
        // Load full portfolio details for the first one
        const fullPortfolio = await portfolioApi.getById(portfolioList[0].id);
        setSelectedPortfolio(fullPortfolio);
      } else if (selectedPortfolio) {
        // Refresh current selected portfolio details
        const fullPortfolio = await portfolioApi.getById(selectedPortfolio.id);
        setSelectedPortfolio(fullPortfolio);
      }
    } catch (err) {
      setError('Failed to load portfolios');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const loadPositions = async () => {
    if (!selectedPortfolio) return;
    try {
      const data = await portfolioApi.getPositions(selectedPortfolio.id);
      
      // Calculate total portfolio value for weight calculation
      const totalValue = data.reduce((sum: number, p: any) => 
        sum + (parseFloat(p.market_value) || 0), 0
      );
      
      // Map API response to Position interface
      // API returns: avg_cost, market_value, unrealized_pnl_percent
      // UI expects: average_cost, current_value, unrealized_pnl_pct
      setPositions(data.map((p: any) => {
        const marketValue = parseFloat(p.market_value) || 0;
        return {
          symbol: p.symbol,
          exchange: p.exchange,
          quantity: parseFloat(p.quantity) || 0,
          average_cost: parseFloat(p.avg_cost) || 0,
          current_price: parseFloat(p.current_price) || 0,
          current_value: marketValue,
          unrealized_pnl: parseFloat(p.unrealized_pnl) || 0,
          unrealized_pnl_pct: parseFloat(p.unrealized_pnl_percent) || 0,
          weight_pct: totalValue > 0 ? (marketValue / totalValue) * 100 : 0,
          native_currency: p.native_currency || 'USD'  // Currency the symbol is quoted in
        };
      }));
    } catch (err) {
      console.error('Failed to load positions:', err);
    }
  };

  const loadRecentTrades = async () => {
    if (!selectedPortfolio) return;
    try {
      console.log('loadRecentTrades: Fetching trades for portfolio', selectedPortfolio.id);
      const params: any = {};
      if (filterSymbol) params.symbol = filterSymbol.toUpperCase();
      if (filterStartDate) params.start_date = filterStartDate + 'T00:00:00';
      if (filterEndDate) params.end_date = filterEndDate + 'T23:59:59';
      
      const data = await tradingApi.getTradeHistory(selectedPortfolio.id, params);
      console.log('loadRecentTrades: Raw API response:', data);
      // Convert string values to numbers
      const parsedTrades = data.slice(0, 50).map((t: any) => ({
        ...t,
        quantity: parseFloat(t.quantity) || 0,
        price: parseFloat(t.price) || 0,
        executed_price: parseFloat(t.executed_price) || 0,
        executed_quantity: parseFloat(t.executed_quantity) || 0,
        total_value: parseFloat(t.total_value) || 0,
        commission: parseFloat(t.commission) || 0,
        realized_pnl: t.realized_pnl ? parseFloat(t.realized_pnl) : null,
      }));
      console.log('loadRecentTrades: Parsed trades:', parsedTrades);
      setRecentTrades(parsedTrades);
    } catch (err) {
      console.error('Failed to load trades:', err);
    }
  };

  const handleExportCSV = async () => {
    if (!selectedPortfolio) return;
    setIsExporting(true);
    try {
      const params = new URLSearchParams();
      if (filterStartDate) params.append('start_date', filterStartDate + 'T00:00:00');
      if (filterEndDate) params.append('end_date', filterEndDate + 'T23:59:59');
      
      const url = `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/trades/export/${selectedPortfolio.id}?${params.toString()}`;
      
      const response = await fetch(url);
      if (!response.ok) throw new Error('Export failed');
      
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = `trades_portfolio_${selectedPortfolio.id}_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(downloadUrl);
    } catch (err) {
      console.error('Export failed:', err);
      setError('Failed to export trades');
    } finally {
      setIsExporting(false);
    }
  };

  const handleApplyFilters = () => {
    loadRecentTrades();
  };

  const handleClearFilters = () => {
    setFilterSymbol('');
    setFilterStartDate('');
    setFilterEndDate('');
  };

  const handleOrderSubmit = async (order: any) => {
    console.log('Trading.handleOrderSubmit called with:', order);
    try {
      console.log('Calling tradingApi.createOrder...');
      const result = await tradingApi.createOrder(order);
      console.log('tradingApi.createOrder returned:', result);
      
      // Check if order was successful (backend returns success: false with HTTP 200)
      if (!result.success) {
        const errorMessage = result.errors?.join(', ') || result.message || 'Order failed';
        console.error('Order rejected:', errorMessage);
        throw new Error(errorMessage);
      }
      
      // Refresh data only on success
      await loadPositions();
      await loadRecentTrades();
      // Also refresh portfolio to get updated cash balance
      await loadPortfolios();
    } catch (err) {
      console.error('tradingApi.createOrder error:', err);
      throw err;
    }
  };

  const handleSellPosition = (_symbol: string, _quantity: number) => {
    // Switch to trade tab and pre-fill sell order
    setActiveTab('trade');
    // TODO: Pre-fill the order form with sell data
  };

  const refreshData = async () => {
    await loadPortfolios();
    if (selectedPortfolio) {
      await loadPositions();
      await loadRecentTrades();
    }
  };

  const handleRefreshPrices = async () => {
    if (!selectedPortfolio) return;
    setIsRefreshingPrices(true);
    try {
      const result = await portfolioApi.refreshPrices(selectedPortfolio.id);
      // Update positions with refreshed data
      const totalValue = result.positions.reduce((sum: number, p: any) => 
        sum + (parseFloat(p.market_value) || 0), 0
      );
      setPositions(result.positions.map((p: any) => {
        const marketValue = parseFloat(p.market_value) || 0;
        return {
          symbol: p.symbol,
          exchange: p.exchange,
          quantity: parseFloat(p.quantity) || 0,
          average_cost: parseFloat(p.avg_cost) || 0,
          current_price: parseFloat(p.current_price) || 0,
          current_value: marketValue,
          unrealized_pnl: parseFloat(p.unrealized_pnl) || 0,
          unrealized_pnl_pct: parseFloat(p.unrealized_pnl_percent) || 0,
          weight_pct: totalValue > 0 ? (marketValue / totalValue) * 100 : 0,
          native_currency: p.native_currency || 'USD'
        };
      }));
    } catch (err) {
      console.error('Failed to refresh prices:', err);
    } finally {
      setIsRefreshingPrices(false);
    }
  };

  if (isLoading) {
    return (
      <Layout title="Trading">
        <div className="animate-pulse space-y-6">
          <div className="h-20 bg-gray-200 dark:bg-gray-700 rounded-lg" />
          <div className="h-96 bg-gray-200 dark:bg-gray-700 rounded-lg" />
        </div>
      </Layout>
    );
  }

  if (portfolios.length === 0) {
    return (
      <Layout title="Trading">
        <Card>
          <CardContent className="p-12 text-center">
            <Wallet className="w-16 h-16 mx-auto text-gray-400 mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
              No Portfolio Found
            </h2>
            <p className="text-gray-500 dark:text-gray-400 mb-4">
              Create a portfolio first to start trading.
            </p>
            <a
              href="/portfolio"
              className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Create Portfolio
            </a>
          </CardContent>
        </Card>
      </Layout>
    );
  }

  return (
    <Layout title="Trading">
      <div className="space-y-6">
        {/* Portfolio Selector and Stats */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
          {/* Portfolio Selector */}
          <Card>
            <CardContent className="p-4">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Active Portfolio
              </label>
              <select
                value={selectedPortfolio?.id || ''}
                onChange={async (e) => {
                  const portfolioId = parseInt(e.target.value);
                  try {
                    const fullPortfolio = await portfolioApi.getById(portfolioId);
                    setSelectedPortfolio(fullPortfolio);
                  } catch (err) {
                    console.error('Failed to load portfolio:', err);
                  }
                }}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg
                           bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                {portfolios.map(p => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </CardContent>
          </Card>

          {/* Cash Balance */}
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-100 dark:bg-green-900/30 rounded-lg">
                  <Wallet className="w-5 h-5 text-green-600 dark:text-green-400" />
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Cash Available</p>
                  <p className="text-xl font-semibold text-gray-900 dark:text-white">
                    {CURRENCY_SYMBOLS[selectedPortfolio?.currency || 'USD'] || '$'}{selectedPortfolio?.cash_balance?.toLocaleString() || '0'}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Positions Count */}
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                  <BarChart3 className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Open Positions</p>
                  <p className="text-xl font-semibold text-gray-900 dark:text-white">
                    {positions.length}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Refresh Button */}
          <Card>
            <CardContent className="p-4 flex items-center justify-center">
              <button
                onClick={refreshData}
                className="flex items-center gap-2 px-4 py-2 text-gray-700 dark:text-gray-300
                           hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                Refresh Data
              </button>
            </CardContent>
          </Card>
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-200 dark:border-gray-700">
          <nav className="flex gap-4">
            <button
              onClick={() => setActiveTab('trade')}
              className={clsx(
                'pb-3 px-1 font-medium text-sm border-b-2 transition-colors',
                activeTab === 'trade'
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
              )}
            >
              <TrendingUp className="w-4 h-4 inline mr-2" />
              Trade
            </button>
            <button
              onClick={() => setActiveTab('positions')}
              className={clsx(
                'pb-3 px-1 font-medium text-sm border-b-2 transition-colors',
                activeTab === 'positions'
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
              )}
            >
              <BarChart3 className="w-4 h-4 inline mr-2" />
              Positions ({positions.length})
            </button>
            <button
              onClick={() => setActiveTab('history')}
              className={clsx(
                'pb-3 px-1 font-medium text-sm border-b-2 transition-colors',
                activeTab === 'history'
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
              )}
            >
              <History className="w-4 h-4 inline mr-2" />
              History
            </button>
          </nav>
        </div>

        {/* Tab Content */}
        {activeTab === 'trade' && selectedPortfolio && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Order Form */}
            <Card className="lg:col-span-1">
              <CardHeader>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">New Order</h3>
              </CardHeader>
              <CardContent>
                <OrderForm
                  portfolioId={selectedPortfolio.id}
                  availableCash={selectedPortfolio.cash_balance}
                  positions={positions}
                  currency={selectedPortfolio.currency}
                  onSubmit={handleOrderSubmit}
                />
              </CardContent>
            </Card>

            {/* Quick Position Overview */}
            <Card className="lg:col-span-2">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Current Positions</h3>
                  <button
                    onClick={handleRefreshPrices}
                    disabled={isRefreshingPrices}
                    className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 
                               border border-gray-300 dark:border-gray-600 rounded-lg 
                               hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors
                               disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <RefreshCw className={clsx("w-4 h-4", isRefreshingPrices && "animate-spin")} />
                    {isRefreshingPrices ? 'Refreshing...' : 'Refresh Prices'}
                  </button>
                </div>
              </CardHeader>
              <CardContent>
                {positions.length > 0 ? (
                  <PositionTable
                    positions={positions.slice(0, 5)}
                    onSell={handleSellPosition}
                    currency={selectedPortfolio?.currency || 'EUR'}
                  />
                ) : (
                  <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                    <TrendingUp className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>No positions yet. Start trading!</p>
                  </div>
                )}
                {positions.length > 5 && (
                  <button
                    onClick={() => setActiveTab('positions')}
                    className="mt-4 text-sm text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    View all {positions.length} positions →
                  </button>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === 'positions' && (
          <Card>
            <CardHeader>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">All Positions</h3>
            </CardHeader>
            <CardContent>
              <PositionTable
                positions={positions}
                onSell={handleSellPosition}
                currency={selectedPortfolio?.currency || 'EUR'}
              />
            </CardContent>
          </Card>
        )}

        {activeTab === 'history' && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between flex-wrap gap-4">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Trade History</h3>
                <button
                  onClick={handleExportCSV}
                  disabled={isExporting || recentTrades.length === 0}
                  className="flex items-center gap-2 px-3 py-2 text-sm bg-green-600 text-white rounded-lg
                             hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <Download className="w-4 h-4" />
                  {isExporting ? 'Exporting...' : 'Export CSV'}
                </button>
              </div>
            </CardHeader>
            <CardContent>
              {/* Filters Section */}
              <div className="mb-6 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                <div className="flex items-center gap-2 mb-3">
                  <Filter className="w-4 h-4 text-gray-500" />
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Filters</span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div>
                    <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Symbol</label>
                    <input
                      type="text"
                      value={filterSymbol}
                      onChange={(e) => setFilterSymbol(e.target.value)}
                      placeholder="e.g. AAPL"
                      className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg
                                 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">From Date</label>
                    <input
                      type="date"
                      value={filterStartDate}
                      onChange={(e) => setFilterStartDate(e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg
                                 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">To Date</label>
                    <input
                      type="date"
                      value={filterEndDate}
                      onChange={(e) => setFilterEndDate(e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg
                                 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    />
                  </div>
                  <div className="flex items-end gap-2">
                    <button
                      onClick={handleApplyFilters}
                      className="flex-1 px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                    >
                      Apply
                    </button>
                    <button
                      onClick={handleClearFilters}
                      className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400 border border-gray-300 dark:border-gray-600 
                                 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                    >
                      Clear
                    </button>
                  </div>
                </div>
              </div>
              
              {recentTrades.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase border-b border-gray-200 dark:border-gray-700">
                        <th className="pb-3 pr-4">Date</th>
                        <th className="pb-3 px-4">Symbol</th>
                        <th className="pb-3 px-4">Type</th>
                        <th className="pb-3 px-4 text-right">Qty</th>
                        <th className="pb-3 px-4 text-right">Price</th>
                        <th className="pb-3 px-4 text-right">Total</th>
                        <th className="pb-3 pl-4">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                      {recentTrades.map((trade) => (
                        <tr key={trade.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                          <td className="py-3 pr-4 text-sm text-gray-600 dark:text-gray-400">
                            {new Date(trade.executed_at || trade.created_at).toLocaleDateString()}
                          </td>
                          <td className="py-3 px-4 font-medium text-gray-900 dark:text-white">
                            {trade.symbol}
                          </td>
                          <td className="py-3 px-4">
                            <span className={clsx(
                              'px-2 py-1 rounded text-xs font-medium',
                              trade.trade_type === 'buy'
                                ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                                : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                            )}>
                              {trade.trade_type.toUpperCase()}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-right font-mono text-gray-900 dark:text-white">
                            {trade.quantity}
                          </td>
                          <td className="py-3 px-4 text-right font-mono text-gray-600 dark:text-gray-400">
                            {/* Price is in NATIVE currency */}
                            {(trade.executed_price || trade.price)?.toFixed(2)} {trade.native_currency || ''}
                          </td>
                          <td className="py-3 px-4 text-right font-mono font-medium text-gray-900 dark:text-white">
                            {/* total_value is already in PORTFOLIO currency */}
                            {CURRENCY_SYMBOLS[selectedPortfolio?.currency || 'EUR'] || '€'}{trade.total_value?.toFixed(2) || '—'}
                          </td>
                          <td className="py-3 pl-4">
                            <span className={clsx(
                              'px-2 py-1 rounded text-xs font-medium',
                              trade.status === 'executed'
                                ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                                : trade.status === 'pending'
                                ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                                : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                            )}>
                              {trade.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                  <History className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>No trade history yet</p>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Error Display */}
        {error && (
          <div className="flex items-center gap-2 text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 p-4 rounded-lg">
            <AlertCircle className="w-5 h-5" />
            <span>{error}</span>
          </div>
        )}
      </div>
    </Layout>
  );
};

export default Trading;

