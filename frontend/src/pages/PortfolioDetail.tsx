/**
 * Portfolio Detail Page
 * Shows detailed portfolio information with rebalancing wizard and position management
 */
import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  PieChart,
  Activity,
  DollarSign,
  BarChart3,
  Target,
  AlertCircle,
  Clock,
  Wallet,
  Scale,
  Sparkles,
} from 'lucide-react';
import { Layout } from '../components/layout';
import { Card, CardContent, CardHeader, CardTitle, Spinner, Badge } from '../components/common';
import { RebalancingWizard, TradeHistory } from '../components/trading';
import { PortfolioOptimizer } from '../components/optimizer';
import { Position, Portfolio, Trade } from '../types';
import { tokenStorage } from '../services/tokenStorage';

interface PortfolioStats {
  total_value: number;
  cash_balance: number;
  invested_value: number;
  total_return: number;
  total_return_pct: number;
  day_change: number;
  day_change_pct: number;
  positions_count: number;
}

const PortfolioDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const portfolioId = id || '';

  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [stats, setStats] = useState<PortfolioStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'positions' | 'optimizer' | 'rebalance' | 'history'>('overview');
  const [showRebalanceWizard, setShowRebalanceWizard] = useState(false);

  const fetchPortfolioData = useCallback(async () => {
    if (!portfolioId) return;

    setIsLoading(true);
    setError(null);

    try {
      const token = tokenStorage.getAccessToken();
      const headers = {
        'Content-Type': 'application/json',
        ...(token && { Authorization: `Bearer ${token}` }),
      };

      // Fetch portfolio details, positions, and trades in parallel
      const [portfolioRes, positionsRes, tradesRes] = await Promise.all([
        fetch(`/api/v1/portfolios/${portfolioId}`, { headers }),
        fetch(`/api/v1/positions/portfolio/${portfolioId}`, { headers }),
        fetch(`/api/v1/trades?portfolio_id=${portfolioId}&limit=50`, { headers }),
      ]);

      if (!portfolioRes.ok) {
        throw new Error('Portfolio not found');
      }

      const portfolioData = await portfolioRes.json();
      
      // Parse positions from response
      let positionsData: any[] = [];
      if (positionsRes.ok) {
        const rawPositions = await positionsRes.json();
        // API returns {portfolio_id, positions: [...], count, total_market_value, ...}
        positionsData = Array.isArray(rawPositions) 
          ? rawPositions 
          : rawPositions.positions || rawPositions.items || [];
      }
      
      const tradesData = tradesRes.ok ? await tradesRes.json() : [];

      setPortfolio(portfolioData);
      setPositions(positionsData);
      setTrades(Array.isArray(tradesData) ? tradesData : tradesData.items || []);

      // Calculate stats - use market_value which is already in portfolio currency
      const investedValue = positionsData.reduce?.(
        (sum: number, p: any) => sum + (parseFloat(p.market_value) || 0),
        0
      ) || 0;
      const totalReturn = positionsData.reduce?.(
        (sum: number, p: any) => sum + (parseFloat(p.unrealized_pnl) || 0),
        0
      ) || 0;
      const initialValue = parseFloat(portfolioData.initial_capital) || 10000;
      const totalValue = parseFloat(portfolioData.cash_balance) + investedValue;

      setStats({
        total_value: totalValue,
        cash_balance: portfolioData.cash_balance || 0,
        invested_value: investedValue,
        total_return: totalReturn,
        total_return_pct: initialValue > 0 ? ((totalValue - initialValue) / initialValue) * 100 : 0,
        day_change: portfolioData.day_change || 0,
        day_change_pct: portfolioData.day_change_pct || 0,
        positions_count: positionsData?.length || 0,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load portfolio');
    } finally {
      setIsLoading(false);
    }
  }, [portfolioId]);

  useEffect(() => {
    fetchPortfolioData();
  }, [fetchPortfolioData]);

  // Get portfolio currency (default EUR)
  const portfolioCurrency = (portfolio as any)?.currency || 'EUR';
  
  const formatCurrency = (value: number, currency?: string) => {
    const curr = currency || portfolioCurrency;
    const locale = curr === 'EUR' ? 'de-DE' : curr === 'GBP' ? 'en-GB' : curr === 'JPY' ? 'ja-JP' : 'en-US';
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency: curr,
      minimumFractionDigits: curr === 'JPY' ? 0 : 2,
    }).format(value);
  };
  
  // Format price in native currency for positions
  const formatNativePrice = (value: number, nativeCurrency?: string) => {
    const curr = nativeCurrency || 'USD';
    const locale = curr === 'EUR' ? 'de-DE' : curr === 'GBP' ? 'en-GB' : curr === 'JPY' ? 'ja-JP' : 'en-US';
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency: curr,
      minimumFractionDigits: curr === 'JPY' ? 0 : 2,
    }).format(value);
  };

  const formatPercent = (value: number) => {
    const prefix = value >= 0 ? '+' : '';
    return `${prefix}${value.toFixed(2)}%`;
  };

  if (isLoading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <Spinner size="lg" />
        </div>
      </Layout>
    );
  }

  if (error || !portfolio) {
    return (
      <Layout>
        <div className="p-4">
          <button
            onClick={() => navigate('/portfolio')}
            className="flex items-center gap-2 text-surface-400 hover:text-white mb-4"
          >
            <ArrowLeft className="w-5 h-5" />
            Back to Portfolios
          </button>
          <Card>
            <CardContent className="p-8 text-center">
              <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-white mb-2">Portfolio Not Found</h2>
              <p className="text-surface-400">{error || 'The requested portfolio could not be found.'}</p>
            </CardContent>
          </Card>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="p-4 space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/portfolio')}
              className="p-2 hover:bg-surface-700 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-5 h-5 text-surface-400" />
            </button>
            <div>
              <h1 className="text-2xl font-bold text-white">{portfolio.name}</h1>
              <p className="text-surface-400">{portfolio.description || 'Paper Trading Portfolio'}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={fetchPortfolioData}
              disabled={isLoading}
              className="p-2 hover:bg-surface-700 rounded-lg transition-colors disabled:opacity-50"
              title="Refresh"
            >
              <RefreshCw className={`w-5 h-5 text-surface-400 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={() => setShowRebalanceWizard(true)}
              className="flex items-center gap-2 px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg transition-colors"
            >
              <Scale className="w-5 h-5" />
              Rebalance
            </button>
          </div>
        </div>

        {/* Stats Grid */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-2 text-surface-400 mb-1">
                  <Wallet className="w-4 h-4" />
                  <span className="text-sm">Total Value</span>
                </div>
                <p className="text-xl font-bold text-white">{formatCurrency(stats.total_value)}</p>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-2 text-surface-400 mb-1">
                  <DollarSign className="w-4 h-4" />
                  <span className="text-sm">Cash Available</span>
                </div>
                <p className="text-xl font-bold text-white">{formatCurrency(stats.cash_balance)}</p>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-2 text-surface-400 mb-1">
                  {stats.total_return >= 0 ? (
                    <TrendingUp className="w-4 h-4 text-green-400" />
                  ) : (
                    <TrendingDown className="w-4 h-4 text-red-400" />
                  )}
                  <span className="text-sm">Total Return</span>
                </div>
                <p className={`text-xl font-bold ${stats.total_return >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {formatCurrency(stats.total_return)}
                </p>
                <p className={`text-sm ${stats.total_return_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {formatPercent(stats.total_return_pct)}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-2 text-surface-400 mb-1">
                  <BarChart3 className="w-4 h-4" />
                  <span className="text-sm">Positions</span>
                </div>
                <p className="text-xl font-bold text-white">{stats.positions_count}</p>
                <p className="text-sm text-surface-400">
                  {formatCurrency(stats.invested_value)} invested
                </p>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-2 border-b border-surface-700">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-[1px] ${
              activeTab === 'overview'
                ? 'text-primary-400 border-primary-400'
                : 'text-surface-400 border-transparent hover:text-white'
            }`}
          >
            <div className="flex items-center gap-2">
              <PieChart className="w-4 h-4" />
              Overview
            </div>
          </button>
          <button
            onClick={() => setActiveTab('positions')}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-[1px] ${
              activeTab === 'positions'
                ? 'text-primary-400 border-primary-400'
                : 'text-surface-400 border-transparent hover:text-white'
            }`}
          >
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4" />
              Positions ({positions.length})
            </div>
          </button>
          <button
            onClick={() => setActiveTab('optimizer')}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-[1px] ${
              activeTab === 'optimizer'
                ? 'text-primary-400 border-primary-400'
                : 'text-surface-400 border-transparent hover:text-white'
            }`}
          >
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4" />
              AI Optimizer
            </div>
          </button>
          <button
            onClick={() => setActiveTab('rebalance')}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-[1px] ${
              activeTab === 'rebalance'
                ? 'text-primary-400 border-primary-400'
                : 'text-surface-400 border-transparent hover:text-white'
            }`}
          >
            <div className="flex items-center gap-2">
              <Target className="w-4 h-4" />
              Rebalance
            </div>
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-[1px] ${
              activeTab === 'history'
                ? 'text-primary-400 border-primary-400'
                : 'text-surface-400 border-transparent hover:text-white'
            }`}
          >
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4" />
              History
            </div>
          </button>
        </div>

        {/* Tab Content */}
        {activeTab === 'overview' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Portfolio Allocation */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <PieChart className="w-5 h-5" />
                  Allocation
                </CardTitle>
              </CardHeader>
              <CardContent>
                {positions.length > 0 ? (
                  <div className="space-y-3">
                    {positions.map((position: any) => {
                      // Use market_value which is already converted to portfolio currency
                      const value = parseFloat(position.market_value) || 0;
                      const percentage = stats && stats.total_value > 0 ? (value / stats.total_value) * 100 : 0;
                      return (
                        <div key={position.id} className="flex items-center gap-3">
                          <div className="w-12 text-sm font-medium text-white">{position.symbol}</div>
                          <div className="flex-1 h-2 bg-surface-700 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-primary-500 rounded-full"
                              style={{ width: `${Math.min(percentage, 100)}%` }}
                            />
                          </div>
                          <div className="w-16 text-right text-sm text-surface-400">
                            {percentage.toFixed(1)}%
                          </div>
                          <div className="w-24 text-right text-sm text-white">
                            {formatCurrency(value)}
                          </div>
                        </div>
                      );
                    })}
                    {stats && stats.cash_balance > 0 && (
                      <div className="flex items-center gap-3">
                        <div className="w-12 text-sm font-medium text-white">Cash</div>
                        <div className="flex-1 h-2 bg-surface-700 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-green-500 rounded-full"
                            style={{ width: `${(stats.cash_balance / stats.total_value) * 100}%` }}
                          />
                        </div>
                        <div className="w-16 text-right text-sm text-surface-400">
                          {((stats.cash_balance / stats.total_value) * 100).toFixed(1)}%
                        </div>
                        <div className="w-24 text-right text-sm text-white">
                          {formatCurrency(stats.cash_balance)}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-center text-surface-400 py-8">
                    No positions yet. Start trading to see your allocation.
                  </p>
                )}
              </CardContent>
            </Card>

            {/* Recent Trades */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Clock className="w-5 h-5" />
                  Recent Trades
                </CardTitle>
              </CardHeader>
              <CardContent>
                {trades.length > 0 ? (
                  <div className="space-y-2">
                    {trades.slice(0, 5).map((trade: any) => {
                      // Use executed_price for display, total_value for the total (already in portfolio currency)
                      const displayPrice = parseFloat(trade.executed_price) || parseFloat(trade.price) || 0;
                      const totalValue = parseFloat(trade.total_value) || 0;
                      const nativeCurrency = trade.native_currency || 'USD';
                      return (
                      <div
                        key={trade.id}
                        className="flex items-center justify-between p-2 bg-surface-800/50 rounded-lg"
                      >
                        <div className="flex items-center gap-3">
                          <Badge variant={(trade.trade_type || trade.side)?.toLowerCase() === 'buy' ? 'success' : 'danger'}>
                            {(trade.trade_type || trade.side || 'N/A').toUpperCase()}
                          </Badge>
                          <div>
                            <p className="text-sm font-medium text-white">{trade.symbol}</p>
                            <p className="text-xs text-surface-400">
                              {trade.executed_quantity || trade.quantity} @ {formatNativePrice(displayPrice, nativeCurrency)}
                            </p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-sm text-white">
                            {formatCurrency(totalValue)}
                          </p>
                          <p className="text-xs text-surface-400">
                            {new Date(trade.executed_at || trade.created_at).toLocaleDateString()}
                          </p>
                        </div>
                      </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="text-center text-surface-400 py-8">
                    No trades yet. Place your first order to see trade history.
                  </p>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === 'positions' && (
          <Card>
            <CardHeader>
              <CardTitle>Open Positions</CardTitle>
            </CardHeader>
            <CardContent>
              {positions.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="text-left text-sm text-surface-400 border-b border-surface-700">
                        <th className="pb-3 font-medium">Symbol</th>
                        <th className="pb-3 font-medium text-right">Quantity</th>
                        <th className="pb-3 font-medium text-right">Avg Price</th>
                        <th className="pb-3 font-medium text-right">Current</th>
                        <th className="pb-3 font-medium text-right">Value</th>
                        <th className="pb-3 font-medium text-right">P&L</th>
                        <th className="pb-3 font-medium text-right">%</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-surface-700">
                      {positions.map((position: any) => {
                        // API returns: avg_cost, current_price (in native currency)
                        // market_value, unrealized_pnl (in portfolio currency)
                        const nativeCurrency = position.native_currency || 'USD';
                        const avgCost = parseFloat(position.avg_cost) || 0;
                        const currentPrice = parseFloat(position.current_price) || avgCost;
                        const marketValue = parseFloat(position.market_value) || 0;
                        const pnl = parseFloat(position.unrealized_pnl) || 0;
                        const pnlPct = parseFloat(position.unrealized_pnl_percent) || 0;

                        return (
                          <tr key={position.id} className="text-sm">
                            <td className="py-3">
                              <div className="font-medium text-white">{position.symbol}</div>
                            </td>
                            <td className="py-3 text-right text-white">{position.quantity}</td>
                            <td className="py-3 text-right text-white">{formatNativePrice(avgCost, nativeCurrency)}</td>
                            <td className="py-3 text-right text-white">{formatNativePrice(currentPrice, nativeCurrency)}</td>
                            <td className="py-3 text-right text-white">{formatCurrency(marketValue)}</td>
                            <td className={`py-3 text-right ${pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                              {formatCurrency(pnl)}
                            </td>
                            <td className={`py-3 text-right ${pnlPct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                              {formatPercent(pnlPct)}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-center text-surface-400 py-8">
                  No open positions. Start trading to see your positions here.
                </p>
              )}
            </CardContent>
          </Card>
        )}

        {activeTab === 'optimizer' && (
          <PortfolioOptimizer
            portfolioId={portfolioId}
            portfolioName={portfolio.name}
            riskProfile={(portfolio as any).risk_profile || 'balanced'}
            capital={(portfolio as any).initial_capital || 100000}
            currency={(portfolio as any).currency || 'USD'}
            strategyPeriodWeeks={(portfolio as any).strategy_period_weeks || 12}
            onTradesExecuted={() => {
              // Refresh portfolio data after trades are executed
              fetchPortfolioData();
            }}
          />
        )}

        {activeTab === 'rebalance' && (
          <div className="space-y-6">
            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-white mb-2">Portfolio Rebalancing</h3>
                    <p className="text-surface-400">
                      Analyze your portfolio allocation and generate orders to rebalance to your target weights.
                    </p>
                  </div>
                  <button
                    onClick={() => setShowRebalanceWizard(true)}
                    className="flex items-center gap-2 px-6 py-3 bg-primary-500 hover:bg-primary-600 text-white rounded-lg transition-colors"
                  >
                    <Scale className="w-5 h-5" />
                    Start Rebalancing Wizard
                  </button>
                </div>
              </CardContent>
            </Card>

            {/* Current Allocation vs Target */}
            <Card>
              <CardHeader>
                <CardTitle>Current vs Target Allocation</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-surface-400 text-center py-8">
                  Set target allocations in the rebalancing wizard to see comparison.
                </p>
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === 'history' && (
          <TradeHistory portfolioId={portfolioId} portfolioCurrency={portfolioCurrency} />
        )}
      </div>

      {/* Rebalancing Wizard Modal */}
      {showRebalanceWizard && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-surface-800 rounded-xl w-full max-w-4xl max-h-[90vh] overflow-y-auto">
            <RebalancingWizard
              portfolioId={portfolioId}
              onComplete={() => {
                setShowRebalanceWizard(false);
                fetchPortfolioData();
              }}
              onCancel={() => setShowRebalanceWizard(false)}
            />
          </div>
        </div>
      )}
    </Layout>
  );
};

export default PortfolioDetail;
