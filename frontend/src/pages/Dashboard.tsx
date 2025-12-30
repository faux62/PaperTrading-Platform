/**
 * Dashboard Page - Real Data Implementation
 */
import { useEffect, useState } from 'react';
import { clsx } from 'clsx';
import { useNavigate } from 'react-router-dom';
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  PieChart,
  Activity,
  ArrowUpRight,
  ArrowDownRight,
  Plus,
  Briefcase,
  RefreshCw,
  AlertTriangle,
  Bell,
  CheckCircle,
} from 'lucide-react';
import { Layout } from '../components/layout';
import { Card, CardHeader, CardContent, Badge, Button, Spinner } from '../components/common';
import { portfolioApi, tradingApi, marketApi } from '../services/api';

// Types
interface Portfolio {
  id: number;
  name: string;
  cash_balance: number;
  initial_capital: number;
  currency: string;
}

interface Position {
  id: number;
  symbol: string;
  quantity: number;
  average_cost: number;
  current_price?: number;
  market_value?: number;
  unrealized_pnl?: number;
  unrealized_pnl_percent?: number;
  native_currency?: string;  // Currency the symbol is quoted in (e.g., USD)
  avg_cost_portfolio?: number;  // Average cost in portfolio currency
}

interface Trade {
  id: number;
  symbol: string;
  trade_type: string;
  quantity: number;
  price: number;
  executed_price?: number;
  executed_quantity?: number;
  created_at: string;
  native_currency?: string;  // Currency the symbol is quoted in
  exchange_rate?: number;
}

interface MarketIndex {
  name: string;
  symbol: string;
  region: string;
  type: string;
  value: number;
  change: number;
}

interface DashboardStats {
  totalValue: number;
  dailyChange: number;
  dailyChangePercent: number;
  overnightChange: number;
  overnightChangePercent: number;
  unrealizedPL: number;
  unrealizedPLPercent: number;
  cashAvailable: number;
  buyingPower: number;
}

// Alert types for Morning Briefing
interface MorningAlert {
  id: string;
  type: 'loss' | 'stop_loss' | 'profit' | 'info';
  symbol: string;
  message: string;
  value?: number;
  percent?: number;
  priority: 'urgent' | 'high' | 'medium' | 'low';
}

// Region display order and labels
const REGION_ORDER = ['US', 'EU', 'Asia', 'Crypto', 'Commodities'];
const REGION_LABELS: Record<string, string> = {
  US: '🇺🇸 US Markets',
  EU: '🇪🇺 European Markets', 
  Asia: '🌏 Asian Markets',
  Crypto: '₿ Crypto',
  Commodities: '🏆 Commodities',
};

