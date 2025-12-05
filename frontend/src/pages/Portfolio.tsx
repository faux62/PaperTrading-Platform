/**
 * Portfolio Page
 * 
 * Main portfolio management page with list view, create modal,
 * and portfolio details.
 */
import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout } from '../components/layout';
import { Card, CardContent } from '../components/common';
import { PortfolioCard, CreatePortfolioModal, EditPortfolioModal, PortfolioSummary } from '../components/portfolio';
import { portfolioApi, currencyApi, authApi } from '../services/api';
import { Briefcase, Plus, RefreshCw, AlertCircle } from 'lucide-react';

// Currency symbols
const CURRENCY_SYMBOLS: Record<string, string> = {
  USD: '$', EUR: '€', GBP: '£', JPY: '¥', CHF: 'CHF', CAD: 'C$', AUD: 'A$'
};

const Portfolio = () => {
  const navigate = useNavigate();
  const [portfolios, setPortfolios] = useState<PortfolioSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  
  // Edit modal state
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingPortfolio, setEditingPortfolio] = useState<PortfolioSummary | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);
  
  // Currency conversion state
  const [baseCurrency, setBaseCurrency] = useState<string>('USD');
  const [exchangeRates, setExchangeRates] = useState<Record<string, number>>({});

  // Fetch user's base currency and exchange rates
  const fetchCurrencyData = async () => {
    try {
      const [userData, ratesData] = await Promise.all([
        authApi.getMe(),
        currencyApi.getRates('USD'),
      ]);
      setBaseCurrency(userData.base_currency || 'USD');
      setExchangeRates(ratesData.rates || {});
    } catch (err) {
      console.error('Failed to fetch currency data:', err);
    }
  };

  // Fetch portfolios
  const fetchPortfolios = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [response] = await Promise.all([
        portfolioApi.getAll(),
        fetchCurrencyData(), // Always refresh currency data too
      ]);
      setPortfolios(response.portfolios || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load portfolios');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchPortfolios();
  }, []);

  // Create portfolio
  const handleCreatePortfolio = async (data: {
    name: string;
    description?: string;
    risk_profile: string;
    initial_capital: number;
    currency: string;
  }) => {
    setIsCreating(true);
    setCreateError(null);
    try {
      await portfolioApi.create({
        name: data.name,
        initial_capital: data.initial_capital,
        risk_profile: data.risk_profile,
        currency: data.currency,
      });
      setIsCreateModalOpen(false);
      await fetchPortfolios();
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : 'Failed to create portfolio');
    } finally {
      setIsCreating(false);
    }
  };

  // View portfolio details
  const handleViewPortfolio = (id: number) => {
    navigate(`/portfolio/${id}`);
  };

  // Edit portfolio
  const handleEditPortfolio = (id: number) => {
    const portfolio = portfolios.find(p => p.id === id);
    if (portfolio) {
      setEditingPortfolio(portfolio);
      setEditError(null);
      setIsEditModalOpen(true);
    }
  };

  // Update portfolio
  const handleUpdatePortfolio = async (id: number, data: {
    name: string;
    description?: string;
    risk_profile: string;
  }) => {
    setIsEditing(true);
    setEditError(null);
    try {
      await portfolioApi.update(id, data);
      setIsEditModalOpen(false);
      setEditingPortfolio(null);
      await fetchPortfolios();
    } catch (err) {
      setEditError(err instanceof Error ? err.message : 'Failed to update portfolio');
    } finally {
      setIsEditing(false);
    }
  };

  // Delete portfolio
  const handleDeletePortfolio = async (id: number) => {
    if (!confirm('Are you sure you want to delete this portfolio? This action cannot be undone.')) {
      return;
    }
    try {
      await portfolioApi.delete(id);
      await fetchPortfolios();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete portfolio');
    }
  };

  // Convert amount from one currency to user's base currency
  const convertToBaseCurrency = (amount: number, fromCurrency: string): number => {
    if (fromCurrency === baseCurrency) return amount;
    if (!exchangeRates[fromCurrency] || !exchangeRates[baseCurrency]) return amount;
    
    // Convert via USD: amount / fromRate * toRate
    const amountInUSD = amount / exchangeRates[fromCurrency];
    return amountInUSD * exchangeRates[baseCurrency];
  };

  // Calculate totals converted to user's base currency
  const { totalValue, totalReturn } = useMemo(() => {
    let value = 0;
    let ret = 0;
    
    for (const p of portfolios) {
      value += convertToBaseCurrency(p.total_value, p.currency);
      ret += convertToBaseCurrency(p.total_return, p.currency);
    }
    
    return { totalValue: value, totalReturn: ret };
  }, [portfolios, baseCurrency, exchangeRates]);

  const currencySymbol = CURRENCY_SYMBOLS[baseCurrency] || baseCurrency;

  return (
    <Layout title="Portfolio">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Portfolios</h1>
          <p className="text-surface-400 mt-1">
            Manage your paper trading portfolios
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchPortfolios}
            disabled={isLoading}
            className="p-2 hover:bg-surface-700 rounded-lg transition-colors disabled:opacity-50"
            title="Refresh"
          >
            <RefreshCw className={`w-5 h-5 text-surface-400 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg transition-colors"
          >
            <Plus className="w-5 h-5" />
            New Portfolio
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      {portfolios.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
          <Card>
            <CardContent className="p-4">
              <p className="text-sm text-surface-400">Total Portfolios</p>
              <p className="text-2xl font-bold text-white mt-1">{portfolios.length}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <p className="text-sm text-surface-400">Total Value ({baseCurrency})</p>
              <p className="text-2xl font-bold text-white mt-1">
                {currencySymbol}{totalValue.toLocaleString('en-US', { minimumFractionDigits: 2 })}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <p className="text-sm text-surface-400">Total Return ({baseCurrency})</p>
              <p className={`text-2xl font-bold mt-1 ${totalReturn >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {totalReturn >= 0 ? '+' : ''}{currencySymbol}{Math.abs(totalReturn).toLocaleString('en-US', { minimumFractionDigits: 2 })}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="flex items-center gap-2 p-4 mb-6 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <p>{error}</p>
          <button
            onClick={() => setError(null)}
            className="ml-auto text-sm hover:text-red-300"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Loading State */}
      {isLoading && portfolios.length === 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardContent className="p-4">
                <div className="animate-pulse">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-surface-700 rounded-lg" />
                    <div className="space-y-2 flex-1">
                      <div className="h-4 bg-surface-700 rounded w-3/4" />
                      <div className="h-3 bg-surface-700 rounded w-1/2" />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4 mt-4 pt-4 border-t border-surface-700">
                    <div className="space-y-2">
                      <div className="h-3 bg-surface-700 rounded w-1/2" />
                      <div className="h-5 bg-surface-700 rounded w-3/4" />
                    </div>
                    <div className="space-y-2">
                      <div className="h-3 bg-surface-700 rounded w-1/2" />
                      <div className="h-5 bg-surface-700 rounded w-3/4" />
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Empty State */}
      {!isLoading && portfolios.length === 0 && (
        <Card>
          <CardContent className="p-12 text-center">
            <div className="w-16 h-16 bg-primary-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
              <Briefcase className="w-8 h-8 text-primary-400" />
            </div>
            <h2 className="text-xl font-semibold text-white mb-2">No Portfolios Yet</h2>
            <p className="text-surface-400 mb-6 max-w-md mx-auto">
              Create your first paper trading portfolio to start tracking your investments
              and testing trading strategies risk-free.
            </p>
            <button
              onClick={() => setIsCreateModalOpen(true)}
              className="inline-flex items-center gap-2 px-6 py-3 bg-primary-500 hover:bg-primary-600 text-white rounded-lg transition-colors"
            >
              <Plus className="w-5 h-5" />
              Create Your First Portfolio
            </button>
          </CardContent>
        </Card>
      )}

      {/* Portfolio List */}
      {!isLoading && portfolios.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {portfolios.map((portfolio) => (
            <PortfolioCard
              key={portfolio.id}
              portfolio={portfolio}
              onView={handleViewPortfolio}
              onEdit={handleEditPortfolio}
              onDelete={handleDeletePortfolio}
            />
          ))}
        </div>
      )}

      {/* Create Portfolio Modal */}
      <CreatePortfolioModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSubmit={handleCreatePortfolio}
        isLoading={isCreating}
        error={createError}
      />

      {/* Edit Portfolio Modal */}
      <EditPortfolioModal
        isOpen={isEditModalOpen}
        portfolio={editingPortfolio}
        onClose={() => {
          setIsEditModalOpen(false);
          setEditingPortfolio(null);
        }}
        onSubmit={handleUpdatePortfolio}
        isLoading={isEditing}
        error={editError}
      />
    </Layout>
  );
};

export default Portfolio;
