/**
 * Currency Balances Component (IBKR-style)
 * 
 * Displays multi-currency cash balances for a portfolio
 * with deposit, withdraw, and FX conversion capabilities.
 */
import { useState, useEffect } from 'react';
import { currencyApi } from '../../services/api';
import { 
  Wallet, 
  ArrowRightLeft, 
  Plus, 
  Minus, 
  RefreshCw, 
  ChevronDown,
  ChevronUp,
  History,
  AlertCircle
} from 'lucide-react';

// Currency symbols and flags
const CURRENCY_INFO: Record<string, { symbol: string; flag: string; name: string }> = {
  USD: { symbol: '$', flag: '🇺🇸', name: 'US Dollar' },
  EUR: { symbol: '€', flag: '🇪🇺', name: 'Euro' },
  GBP: { symbol: '£', flag: '🇬🇧', name: 'British Pound' },
  JPY: { symbol: '¥', flag: '🇯🇵', name: 'Japanese Yen' },
  CHF: { symbol: 'CHF', flag: '🇨🇭', name: 'Swiss Franc' },
  CAD: { symbol: 'C$', flag: '🇨🇦', name: 'Canadian Dollar' },
  AUD: { symbol: 'A$', flag: '🇦🇺', name: 'Australian Dollar' },
  HKD: { symbol: 'HK$', flag: '🇭🇰', name: 'Hong Kong Dollar' },
  SGD: { symbol: 'S$', flag: '🇸🇬', name: 'Singapore Dollar' },
  SEK: { symbol: 'kr', flag: '🇸🇪', name: 'Swedish Krona' },
  NOK: { symbol: 'kr', flag: '🇳🇴', name: 'Norwegian Krone' },
  DKK: { symbol: 'kr', flag: '🇩🇰', name: 'Danish Krone' },
  CNY: { symbol: '¥', flag: '🇨🇳', name: 'Chinese Yuan' },
  INR: { symbol: '₹', flag: '🇮🇳', name: 'Indian Rupee' },
};

interface CashBalance {
  id: number;
  currency: string;
  balance: number;
  updated_at: string;
}

interface FxTransaction {
  id: number;
  from_currency: string;
  to_currency: string;
  from_amount: number;
  to_amount: number;
  exchange_rate: number;
  fee: number;
  created_at: string;
}

interface Props {
  portfolioId: number;
  baseCurrency?: string;
  onBalanceChange?: () => void;
}

type ModalType = 'deposit' | 'withdraw' | 'convert' | 'history' | null;

