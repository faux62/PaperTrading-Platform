/**
 * Order Form Component
 * 
 * Form for submitting buy/sell orders with support for
 * Market, Limit, Stop, and Stop-Limit order types.
 * Features user-friendly layered symbol selection.
 * Handles multi-currency conversion for validation.
 */
import { useState, useEffect } from 'react';
import { clsx } from 'clsx';
import {
  TrendingUp,
  TrendingDown,
  AlertCircle,
  CheckCircle,
  Loader2,
  Info,
  RefreshCw
} from 'lucide-react';
import { LayeredSymbolSelector } from './LayeredSymbolSelector';
import { currencyApi } from '../../services/api';

// Currency symbols
const CURRENCY_SYMBOLS: Record<string, string> = {
  USD: '$', EUR: '€', GBP: '£', JPY: '¥', CHF: 'CHF', CAD: 'C$', AUD: 'A$'
};

interface PositionInfo {
  symbol: string;
  quantity: number;
}

interface OrderFormProps {
  portfolioId: number;
  symbol?: string;
  currentPrice?: number;
  availableCash?: number;
  positions?: PositionInfo[];  // All positions to lookup shares by symbol
  currency?: string;
  onSubmit: (order: OrderData) => Promise<void>;
  onCancel?: () => void;
  className?: string;
}

interface OrderData {
  portfolio_id: number;
  symbol: string;
  trade_type: 'buy' | 'sell';
  quantity: number;
  order_type: 'market' | 'limit' | 'stop' | 'stop_limit';
  limit_price?: number;
  stop_price?: number;
  notes?: string;
}

type OrderType = 'market' | 'limit' | 'stop' | 'stop_limit';
type TradeType = 'buy' | 'sell';

const ORDER_TYPES: { value: OrderType; label: string; description: string }[] = [
  { 
    value: 'market', 
    label: 'Market', 
    description: 'Execute immediately at current price'
  },
  { 
    value: 'limit', 
    label: 'Limit', 
    description: 'Execute only at specified price or better'
  },
  { 
    value: 'stop', 
    label: 'Stop', 
    description: 'Trigger market order when price hits stop level'
  },
  { 
    value: 'stop_limit', 
    label: 'Stop-Limit', 
    description: 'Trigger limit order when price hits stop level'
  }
];

