/**
 * Order Form Component
 * 
 * Form for submitting buy/sell orders with support for
 * Market, Limit, Stop, and Stop-Limit order types.
 */
import { useState, useEffect } from 'react';
import { clsx } from 'clsx';
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  AlertCircle,
  CheckCircle,
  Loader2,
  Info
} from 'lucide-react';

interface OrderFormProps {
  portfolioId: number;
  symbol?: string;
  currentPrice?: number;
  availableCash?: number;
  availableShares?: number;
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
  currentPrice,
  availableCash = 0,
  availableShares = 0,
  onSubmit,
  onCancel,
  className
}: OrderFormProps) {
  const [tradeType, setTradeType] = useState<TradeType>('buy');
  const [orderType, setOrderType] = useState<OrderType>('market');
  const [symbol, setSymbol] = useState(initialSymbol);
  const [quantity, setQuantity] = useState<string>('');
  const [limitPrice, setLimitPrice] = useState<string>('');
  const [stopPrice, setStopPrice] = useState<string>('');
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Update symbol when prop changes
  useEffect(() => {
    if (initialSymbol) {
      setSymbol(initialSymbol);
    }
  }, [initialSymbol]);

  // Calculate estimated order value
  const estimatedValue = (() => {
    const qty = parseFloat(quantity) || 0;
    if (orderType === 'limit' || orderType === 'stop_limit') {
      return qty * (parseFloat(limitPrice) || 0);
    }
    return qty * (currentPrice || 0);
  })();

  // Validation
  const validate = (): string | null => {
    if (!symbol.trim()) {
      return 'Symbol is required';
    }
    
    const qty = parseFloat(quantity);
    if (!qty || qty <= 0) {
      return 'Quantity must be greater than 0';
    }
    
    if (tradeType === 'buy' && estimatedValue > availableCash) {
      return `Insufficient funds. Need $${estimatedValue.toFixed(2)}, have $${availableCash.toFixed(2)}`;
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
    setError(null);
    setSuccess(false);
    
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }
    
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
      
      if (orderType === 'limit' || orderType === 'stop_limit') {
        orderData.limit_price = parseFloat(limitPrice);
      }
      
      if (orderType === 'stop' || orderType === 'stop_limit') {
        orderData.stop_price = parseFloat(stopPrice);
      }
      
      await onSubmit(orderData);
      setSuccess(true);
      
      // Reset form after success
      setTimeout(() => {
        setQuantity('');
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

      {/* Symbol Input */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Symbol
        </label>
        <input
          type="text"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value.toUpperCase())}
          placeholder="AAPL"
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg 
                     bg-white dark:bg-gray-700 text-gray-900 dark:text-white
                     focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

      {/* Current Price Display */}
      {currentPrice && (
        <div className="flex items-center justify-between text-sm bg-gray-50 dark:bg-gray-800 p-3 rounded-lg">
          <span className="text-gray-600 dark:text-gray-400">Current Price</span>
          <span className="font-semibold text-gray-900 dark:text-white">
            ${currentPrice.toFixed(2)}
          </span>
        </div>
      )}

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

      {/* Limit Price (for limit and stop-limit orders) */}
      {(orderType === 'limit' || orderType === 'stop_limit') && (
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Limit Price
          </label>
          <div className="relative">
            <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
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
            Stop Price
          </label>
          <div className="relative">
            <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
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
        <div className="flex justify-between text-sm">
          <span className="text-gray-600 dark:text-gray-400">Estimated Value</span>
          <span className="font-semibold text-gray-900 dark:text-white">
            ${estimatedValue.toFixed(2)}
          </span>
        </div>
        {tradeType === 'buy' && (
          <div className="flex justify-between text-sm">
            <span className="text-gray-600 dark:text-gray-400">Available Cash</span>
            <span className={clsx(
              'font-medium',
              estimatedValue > availableCash ? 'text-red-600' : 'text-green-600'
            )}>
              ${availableCash.toFixed(2)}
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
