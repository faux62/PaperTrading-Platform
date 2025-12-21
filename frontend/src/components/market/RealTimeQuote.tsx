/**
 * Real-Time Quote Component
 * Displays live stock quote with price changes
 */
import { useEffect, useState } from 'react';
import { cn } from '../../utils/cn';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { MarketQuote } from '../../hooks/useWebSocket';

interface RealTimeQuoteProps {
  symbol: string;
  quote?: MarketQuote | null;
  compact?: boolean;
  showVolume?: boolean;
  onClick?: () => void;
}

export function RealTimeQuote({
  symbol,
  quote,
  compact = false,
  showVolume = true,
  onClick,
}: RealTimeQuoteProps) {
  const [flash, setFlash] = useState<'up' | 'down' | null>(null);
  const [prevPrice, setPrevPrice] = useState<number | null>(null);

  // Flash animation on price change
  useEffect(() => {
    if (quote && prevPrice !== null && quote.price !== prevPrice) {
      setFlash(quote.price > prevPrice ? 'up' : 'down');
      const timer = setTimeout(() => setFlash(null), 500);
      return () => clearTimeout(timer);
    }
    if (quote) {
      setPrevPrice(quote.price);
    }
  }, [quote?.price, prevPrice]);

  // Get currency info based on stock ticker suffix
  const getCurrencyInfo = (sym: string): { code: string; decimals: number; prefix: string } => {
    if (!sym) return { code: 'USD', decimals: 2, prefix: '$' };
    
    const upperSymbol = sym.toUpperCase();
    
    // London Stock Exchange - prices in GBX (pence)
    if (upperSymbol.endsWith('.L')) {
      return { code: 'GBX', decimals: 2, prefix: 'GBX ' };
    }
    // Hong Kong Stock Exchange
    if (upperSymbol.endsWith('.HK')) {
      return { code: 'HKD', decimals: 2, prefix: 'HK$' };
    }
    // Tokyo Stock Exchange
    if (upperSymbol.endsWith('.T')) {
      return { code: 'JPY', decimals: 0, prefix: '¥' };
    }
    // Euronext exchanges
    if (upperSymbol.endsWith('.MI') || upperSymbol.endsWith('.PA') || 
        upperSymbol.endsWith('.AS') || upperSymbol.endsWith('.BR')) {
      return { code: 'EUR', decimals: 2, prefix: '€' };
    }
    // German exchanges
    if (upperSymbol.endsWith('.DE') || upperSymbol.endsWith('.F')) {
      return { code: 'EUR', decimals: 2, prefix: '€' };
    }
    // Swiss Exchange
    if (upperSymbol.endsWith('.SW')) {
      return { code: 'CHF', decimals: 2, prefix: 'CHF ' };
    }
    // Toronto Stock Exchange
    if (upperSymbol.endsWith('.TO')) {
      return { code: 'CAD', decimals: 2, prefix: 'C$' };
    }
    // Australian Stock Exchange
    if (upperSymbol.endsWith('.AX')) {
      return { code: 'AUD', decimals: 2, prefix: 'A$' };
    }
    // Singapore Exchange
    if (upperSymbol.endsWith('.SI')) {
      return { code: 'SGD', decimals: 2, prefix: 'S$' };
    }
    // India NSE/BSE
    if (upperSymbol.endsWith('.NS') || upperSymbol.endsWith('.BO')) {
      return { code: 'INR', decimals: 2, prefix: '₹' };
    }
    // Default US market
    return { code: 'USD', decimals: 2, prefix: '$' };
  };

  const currencyInfo = getCurrencyInfo(symbol);

  const formatPrice = (price: number) => {
    const formatted = price.toFixed(currencyInfo.decimals);
    return `${currencyInfo.prefix}${formatted}`;
  };

  const formatVolume = (volume: number) => {
    if (volume >= 1_000_000_000) {
      return `${(volume / 1_000_000_000).toFixed(1)}B`;
    }
    if (volume >= 1_000_000) {
      return `${(volume / 1_000_000).toFixed(1)}M`;
    }
    if (volume >= 1_000) {
      return `${(volume / 1_000).toFixed(1)}K`;
    }
    return volume.toString();
  };

  const formatPercent = (percent: number) => {
    const sign = percent >= 0 ? '+' : '';
    return `${sign}${percent.toFixed(2)}%`;
  };

  const isPositive = quote && quote.changePercent >= 0;
  const isNegative = quote && quote.changePercent < 0;

  if (!quote) {
    return (
      <div
        className={cn(
          'flex items-center justify-between p-3 rounded-lg border bg-card animate-pulse',
          onClick && 'cursor-pointer hover:bg-accent/50'
        )}
        onClick={onClick}
      >
        <div className="flex items-center gap-3">
          <span className="font-semibold text-base">{symbol}</span>
          <div className="h-4 w-16 bg-muted rounded" />
        </div>
        <div className="h-4 w-12 bg-muted rounded" />
      </div>
    );
  }

  if (compact) {
    return (
      <div
        className={cn(
          'flex items-center justify-between py-2 px-3 rounded-md transition-colors',
          flash === 'up' && 'bg-green-500/10',
          flash === 'down' && 'bg-red-500/10',
          onClick && 'cursor-pointer hover:bg-accent/50'
        )}
        onClick={onClick}
      >
        <span className="font-medium text-sm">{symbol}</span>
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm">{formatPrice(quote.price)}</span>
          <span
            className={cn(
              'text-xs font-medium',
              isPositive && 'text-green-500',
              isNegative && 'text-red-500'
            )}
          >
            {formatPercent(quote.changePercent)}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'flex items-center justify-between p-4 rounded-lg border bg-card transition-all',
        flash === 'up' && 'bg-green-500/10 border-green-500/30',
        flash === 'down' && 'bg-red-500/10 border-red-500/30',
        onClick && 'cursor-pointer hover:border-primary/50 hover:shadow-sm'
      )}
      onClick={onClick}
    >
      <div className="flex items-center gap-4">
        <div>
          <h3 className="font-semibold text-lg">{symbol}</h3>
          {showVolume && (
            <span className="text-xs text-muted-foreground">
              Vol: {formatVolume(quote.volume)}
            </span>
          )}
        </div>
      </div>

      <div className="flex flex-col items-end">
        <span
          className={cn(
            'font-mono text-lg font-semibold',
            flash === 'up' && 'text-green-500',
            flash === 'down' && 'text-red-500'
          )}
        >
          {formatPrice(quote.price)}
        </span>
        
        <div className="flex items-center gap-1">
          {isPositive && <TrendingUp className="h-3 w-3 text-green-500" />}
          {isNegative && <TrendingDown className="h-3 w-3 text-red-500" />}
          {!isPositive && !isNegative && <Minus className="h-3 w-3 text-muted-foreground" />}
          
          <span
            className={cn(
              'text-sm font-medium',
              isPositive && 'text-green-500',
              isNegative && 'text-red-500',
              !isPositive && !isNegative && 'text-muted-foreground'
            )}
          >
            {formatPrice(Math.abs(quote.change))} ({formatPercent(quote.changePercent)})
          </span>
        </div>

        {quote.bid && quote.ask && (
          <span className="text-xs text-muted-foreground mt-1">
            Bid: {formatPrice(quote.bid)} / Ask: {formatPrice(quote.ask)}
          </span>
        )}
      </div>
    </div>
  );
}

export default RealTimeQuote;
