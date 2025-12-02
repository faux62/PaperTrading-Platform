/**
 * Dashboard Page
 */
import { clsx } from 'clsx';
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  PieChart,
  Activity,
  ArrowUpRight,
  ArrowDownRight,
} from 'lucide-react';
import { Layout } from '../components/layout';
import { Card, CardHeader, CardContent, Badge } from '../components/common';

// Mock data - will be replaced with real API calls
const portfolioStats = {
  totalValue: 125432.50,
  dailyChange: 2987.50,
  dailyChangePercent: 2.45,
  unrealizedPL: 5432.50,
  unrealizedPLPercent: 4.53,
  cashAvailable: 24567.50,
  buyingPower: 49135.00,
};

const topPositions = [
  { symbol: 'AAPL', name: 'Apple Inc.', value: 28450.00, change: 3.24, shares: 150 },
  { symbol: 'MSFT', name: 'Microsoft Corp.', value: 22340.00, change: -1.12, shares: 55 },
  { symbol: 'GOOGL', name: 'Alphabet Inc.', value: 18230.00, change: 2.87, shares: 12 },
  { symbol: 'AMZN', name: 'Amazon.com Inc.', value: 15670.00, change: 1.45, shares: 85 },
  { symbol: 'NVDA', name: 'NVIDIA Corp.', value: 12890.00, change: 5.67, shares: 25 },
];

const recentTrades = [
  { id: 1, symbol: 'AAPL', type: 'BUY', shares: 10, price: 189.50, time: '2 hours ago' },
  { id: 2, symbol: 'TSLA', type: 'SELL', shares: 5, price: 245.30, time: '4 hours ago' },
  { id: 3, symbol: 'MSFT', type: 'BUY', shares: 15, price: 406.20, time: 'Yesterday' },
  { id: 4, symbol: 'NVDA', type: 'BUY', shares: 8, price: 515.80, time: 'Yesterday' },
];

const marketOverview = [
  { name: 'S&P 500', value: '5,234.18', change: 0.85 },
  { name: 'NASDAQ', value: '16,428.82', change: 1.24 },
  { name: 'DOW', value: '38,996.39', change: 0.32 },
  { name: 'BTC/USD', value: '67,245.00', change: -2.15 },
];

const StatCard = ({
  title,
  value,
  change,
  changePercent,
  icon: Icon,
  iconBg,
}: {
  title: string;
  value: string;
  change?: number;
  changePercent?: number;
  icon: React.ComponentType<{ className?: string }>;
  iconBg: string;
}) => {
  const isPositive = (change ?? 0) >= 0;
  
  return (
    <Card>
      <CardContent className="p-6">
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
      </CardContent>
    </Card>
  );
};

const Dashboard = () => {
  return (
    <Layout title="Dashboard">
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        <StatCard
          title="Portfolio Value"
          value={`$${portfolioStats.totalValue.toLocaleString()}`}
          change={portfolioStats.dailyChange}
          changePercent={portfolioStats.dailyChangePercent}
          icon={DollarSign}
          iconBg="bg-primary-500/20"
        />
        <StatCard
          title="Unrealized P&L"
          value={`${portfolioStats.unrealizedPL >= 0 ? '+' : ''}$${portfolioStats.unrealizedPL.toLocaleString()}`}
          changePercent={portfolioStats.unrealizedPLPercent}
          icon={TrendingUp}
          iconBg="bg-success-500/20"
        />
        <StatCard
          title="Cash Available"
          value={`$${portfolioStats.cashAvailable.toLocaleString()}`}
          icon={PieChart}
          iconBg="bg-secondary-500/20"
        />
        <StatCard
          title="Buying Power"
          value={`$${portfolioStats.buyingPower.toLocaleString()}`}
          icon={Activity}
          iconBg="bg-warning-500/20"
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Top Positions */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <h3 className="text-lg font-semibold text-white">Top Positions</h3>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="border-b border-surface-700">
                  <tr>
                    <th className="text-left text-sm font-medium text-surface-400 p-4">Symbol</th>
                    <th className="text-right text-sm font-medium text-surface-400 p-4">Shares</th>
                    <th className="text-right text-sm font-medium text-surface-400 p-4">Value</th>
                    <th className="text-right text-sm font-medium text-surface-400 p-4">Change</th>
                  </tr>
                </thead>
                <tbody>
                  {topPositions.map((position) => (
                    <tr
                      key={position.symbol}
                      className="border-b border-surface-700/50 hover:bg-surface-800/50 transition-colors"
                    >
                      <td className="p-4">
                        <div>
                          <p className="font-medium text-white">{position.symbol}</p>
                          <p className="text-sm text-surface-400">{position.name}</p>
                        </div>
                      </td>
                      <td className="p-4 text-right text-surface-300">
                        {position.shares}
                      </td>
                      <td className="p-4 text-right font-medium text-white">
                        ${position.value.toLocaleString()}
                      </td>
                      <td className="p-4 text-right">
                        <Badge
                          color={position.change >= 0 ? 'success' : 'danger'}
                        >
                          {position.change >= 0 ? '+' : ''}{position.change}%
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        {/* Market Overview */}
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold text-white">Market Overview</h3>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {marketOverview.map((market) => (
                <div
                  key={market.name}
                  className="flex items-center justify-between p-3 bg-surface-800/50 rounded-lg"
                >
                  <div>
                    <p className="font-medium text-white">{market.name}</p>
                    <p className="text-sm text-surface-400">{market.value}</p>
                  </div>
                  <div
                    className={clsx(
                      'flex items-center gap-1',
                      market.change >= 0 ? 'text-success-400' : 'text-danger-400'
                    )}
                  >
                    {market.change >= 0 ? (
                      <TrendingUp className="w-4 h-4" />
                    ) : (
                      <TrendingDown className="w-4 h-4" />
                    )}
                    <span className="font-medium">
                      {market.change >= 0 ? '+' : ''}{market.change}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Trades */}
      <Card className="mt-6">
        <CardHeader>
          <h3 className="text-lg font-semibold text-white">Recent Trades</h3>
        </CardHeader>
        <CardContent className="p-0">
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
                      <Badge color={trade.type === 'BUY' ? 'success' : 'danger'}>
                        {trade.type}
                      </Badge>
                    </td>
                    <td className="p-4 text-right text-surface-300">{trade.shares}</td>
                    <td className="p-4 text-right font-medium text-white">
                      ${trade.price.toFixed(2)}
                    </td>
                    <td className="p-4 text-right text-surface-400">{trade.time}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </Layout>
  );
};

export default Dashboard;