export function OrderForm({
  portfolioId,
  symbol: initialSymbol = '',
  currentPrice: initialPrice,
  availableCash = 0,
  positions = [],
  currency = 'USD',
  onSubmit,
  onCancel,
  className
}: OrderFormProps) {
  const portfolioCurrencySymbol = CURRENCY_SYMBOLS[currency] || currency;
  const [tradeType, setTradeType] = useState<TradeType>('buy');
  const [orderType, setOrderType] = useState<OrderType>('market');
  const [symbol, setSymbol] = useState(initialSymbol);
  const [selectedPrice, setSelectedPrice] = useState<number | null>(initialPrice || null);
  const [symbolCurrency, setSymbolCurrency] = useState<string>('USD'); // Currency of the selected stock
  const [exchangeRate, setExchangeRate] = useState<number>(1); // Rate from symbolCurrency to portfolio currency
  const [isLoadingRate, setIsLoadingRate] = useState(false);
  const [quantity, setQuantity] = useState<string>('');
  const [marketPrice, setMarketPrice] = useState<string>('');  // For market orders without live data
  const [limitPrice, setLimitPrice] = useState<string>('');
  const [stopPrice, setStopPrice] = useState<string>('');
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Use selectedPrice or initialPrice
  const currentPrice = selectedPrice || initialPrice;
  
  // Symbol currency symbol for display
  const symbolCurrencySymbol = CURRENCY_SYMBOLS[symbolCurrency] || symbolCurrency;
  
  // Check if currency conversion is needed
  const needsConversion = symbolCurrency !== currency;

  // Calculate available shares for current symbol from positions
  const availableShares = positions.find(
    p => p.symbol.toUpperCase() === symbol.toUpperCase()
  )?.quantity || 0;

  // Fetch exchange rate when symbol currency changes
  useEffect(() => {
    const fetchExchangeRate = async () => {
      if (symbolCurrency === currency) {
        setExchangeRate(1);
        return;
      }
      
      setIsLoadingRate(true);
      try {
        const result = await currencyApi.convert(1, symbolCurrency, currency);
        setExchangeRate(result.rate);
      } catch (err) {
        console.error('Failed to fetch exchange rate:', err);
        // Fallback: keep rate as 1 but show warning
        setExchangeRate(1);
      } finally {
        setIsLoadingRate(false);
      }
    };
    
    if (symbolCurrency && currency) {
      fetchExchangeRate();
    }
  }, [symbolCurrency, currency]);

  // Handle symbol selection from LayeredSymbolSelector
  const handleSymbolSelect = (selectedSymbol: string, price: number | null, _name: string, stockCurrency: string) => {
    setSymbol(selectedSymbol);
    setSelectedPrice(price);
    setSymbolCurrency(stockCurrency);
    if (price) {
      setMarketPrice(price.toString());
    }
    setError(null);
  };

  // Update symbol when prop changes
  useEffect(() => {
    if (initialSymbol) {
      setSymbol(initialSymbol);
    }
  }, [initialSymbol]);

  // Calculate estimated order value in NATIVE currency (stock's currency)
  const estimatedValueNative = (() => {
    const qty = parseFloat(quantity) || 0;
    if (orderType === 'limit' || orderType === 'stop_limit') {
      return qty * (parseFloat(limitPrice) || 0);
    }
    // For market orders, use provided currentPrice or user-entered marketPrice
    const price = currentPrice || parseFloat(marketPrice) || 0;
    return qty * price;
  })();
  
  // Estimated value converted to PORTFOLIO currency for validation
  const estimatedValueInPortfolioCurrency = estimatedValueNative * exchangeRate;

  // Validation
  const validate = (): string | null => {
    if (!symbol.trim()) {
      return 'Symbol is required';
    }
    
    const qty = parseFloat(quantity);
    if (!qty || qty <= 0) {
      return 'Quantity must be greater than 0';
    }
    
    // For market orders without live price, require user to enter price
    if (orderType === 'market' && !currentPrice && !parseFloat(marketPrice)) {
      return 'Price per share is required';
    }
    
    // Validate using CONVERTED value against portfolio cash
    if (tradeType === 'buy' && estimatedValueInPortfolioCurrency > availableCash) {
      const neededStr = needsConversion 
        ? `${symbolCurrencySymbol}${estimatedValueNative.toFixed(2)} (≈${portfolioCurrencySymbol}${estimatedValueInPortfolioCurrency.toFixed(2)})`
        : `${portfolioCurrencySymbol}${estimatedValueInPortfolioCurrency.toFixed(2)}`;
      return `Insufficient funds. Need ${neededStr}, have ${portfolioCurrencySymbol}${availableCash.toFixed(2)}`;
    }
    
    if (tradeType === 'sell' && qty > availableShares) {
      return `Insufficient shares. Want to sell ${qty}, have ${availableShares}`;
    }
    
    if ((orderType === 'limit' || orderType === 'stop_limit') && !parseFloat(limitPrice)) {
      return 'Limit price is required for this order type';
    }
    
    if ((orderType === 'stop' || orderType === 'stop_limit') && !parseFloat(stopPrice)) {
      return 'Stop price is required for this order type';
    }
    
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    console.log('OrderForm handleSubmit called', { 
      symbol, quantity, marketPrice, orderType, tradeType,
      availableCash, portfolioId, 
      estimatedValueNative, estimatedValueInPortfolioCurrency,
      symbolCurrency, portfolioCurrency: currency, exchangeRate
    });
    setError(null);
    setSuccess(false);
    
    const validationError = validate();
    if (validationError) {
      console.log('Validation error:', validationError);
      setError(validationError);
      return;
    }
    
    console.log('Validation passed, submitting...');
    setIsSubmitting(true);
    
    try {
      const orderData: OrderData = {
        portfolio_id: portfolioId,
        symbol: symbol.toUpperCase().trim(),
        trade_type: tradeType,
        quantity: parseFloat(quantity),
        order_type: orderType,
        notes: notes.trim() || undefined
      };
      
      // For market orders, pass the user-entered price as limit_price
      // The backend will use this for execution when no live data
      if (orderType === 'market' && marketPrice) {
        orderData.limit_price = parseFloat(marketPrice);
      }
      
      if (orderType === 'limit' || orderType === 'stop_limit') {
        orderData.limit_price = parseFloat(limitPrice);
      }
      
      if (orderType === 'stop' || orderType === 'stop_limit') {
        orderData.stop_price = parseFloat(stopPrice);
      }
      
      console.log('Calling onSubmit with:', orderData);
      const result = await onSubmit(orderData);
      console.log('onSubmit returned:', result);
      setSuccess(true);
      
      // Reset form after success
      setTimeout(() => {
        setQuantity('');
        setMarketPrice('');
        setLimitPrice('');
        setStopPrice('');
        setNotes('');
        setSuccess(false);
      }, 2000);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit order');
    } finally {
      setIsSubmitting(false);
    }
  };

  const setMaxQuantity = () => {
    if (tradeType === 'buy' && currentPrice && currentPrice > 0) {
      const maxQty = Math.floor(availableCash / currentPrice);
      setQuantity(maxQty.toString());
    } else if (tradeType === 'sell') {
      setQuantity(availableShares.toString());
    }
  };

  return (
    <form onSubmit={handleSubmit} className={clsx('space-y-4', className)}>
      {/* Trade Type Selector */}
      <div className="grid grid-cols-2 gap-2">
        <button
          type="button"
          onClick={() => setTradeType('buy')}
          className={clsx(
            'flex items-center justify-center gap-2 py-3 px-4 rounded-lg font-medium transition-all',
            tradeType === 'buy'
              ? 'bg-green-600 text-white'
              : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
          )}
        >
          <TrendingUp className="w-5 h-5" />
          Buy
        </button>
        <button
          type="button"
          onClick={() => setTradeType('sell')}
          className={clsx(
            'flex items-center justify-center gap-2 py-3 px-4 rounded-lg font-medium transition-all',
            tradeType === 'sell'
              ? 'bg-red-600 text-white'
              : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
          )}
        >
          <TrendingDown className="w-5 h-5" />
          Sell
        </button>
      </div>

      {/* Layered Symbol Selector - User-friendly navigation */}
      <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
          Select Stock
        </label>
        <LayeredSymbolSelector
          onSelect={handleSymbolSelect}
          initialSymbol={symbol}
        />
      </div>

      {/* Order Type Selector */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Order Type
        </label>
        <div className="grid grid-cols-2 gap-2">
          {ORDER_TYPES.map((type) => (
            <button
              key={type.value}
              type="button"
              onClick={() => setOrderType(type.value)}
              className={clsx(
                'py-2 px-3 rounded-lg text-sm font-medium transition-all text-left',
                orderType === type.value
                  ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 ring-2 ring-blue-500'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
              )}
            >
              {type.label}
            </button>
          ))}
        </div>
        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
          {ORDER_TYPES.find(t => t.value === orderType)?.description}
        </p>
      </div>

      {/* Quantity Input */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            Quantity
          </label>
          <button
            type="button"
            onClick={setMaxQuantity}
            className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
          >
            Max
          </button>
        </div>
        <input
          type="number"
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
          placeholder="0"
          min="0"
          step="1"
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg 
                     bg-white dark:bg-gray-700 text-gray-900 dark:text-white
                     focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        {tradeType === 'sell' && (
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            Available: {availableShares} shares
          </p>
        )}
      </div>

      {/* Market Price (for market orders when no live price available) */}
      {orderType === 'market' && !currentPrice && (
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Price per Share ({symbolCurrency})
          </label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-gray-400">
              {symbolCurrencySymbol}
            </span>
            <input
              type="number"
              value={marketPrice}
              onChange={(e) => setMarketPrice(e.target.value)}
              placeholder="0.00"
              min="0"
              step="0.01"
              className="w-full pl-8 pr-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg 
                         bg-white dark:bg-gray-700 text-gray-900 dark:text-white
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            Enter the execution price (no live market data)
          </p>
        </div>
      )}

      {/* Limit Price (for limit and stop-limit orders) */}
      {(orderType === 'limit' || orderType === 'stop_limit') && (
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Limit Price ({symbolCurrency})
          </label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-gray-400">
              {symbolCurrencySymbol}
            </span>
            <input
              type="number"
              value={limitPrice}
              onChange={(e) => setLimitPrice(e.target.value)}
              placeholder="0.00"
              min="0"
              step="0.01"
              className="w-full pl-8 pr-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg 
                         bg-white dark:bg-gray-700 text-gray-900 dark:text-white
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>
      )}

      {/* Stop Price (for stop and stop-limit orders) */}
      {(orderType === 'stop' || orderType === 'stop_limit') && (
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Stop Price ({symbolCurrency})
          </label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-gray-400">
              {symbolCurrencySymbol}
            </span>
            <input
              type="number"
              value={stopPrice}
              onChange={(e) => setStopPrice(e.target.value)}
              placeholder="0.00"
              min="0"
              step="0.01"
              className="w-full pl-8 pr-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg 
                         bg-white dark:bg-gray-700 text-gray-900 dark:text-white
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>
      )}

      {/* Order Summary */}
      <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 space-y-2">
        {/* Exchange Rate Info (when different currencies) */}
        {needsConversion && symbol && (
          <div className="flex justify-between items-center text-xs pb-2 border-b border-gray-200 dark:border-gray-700">
            <span className="text-gray-500 dark:text-gray-400">
              Exchange Rate
            </span>
            <span className="text-gray-600 dark:text-gray-300 flex items-center gap-1">
              {isLoadingRate ? (
                <RefreshCw className="h-3 w-3 animate-spin" />
              ) : (
                <>1 {symbolCurrency} = {exchangeRate.toFixed(4)} {currency}</>
              )}
            </span>
          </div>
        )}
        
        <div className="flex justify-between text-sm">
          <span className="text-gray-600 dark:text-gray-400">Estimated Value</span>
          <div className="text-right">
            {needsConversion && estimatedValueNative > 0 ? (
              <>
                <span className="font-semibold text-gray-900 dark:text-white">
                  {symbolCurrencySymbol}{estimatedValueNative.toFixed(2)}
                </span>
                <span className="text-xs text-gray-500 dark:text-gray-400 block">
                  ≈ {portfolioCurrencySymbol}{estimatedValueInPortfolioCurrency.toFixed(2)} {currency}
                </span>
              </>
            ) : (
              <span className="font-semibold text-gray-900 dark:text-white">
                {portfolioCurrencySymbol}{estimatedValueInPortfolioCurrency.toFixed(2)}
              </span>
            )}
          </div>
        </div>
        {tradeType === 'buy' && (
          <div className="flex justify-between text-sm">
            <span className="text-gray-600 dark:text-gray-400">Available Cash</span>
            <span className={clsx(
              'font-medium',
              estimatedValueInPortfolioCurrency > availableCash ? 'text-red-600' : 'text-green-600'
            )}>
              {portfolioCurrencySymbol}{availableCash.toFixed(2)}
            </span>
          </div>
        )}
      </div>

      {/* Notes (optional) */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Notes (optional)
        </label>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Add notes about this trade..."
          rows={2}
          maxLength={500}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg 
                     bg-white dark:bg-gray-700 text-gray-900 dark:text-white
                     focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
        />
      </div>

      {/* Error Message */}
      {error && (
        <div className="flex items-center gap-2 text-red-600 dark:text-red-400 text-sm bg-red-50 dark:bg-red-900/20 p-3 rounded-lg">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Success Message */}
      {success && (
        <div className="flex items-center gap-2 text-green-600 dark:text-green-400 text-sm bg-green-50 dark:bg-green-900/20 p-3 rounded-lg">
          <CheckCircle className="w-4 h-4 flex-shrink-0" />
          <span>Order submitted successfully!</span>
        </div>
      )}

      {/* Submit Buttons */}
      <div className="flex gap-3">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="flex-1 py-3 px-4 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 
                       rounded-lg font-medium hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
          >
            Cancel
          </button>
        )}
        <button
          type="submit"
          disabled={isSubmitting}
          className={clsx(
            'flex-1 py-3 px-4 rounded-lg font-medium transition-colors flex items-center justify-center gap-2',
            tradeType === 'buy'
              ? 'bg-green-600 hover:bg-green-700 text-white'
              : 'bg-red-600 hover:bg-red-700 text-white',
            isSubmitting && 'opacity-50 cursor-not-allowed'
          )}
        >
          {isSubmitting ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Submitting...
            </>
          ) : (
            <>
              {tradeType === 'buy' ? 'Place Buy Order' : 'Place Sell Order'}
            </>
          )}
        </button>
      </div>

      {/* Info Note */}
      <div className="flex items-start gap-2 text-xs text-gray-500 dark:text-gray-400">
        <Info className="w-4 h-4 flex-shrink-0 mt-0.5" />
        <p>
          This is paper trading. No real money is involved. 
          Market orders execute with simulated slippage.
        </p>
      </div>
    </form>
  );
}

export default OrderForm;