const StatCard = ({
  title,
  value,
  change,
  changePercent,
  icon: Icon,
  iconBg,
  loading = false,
}: {
  title: string;
  value: string;
  change?: number;
  changePercent?: number;
  icon: React.ComponentType<{ className?: string }>;
  iconBg: string;
  loading?: boolean;
}) => {
  const isPositive = (change ?? 0) >= 0;
  
  return (
    <Card>
      <CardContent className="p-6">
        {loading ? (
          <div className="flex items-center justify-center h-20">
            <Spinner size="md" />
          </div>
        ) : (
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm text-surface-400">{title}</p>
              <p className="text-2xl font-bold text-white mt-1">{value}</p>
              {changePercent !== undefined && (
                <div className="flex items-center gap-1 mt-2">
                  {isPositive ? (
                    <ArrowUpRight className="w-4 h-4 text-success-400" />
                  ) : (
                    <ArrowDownRight className="w-4 h-4 text-danger-400" />
                  )}
                  <span
                    className={clsx(
                      'text-sm font-medium',
                      isPositive ? 'text-success-400' : 'text-danger-400'
                    )}
                  >
                    {isPositive ? '+' : ''}{changePercent.toFixed(2)}%
                  </span>
                  {change !== undefined && (
                    <span className="text-sm text-surface-400 ml-1">
                      ({isPositive ? '+' : ''}${Math.abs(change).toLocaleString()})
                    </span>
                  )}
                </div>
              )}
            </div>
            <div className={clsx('p-3 rounded-lg', iconBg)}>
              <Icon className="w-6 h-6 text-white" />
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

// Empty State Component
const EmptyState = ({ 
  title, 
  description, 
  actionLabel, 
  onAction,
  icon: Icon 
}: { 
  title: string; 
  description: string; 
  actionLabel?: string;
  onAction?: () => void;
  icon: React.ComponentType<{ className?: string }>;
}) => (
  <div className="flex flex-col items-center justify-center py-12 text-center">
    <div className="p-4 bg-surface-800 rounded-full mb-4">
      <Icon className="w-8 h-8 text-surface-400" />
    </div>
    <h3 className="text-lg font-medium text-white mb-2">{title}</h3>
    <p className="text-surface-400 mb-4 max-w-md">{description}</p>
    {actionLabel && onAction && (
      <Button onClick={onAction} className="gap-2">
        <Plus className="w-4 h-4" />
        {actionLabel}
      </Button>
    )}
  </div>
);

// Morning Alerts Panel Component
const AlertsPanel = ({ 
  alerts, 
  loading 
}: { 
  alerts: MorningAlert[];
  loading: boolean;
}) => {
  const getAlertIcon = (type: MorningAlert['type']) => {
    switch (type) {
      case 'loss':
      case 'stop_loss':
        return <AlertTriangle className="w-4 h-4" />;
      case 'profit':
        return <TrendingUp className="w-4 h-4" />;
      default:
        return <Bell className="w-4 h-4" />;
    }
  };

  const getAlertColor = (type: MorningAlert['type'], priority: MorningAlert['priority']) => {
    if (type === 'loss' || type === 'stop_loss') {
      return priority === 'urgent' ? 'bg-danger-500/20 border-danger-500' : 'bg-danger-500/10 border-danger-400';
    }
    if (type === 'profit') {
      return 'bg-success-500/10 border-success-400';
    }
    return 'bg-primary-500/10 border-primary-400';
  };

  const getTextColor = (type: MorningAlert['type']) => {
    if (type === 'loss' || type === 'stop_loss') return 'text-danger-400';
    if (type === 'profit') return 'text-success-400';
    return 'text-primary-400';
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Bell className="w-5 h-5 text-warning-400" />
            <h3 className="text-lg font-semibold text-white">Morning Alerts</h3>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <Spinner size="md" />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bell className="w-5 h-5 text-warning-400" />
            <h3 className="text-lg font-semibold text-white">Morning Alerts</h3>
          </div>
          {alerts.length > 0 && (
            <Badge color={alerts.some(a => a.priority === 'urgent') ? 'danger' : 'warning'}>
              {alerts.length} alert{alerts.length !== 1 ? 's' : ''}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {alerts.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-6 text-center">
            <div className="p-3 bg-success-500/10 rounded-full mb-3">
              <CheckCircle className="w-6 h-6 text-success-400" />
            </div>
            <p className="text-surface-300 text-sm">All positions healthy!</p>
            <p className="text-surface-500 text-xs mt-1">No alerts requiring attention</p>
          </div>
        ) : (
          <div className="space-y-2">
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className={clsx(
                  'p-3 rounded-lg border-l-4 flex items-start gap-3',
                  getAlertColor(alert.type, alert.priority)
                )}
              >
                <div className={clsx('mt-0.5', getTextColor(alert.type))}>
                  {getAlertIcon(alert.type)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-white">{alert.symbol}</span>
                    {alert.priority === 'urgent' && (
                      <Badge color="danger" size="sm">URGENT</Badge>
                    )}
                  </div>
                  <p className="text-sm text-surface-300 mt-0.5">{alert.message}</p>
                  {alert.percent !== undefined && (
                    <p className={clsx('text-sm font-medium mt-1', getTextColor(alert.type))}>
                      {alert.percent >= 0 ? '+' : ''}{alert.percent.toFixed(2)}%
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

const Dashboard = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [recentTrades, setRecentTrades] = useState<Trade[]>([]);
  const [marketIndices, setMarketIndices] = useState<MarketIndex[]>([]);
  const [morningAlerts, setMorningAlerts] = useState<MorningAlert[]>([]);
  const [stats, setStats] = useState<DashboardStats>({
    totalValue: 0,
    dailyChange: 0,
    dailyChangePercent: 0,
    overnightChange: 0,
    overnightChangePercent: 0,
    unrealizedPL: 0,
    unrealizedPLPercent: 0,
    cashAvailable: 0,
    buyingPower: 0,
  });

  const hasPortfolio = portfolios.length > 0;
  const hasPositions = positions.length > 0;

  // Fetch market indices using public endpoint
  const fetchMarketIndices = async () => {
    try {
      const indicesData = await marketApi.getIndices();
      
      const indices: MarketIndex[] = Object.values(indicesData).map((quote: any) => ({
        name: quote.name,
        symbol: quote.symbol,
        region: quote.region || 'Other',
        type: quote.type || 'index',
        value: quote.price || 0,
        change: quote.change_percent || 0,
      }));
      
      setMarketIndices(indices);
    } catch (error) {
      console.warn('Failed to fetch market indices:', error);
      setMarketIndices([]);
    }
  };

  // Fetch all dashboard data
  const fetchDashboardData = async (isRefresh = false) => {
    if (isRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }

    try {
      // Fetch portfolios
      const portfoliosData = await portfolioApi.getAll();
      setPortfolios(portfoliosData);

      if (portfoliosData.length > 0) {
        let totalCash = 0;
        let allPositions: Position[] = [];
        let allTrades: Trade[] = [];

        for (const portfolio of portfoliosData) {
          totalCash += portfolio.cash_balance || 0;

          try {
            const positionsData = await portfolioApi.getPositions(portfolio.id);
            allPositions = [...allPositions, ...positionsData];
          } catch (e) {
            console.warn(`Failed to fetch positions for portfolio ${portfolio.id}`);
          }

          try {
            const tradesData = await tradingApi.getTradeHistory(portfolio.id);
            allTrades = [...allTrades, ...tradesData.slice(0, 5)];
          } catch (e) {
            console.warn(`Failed to fetch trades for portfolio ${portfolio.id}`);
          }
        }

        // NOTE: Positions from backend already have:
        // - market_value: in portfolio currency (EUR) - already FX-converted
        // - unrealized_pnl: in portfolio currency (EUR) - already FX-converted
        // - current_price: current price in native currency
        // - average_cost: avg cost in native currency
        // DO NOT recalculate these values in frontend as it ignores FX conversion!

        setPositions(allPositions);
        setRecentTrades(allTrades.slice(0, 5));

        // Generate morning alerts based on position performance
        const alerts: MorningAlert[] = [];
        for (const position of allPositions) {
          const pnlPercent = position.unrealized_pnl_percent || 0;
          
          // Alert for positions with loss > 2%
          if (pnlPercent <= -5) {
            alerts.push({
              id: `loss-${position.id}`,
              type: 'loss',
              symbol: position.symbol,
              message: 'Critical loss - consider closing position',
              percent: pnlPercent,
              priority: 'urgent',
            });
          } else if (pnlPercent <= -2) {
            alerts.push({
              id: `loss-${position.id}`,
              type: 'loss',
              symbol: position.symbol,
              message: 'Position in loss overnight - monitor closely',
              percent: pnlPercent,
              priority: 'high',
            });
          }
          
          // Alert for positions with good profit (for trailing stop suggestion)
          if (pnlPercent >= 5) {
            alerts.push({
              id: `profit-${position.id}`,
              type: 'profit',
              symbol: position.symbol,
              message: 'Good profit - consider setting trailing stop',
              percent: pnlPercent,
              priority: 'medium',
            });
          }
        }
        
        // Sort alerts by priority (urgent first)
        const priorityOrder = { urgent: 0, high: 1, medium: 2, low: 3 };
        alerts.sort((a, b) => priorityOrder[a.priority] - priorityOrder[b.priority]);
        setMorningAlerts(alerts);

        // Calculate stats using pre-converted values from backend
        // market_value and unrealized_pnl are already in portfolio currency (EUR)
        const totalMarketValue = allPositions.reduce((sum, p) => sum + (p.market_value || 0), 0);
        const totalUnrealizedPL = allPositions.reduce((sum, p) => sum + (p.unrealized_pnl || 0), 0);
        const totalValue = totalCash + totalMarketValue;
        
        // Calculate unrealized PL percent based on market value vs cost basis
        // cost_basis in portfolio currency = market_value - unrealized_pnl
        const totalCostBasis = totalMarketValue - totalUnrealizedPL;

        // Fetch daily stats (daily change and overnight change) from backend
        let dailyChange = 0;
        let dailyChangePercent = 0;
        let overnightChange = 0;
        let overnightChangePercent = 0;

        for (const portfolio of portfoliosData) {
          try {
            const dailyStats = await portfolioApi.getDailyStats(portfolio.id);
            dailyChange += dailyStats.daily_change || 0;
            overnightChange += dailyStats.overnight_change || 0;
          } catch (e) {
            console.warn(`Failed to fetch daily stats for portfolio ${portfolio.id}`);
          }
        }

        // Calculate percentages based on previous day value
        const previousDayValue = totalValue - dailyChange;
        if (previousDayValue > 0) {
          dailyChangePercent = (dailyChange / previousDayValue) * 100;
        }
        // Overnight is typically same calculation for single-day context
        const prevOvernightValue = totalValue - overnightChange;
        if (prevOvernightValue > 0) {
          overnightChangePercent = (overnightChange / prevOvernightValue) * 100;
        }

        setStats({
          totalValue,
          dailyChange,
          dailyChangePercent,
          overnightChange,
          overnightChangePercent,
          unrealizedPL: totalUnrealizedPL,
          unrealizedPLPercent: totalCostBasis > 0 ? (totalUnrealizedPL / totalCostBasis) * 100 : 0,
          cashAvailable: totalCash,
          buyingPower: totalCash,  // No margin - buying power equals cash
        });
      }

      await fetchMarketIndices();

    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(() => fetchMarketIndices(), 60000);
    return () => clearInterval(interval);
  }, []);

  const formatCurrency = (value: number, currency: string = 'EUR') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 2,
    }).format(value);
  };

  // Format with native currency symbol for individual assets
  const formatNativeCurrency = (value: number, nativeCurrency?: string) => {
    const currency = nativeCurrency || 'USD';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 2,
    }).format(value);
  };

  // Get portfolio currency (from first portfolio or default to EUR)
  const portfolioCurrency = portfolios[0]?.currency || 'EUR';

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffHours < 1) return 'Just now';
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    if (diffDays === 1) return 'Yesterday';
    return `${diffDays} days ago`;
  };

  const topPositions = [...positions]
    .sort((a, b) => (b.market_value || 0) - (a.market_value || 0))
    .slice(0, 5);

  return (
    <Layout title="Dashboard">
      {/* Refresh Button */}
      <div className="flex justify-end mb-4">
        <Button
          variant="outline"
          size="sm"
          onClick={() => fetchDashboardData(true)}
          disabled={refreshing}
          className="gap-2"
        >
          <RefreshCw className={clsx('w-4 h-4', refreshing && 'animate-spin')} />
          Refresh
        </Button>
      </div>

      {/* Stats Grid - Row 1: Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-4">
        <StatCard
          title="Portfolio Value"
          value={hasPortfolio ? formatCurrency(stats.totalValue, portfolioCurrency) : '€0.00'}
          icon={DollarSign}
          iconBg="bg-primary-500/20"
          loading={loading}
        />
        <StatCard
          title="Daily Change"
          value={hasPositions ? `${stats.dailyChange >= 0 ? '+' : ''}${formatCurrency(stats.dailyChange, portfolioCurrency)}` : '€0.00'}
          change={hasPositions ? stats.dailyChange : undefined}
          changePercent={hasPositions && stats.dailyChangePercent !== 0 ? stats.dailyChangePercent : undefined}
          icon={stats.dailyChange >= 0 ? TrendingUp : TrendingDown}
          iconBg={stats.dailyChange >= 0 ? 'bg-success-500/20' : 'bg-danger-500/20'}
          loading={loading}
        />
        <StatCard
          title="Overnight Change"
          value={hasPositions ? `${stats.overnightChange >= 0 ? '+' : ''}${formatCurrency(stats.overnightChange, portfolioCurrency)}` : '€0.00'}
          change={hasPositions ? stats.overnightChange : undefined}
          changePercent={hasPositions && stats.overnightChangePercent !== 0 ? stats.overnightChangePercent : undefined}
          icon={stats.overnightChange >= 0 ? TrendingUp : TrendingDown}
          iconBg={stats.overnightChange >= 0 ? 'bg-success-500/20' : 'bg-danger-500/20'}
          loading={loading}
        />
        <StatCard
          title="Unrealized P&L"
          value={hasPositions ? `${stats.unrealizedPL >= 0 ? '+' : ''}${formatCurrency(stats.unrealizedPL, portfolioCurrency)}` : '€0.00'}
          changePercent={hasPositions ? stats.unrealizedPLPercent : undefined}
          icon={stats.unrealizedPL >= 0 ? TrendingUp : TrendingDown}
          iconBg={stats.unrealizedPL >= 0 ? 'bg-success-500/20' : 'bg-danger-500/20'}
          loading={loading}
        />
      </div>

      {/* Stats Grid - Row 2: Cash & Buying Power */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <StatCard
          title="Cash Available"
          value={hasPortfolio ? formatCurrency(stats.cashAvailable, portfolioCurrency) : '€0.00'}
          icon={PieChart}
          iconBg="bg-secondary-500/20"
          loading={loading}
        />
        <StatCard
          title="Buying Power"
          value={hasPortfolio ? formatCurrency(stats.buyingPower, portfolioCurrency) : '€0.00'}
          icon={Activity}
          iconBg="bg-warning-500/20"
          loading={loading}
        />
      </div>

      {/* Morning Alerts Panel - Only show if has positions */}
      {hasPositions && (
        <div className="mb-6">
          <AlertsPanel alerts={morningAlerts} loading={loading} />
        </div>
      )}

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Top Positions */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <h3 className="text-lg font-semibold text-white">Top Positions</h3>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Spinner size="lg" />
              </div>
            ) : !hasPortfolio ? (
              <EmptyState
                icon={Briefcase}
                title="No Portfolio Yet"
                description="Create your first portfolio to start tracking your positions and trades."
                actionLabel="Create Portfolio"
                onAction={() => navigate('/portfolio')}
              />
            ) : !hasPositions ? (
              <EmptyState
                icon={PieChart}
                title="No Positions"
                description="You don't have any open positions yet. Start trading to see your positions here."
                actionLabel="Start Trading"
                onAction={() => navigate('/trading')}
              />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="border-b border-surface-700">
                    <tr>
                      <th className="text-left text-sm font-medium text-surface-400 p-4">Symbol</th>
                      <th className="text-right text-sm font-medium text-surface-400 p-4">Shares</th>
                      <th className="text-right text-sm font-medium text-surface-400 p-4">Value</th>
                      <th className="text-right text-sm font-medium text-surface-400 p-4">P&L</th>
                    </tr>
                  </thead>
                  <tbody>
                    {topPositions.map((position) => (
                      <tr
                        key={position.id}
                        className="border-b border-surface-700/50 hover:bg-surface-800/50 transition-colors"
                      >
                        <td className="p-4">
                          <p className="font-medium text-white">{position.symbol}</p>
                          <p className="text-sm text-surface-400">
                            Avg: {formatNativeCurrency(position.average_cost, position.native_currency)}
                          </p>
                        </td>
                        <td className="p-4 text-right text-surface-300">
                          {position.quantity}
                        </td>
                        <td className="p-4 text-right font-medium text-white">
                          {formatCurrency(position.market_value || 0, portfolioCurrency)}
                        </td>
                        <td className="p-4 text-right">
                          <Badge color={(position.unrealized_pnl || 0) >= 0 ? 'success' : 'danger'}>
                            {(position.unrealized_pnl_percent || 0) >= 0 ? '+' : ''}
                            {(position.unrealized_pnl_percent || 0).toFixed(2)}%
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Market Overview - Grouped by Region */}
        <Card className="lg:col-span-1 lg:row-span-2">
          <CardHeader>
            <h3 className="text-lg font-semibold text-white">Market Overview</h3>
          </CardHeader>
          <CardContent className="max-h-[600px] overflow-y-auto">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Spinner size="lg" />
              </div>
            ) : (
              <div className="space-y-4">
                {REGION_ORDER.map((region) => {
                  const regionIndices = marketIndices.filter(m => m.region === region);
                  if (regionIndices.length === 0) return null;
                  
                  return (
                    <div key={region}>
                      <p className="text-xs font-medium text-surface-400 uppercase tracking-wider mb-2">
                        {REGION_LABELS[region] || region}
                      </p>
                      <div className="space-y-2">
                        {regionIndices.map((market) => (
                          <div
                            key={market.symbol}
                            className="flex items-center justify-between p-2 bg-surface-800/50 rounded-lg"
                          >
                            <div className="min-w-0 flex-1">
                              <p className="font-medium text-white text-sm truncate">{market.name}</p>
                              <p className="text-xs text-surface-400">
                                {market.value > 0 ? market.value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : '—'}
                              </p>
                            </div>
                            <div
                              className={clsx(
                                'flex items-center gap-1 ml-2',
                                market.change >= 0 ? 'text-success-400' : 'text-danger-400'
                              )}
                            >
                              {market.change >= 0 ? (
                                <TrendingUp className="w-3 h-3" />
                              ) : (
                                <TrendingDown className="w-3 h-3" />
                              )}
                              <span className="font-medium text-sm">
                                {market.value > 0 ? `${market.change >= 0 ? '+' : ''}${market.change.toFixed(2)}%` : '—'}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent Trades */}
      <Card className="mt-6">
        <CardHeader>
          <h3 className="text-lg font-semibold text-white">Recent Trades</h3>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Spinner size="lg" />
            </div>
          ) : !hasPortfolio ? (
            <EmptyState
              icon={Activity}
              title="No Trades Yet"
              description="Create a portfolio and start trading to see your trade history."
              actionLabel="Create Portfolio"
              onAction={() => navigate('/portfolio')}
            />
          ) : recentTrades.length === 0 ? (
            <EmptyState
              icon={Activity}
              title="No Recent Trades"
              description="You haven't made any trades yet. Go to the trading page to place your first order."
              actionLabel="Start Trading"
              onAction={() => navigate('/trading')}
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="border-b border-surface-700">
                  <tr>
                    <th className="text-left text-sm font-medium text-surface-400 p-4">Symbol</th>
                    <th className="text-left text-sm font-medium text-surface-400 p-4">Type</th>
                    <th className="text-right text-sm font-medium text-surface-400 p-4">Shares</th>
                    <th className="text-right text-sm font-medium text-surface-400 p-4">Price</th>
                    <th className="text-right text-sm font-medium text-surface-400 p-4">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {recentTrades.map((trade) => (
                    <tr
                      key={trade.id}
                      className="border-b border-surface-700/50 hover:bg-surface-800/50 transition-colors"
                    >
                      <td className="p-4 font-medium text-white">{trade.symbol}</td>
                      <td className="p-4">
                        <Badge color={trade.trade_type?.toLowerCase() === 'buy' ? 'success' : 'danger'}>
                          {trade.trade_type?.toUpperCase() || 'N/A'}
                        </Badge>
                      </td>
                      <td className="p-4 text-right text-surface-300">{trade.executed_quantity || trade.quantity}</td>
                      <td className="p-4 text-right font-medium text-white">
                        {formatNativeCurrency(trade.executed_price || trade.price, trade.native_currency)}
                      </td>
                      <td className="p-4 text-right text-surface-400">
                        {formatTime(trade.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </Layout>
  );
};

export default Dashboard;