export const CurrencyBalances = ({ portfolioId, baseCurrency: _baseCurrency = 'USD', onBalanceChange }: Props) => {
  // baseCurrency will be used for total conversion display in future
  void _baseCurrency;
  const [balances, setBalances] = useState<CashBalance[]>([]);
  const [fxHistory, setFxHistory] = useState<FxTransaction[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(true);
  
  // Modal state
  const [modalType, setModalType] = useState<ModalType>(null);
  const [selectedCurrency, setSelectedCurrency] = useState<string>('USD');
  const [amount, setAmount] = useState<string>('');
  const [fromCurrency, setFromCurrency] = useState<string>('USD');
  const [toCurrency, setToCurrency] = useState<string>('EUR');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  // Fetch balances
  const fetchBalances = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await currencyApi.getPortfolioBalances(portfolioId);
      setBalances(Array.isArray(data) ? data : data.balances || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load balances');
    } finally {
      setIsLoading(false);
    }
  };

  // Fetch FX history
  const fetchFxHistory = async () => {
    try {
      const data = await currencyApi.getFxHistory(portfolioId, 20);
      setFxHistory(Array.isArray(data) ? data : data.transactions || []);
    } catch (err) {
      console.error('Failed to load FX history:', err);
    }
  };

  useEffect(() => {
    fetchBalances();
  }, [portfolioId]);

  // Handle deposit
  const handleDeposit = async () => {
    if (!amount || parseFloat(amount) <= 0) {
      setModalError('Please enter a valid amount');
      return;
    }
    
    setIsSubmitting(true);
    setModalError(null);
    try {
      await currencyApi.deposit(portfolioId, selectedCurrency, parseFloat(amount));
      await fetchBalances();
      onBalanceChange?.();
      closeModal();
    } catch (err) {
      setModalError(err instanceof Error ? err.message : 'Deposit failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle withdraw
  const handleWithdraw = async () => {
    if (!amount || parseFloat(amount) <= 0) {
      setModalError('Please enter a valid amount');
      return;
    }
    
    setIsSubmitting(true);
    setModalError(null);
    try {
      await currencyApi.withdraw(portfolioId, selectedCurrency, parseFloat(amount));
      await fetchBalances();
      onBalanceChange?.();
      closeModal();
    } catch (err) {
      setModalError(err instanceof Error ? err.message : 'Withdrawal failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle FX conversion
  const handleConvert = async () => {
    if (!amount || parseFloat(amount) <= 0) {
      setModalError('Please enter a valid amount');
      return;
    }
    if (fromCurrency === toCurrency) {
      setModalError('Source and target currencies must be different');
      return;
    }
    
    setIsSubmitting(true);
    setModalError(null);
    try {
      await currencyApi.convertFx(portfolioId, fromCurrency, toCurrency, parseFloat(amount));
      await fetchBalances();
      onBalanceChange?.();
      closeModal();
    } catch (err) {
      setModalError(err instanceof Error ? err.message : 'Conversion failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  const openModal = (type: ModalType, currency?: string) => {
    setModalType(type);
    if (currency) setSelectedCurrency(currency);
    setAmount('');
    setModalError(null);
    if (type === 'history') {
      fetchFxHistory();
    }
  };

  const closeModal = () => {
    setModalType(null);
    setAmount('');
    setModalError(null);
  };

  // Calculate total in base currency (simplified - would need real rates)
  // const totalInBase = balances.reduce((sum, b) => {
  //   // For now, just sum assuming 1:1 (real implementation would use exchange rates)
  //   return sum + b.balance;
  // }, 0);

  const formatCurrency = (amount: number, currency: string) => {
    const info = CURRENCY_INFO[currency] || { symbol: currency };
    return `${info.symbol}${amount.toLocaleString(undefined, { 
      minimumFractionDigits: 2, 
      maximumFractionDigits: 2 
    })}`;
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (isLoading) {
    return (
      <div className="bg-slate-800 rounded-lg p-4 animate-pulse">
        <div className="h-6 bg-slate-700 rounded w-1/3 mb-4"></div>
        <div className="space-y-2">
          <div className="h-12 bg-slate-700 rounded"></div>
          <div className="h-12 bg-slate-700 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-800 rounded-lg overflow-hidden">
      {/* Header */}
      <div 
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-slate-750"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          <Wallet className="h-5 w-5 text-blue-400" />
          <div>
            <h3 className="font-semibold text-white">Cash Balances</h3>
            <p className="text-sm text-slate-400">Multi-currency (IBKR-style)</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={(e) => { e.stopPropagation(); fetchBalances(); }}
            className="p-1.5 hover:bg-slate-700 rounded-lg transition-colors"
            title="Refresh"
          >
            <RefreshCw className="h-4 w-4 text-slate-400" />
          </button>
          {isExpanded ? (
            <ChevronUp className="h-5 w-5 text-slate-400" />
          ) : (
            <ChevronDown className="h-5 w-5 text-slate-400" />
          )}
        </div>
      </div>

      {isExpanded && (
        <div className="px-4 pb-4">
          {error ? (
            <div className="flex items-center gap-2 text-red-400 text-sm p-3 bg-red-500/10 rounded-lg">
              <AlertCircle className="h-4 w-4" />
              {error}
            </div>
          ) : (
            <>
              {/* Currency balances list */}
              <div className="space-y-2 mb-4">
                {balances.length === 0 ? (
                  <div className="text-center py-6 text-slate-400">
                    <Wallet className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p>No cash balances yet</p>
                    <p className="text-sm">Deposit funds to get started</p>
                  </div>
                ) : (
                  balances.map((balance) => {
                    const info = CURRENCY_INFO[balance.currency] || { 
                      symbol: balance.currency, 
                      flag: '🏳️', 
                      name: balance.currency 
                    };
                    return (
                      <div 
                        key={balance.id}
                        className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg hover:bg-slate-700 transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <span className="text-xl">{info.flag}</span>
                          <div>
                            <div className="font-medium text-white">{balance.currency}</div>
                            <div className="text-xs text-slate-400">{info.name}</div>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className={`font-semibold ${balance.balance >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {formatCurrency(balance.balance, balance.currency)}
                          </div>
                          <div className="text-xs text-slate-500">
                            Updated {formatDate(balance.updated_at)}
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>

              {/* Action buttons */}
              <div className="grid grid-cols-4 gap-2">
                <button
                  onClick={() => openModal('deposit')}
                  className="flex flex-col items-center gap-1 p-3 bg-green-500/10 hover:bg-green-500/20 text-green-400 rounded-lg transition-colors"
                >
                  <Plus className="h-5 w-5" />
                  <span className="text-xs">Deposit</span>
                </button>
                <button
                  onClick={() => openModal('withdraw')}
                  className="flex flex-col items-center gap-1 p-3 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-lg transition-colors"
                >
                  <Minus className="h-5 w-5" />
                  <span className="text-xs">Withdraw</span>
                </button>
                <button
                  onClick={() => openModal('convert')}
                  className="flex flex-col items-center gap-1 p-3 bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 rounded-lg transition-colors"
                >
                  <ArrowRightLeft className="h-5 w-5" />
                  <span className="text-xs">Convert</span>
                </button>
                <button
                  onClick={() => openModal('history')}
                  className="flex flex-col items-center gap-1 p-3 bg-slate-600/50 hover:bg-slate-600 text-slate-300 rounded-lg transition-colors"
                >
                  <History className="h-5 w-5" />
                  <span className="text-xs">History</span>
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {/* Modals */}
      {modalType && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-800 rounded-xl w-full max-w-md shadow-xl">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 border-b border-slate-700">
              <h3 className="text-lg font-semibold text-white">
                {modalType === 'deposit' && '💰 Deposit Funds'}
                {modalType === 'withdraw' && '📤 Withdraw Funds'}
                {modalType === 'convert' && '💱 Currency Conversion'}
                {modalType === 'history' && '📜 FX Transaction History'}
              </h3>
              <button
                onClick={closeModal}
                className="p-1 hover:bg-slate-700 rounded-lg text-slate-400"
              >
                ✕
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-4">
              {modalError && (
                <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm flex items-center gap-2">
                  <AlertCircle className="h-4 w-4" />
                  {modalError}
                </div>
              )}

              {/* Deposit / Withdraw Modal */}
              {(modalType === 'deposit' || modalType === 'withdraw') && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Currency
                    </label>
                    <select
                      value={selectedCurrency}
                      onChange={(e) => setSelectedCurrency(e.target.value)}
                      className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-white focus:ring-2 focus:ring-blue-500"
                    >
                      {Object.entries(CURRENCY_INFO).map(([code, info]) => (
                        <option key={code} value={code}>
                          {info.flag} {code} - {info.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Amount
                    </label>
                    <div className="relative">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
                        {CURRENCY_INFO[selectedCurrency]?.symbol || selectedCurrency}
                      </span>
                      <input
                        type="number"
                        value={amount}
                        onChange={(e) => setAmount(e.target.value)}
                        placeholder="0.00"
                        min="0"
                        step="0.01"
                        className="w-full bg-slate-700 border border-slate-600 rounded-lg pl-10 pr-3 py-2 text-white focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </div>
                  <button
                    onClick={modalType === 'deposit' ? handleDeposit : handleWithdraw}
                    disabled={isSubmitting || !amount}
                    className={`w-full py-3 rounded-lg font-medium transition-colors ${
                      modalType === 'deposit'
                        ? 'bg-green-600 hover:bg-green-500 text-white'
                        : 'bg-red-600 hover:bg-red-500 text-white'
                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                  >
                    {isSubmitting ? 'Processing...' : modalType === 'deposit' ? 'Deposit' : 'Withdraw'}
                  </button>
                </div>
              )}

              {/* Convert Modal */}
              {modalType === 'convert' && (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-2">
                        From
                      </label>
                      <select
                        value={fromCurrency}
                        onChange={(e) => setFromCurrency(e.target.value)}
                        className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-white focus:ring-2 focus:ring-blue-500"
                      >
                        {Object.entries(CURRENCY_INFO).map(([code, info]) => (
                          <option key={code} value={code}>
                            {info.flag} {code}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-2">
                        To
                      </label>
                      <select
                        value={toCurrency}
                        onChange={(e) => setToCurrency(e.target.value)}
                        className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-white focus:ring-2 focus:ring-blue-500"
                      >
                        {Object.entries(CURRENCY_INFO).map(([code, info]) => (
                          <option key={code} value={code}>
                            {info.flag} {code}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Amount to convert
                    </label>
                    <div className="relative">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
                        {CURRENCY_INFO[fromCurrency]?.symbol || fromCurrency}
                      </span>
                      <input
                        type="number"
                        value={amount}
                        onChange={(e) => setAmount(e.target.value)}
                        placeholder="0.00"
                        min="0"
                        step="0.01"
                        className="w-full bg-slate-700 border border-slate-600 rounded-lg pl-10 pr-3 py-2 text-white focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </div>
                  <div className="p-3 bg-slate-700/50 rounded-lg text-center">
                    <ArrowRightLeft className="h-5 w-5 mx-auto text-blue-400 mb-1" />
                    <p className="text-sm text-slate-400">
                      Exchange rate will be fetched at execution
                    </p>
                  </div>
                  <button
                    onClick={handleConvert}
                    disabled={isSubmitting || !amount || fromCurrency === toCurrency}
                    className="w-full py-3 rounded-lg font-medium bg-blue-600 hover:bg-blue-500 text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isSubmitting ? 'Converting...' : 'Convert Currency'}
                  </button>
                </div>
              )}

              {/* History Modal */}
              {modalType === 'history' && (
                <div className="max-h-80 overflow-y-auto">
                  {fxHistory.length === 0 ? (
                    <div className="text-center py-8 text-slate-400">
                      <History className="h-8 w-8 mx-auto mb-2 opacity-50" />
                      <p>No FX transactions yet</p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {fxHistory.map((tx) => (
                        <div 
                          key={tx.id}
                          className="p-3 bg-slate-700/50 rounded-lg"
                        >
                          <div className="flex items-center justify-between mb-1">
                            <div className="flex items-center gap-2">
                              <span>{CURRENCY_INFO[tx.from_currency]?.flag || '🏳️'}</span>
                              <span className="text-white font-medium">
                                {formatCurrency(tx.from_amount, tx.from_currency)}
                              </span>
                              <ArrowRightLeft className="h-4 w-4 text-slate-500" />
                              <span>{CURRENCY_INFO[tx.to_currency]?.flag || '🏳️'}</span>
                              <span className="text-green-400 font-medium">
                                {formatCurrency(tx.to_amount, tx.to_currency)}
                              </span>
                            </div>
                          </div>
                          <div className="flex justify-between text-xs text-slate-400">
                            <span>Rate: {tx.exchange_rate.toFixed(4)}</span>
                            <span>{formatDate(tx.created_at)}</span>
                          </div>
                          {tx.fee > 0 && (
                            <div className="text-xs text-slate-500">
                              Fee: {formatCurrency(tx.fee, tx.from_currency)}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CurrencyBalances;
