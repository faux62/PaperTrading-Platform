/**
 * Hook for FX Rate WebSocket
 * 
 * Provides real-time FX rate updates to React components.
 * Automatically connects/disconnects with component lifecycle.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { 
  fxWebSocket, 
  FXRates, 
  connectFXWebSocket
} from '../services/fxWebSocket';

interface UseFXRatesResult {
  rates: FXRates | null;
  timestamp: string | null;
  isConnected: boolean;
  getRate: (fromCurrency: string, toCurrency: string) => number;
  convert: (amount: number, fromCurrency: string, toCurrency: string) => number;
  refreshRates: () => void;
}

/**
 * Hook to subscribe to FX rate updates
 * 
 * @param autoConnect - Whether to auto-connect on mount (default: true)
 * @returns FX rates and utility functions
 */
export function useFXRates(autoConnect: boolean = true): UseFXRatesResult {
  const [rates, setRates] = useState<FXRates | null>(fxWebSocket.getCurrentRates());
  const [timestamp, setTimestamp] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;

    if (autoConnect) {
      connectFXWebSocket();
      setIsConnected(true);
    }

    // Subscribe to rate updates
    const unsubscribe = fxWebSocket.subscribe((newRates, newTimestamp) => {
      if (mountedRef.current) {
        setRates(newRates);
        setTimestamp(newTimestamp);
      }
    });

    return () => {
      mountedRef.current = false;
      unsubscribe();
      // Don't disconnect on unmount - other components may be using it
    };
  }, [autoConnect]);

  /**
   * Get exchange rate between two currencies
   */
  const getRate = useCallback((fromCurrency: string, toCurrency: string): number => {
    if (!rates) return 1;
    if (fromCurrency === toCurrency) return 1;

    const fromRate = rates[fromCurrency] || 1;
    const toRate = rates[toCurrency] || 1;

    return toRate / fromRate;
  }, [rates]);

  /**
   * Convert amount between currencies
   */
  const convert = useCallback((
    amount: number, 
    fromCurrency: string, 
    toCurrency: string
  ): number => {
    const rate = getRate(fromCurrency, toCurrency);
    return amount * rate;
  }, [getRate]);

  /**
   * Request fresh rates from server
   */
  const refreshRates = useCallback(() => {
    fxWebSocket.requestRates();
  }, []);

  return {
    rates,
    timestamp,
    isConnected,
    getRate,
    convert,
    refreshRates,
  };
}

/**
 * Hook for computing position values with real-time FX rates
 * 
 * @param positions - Array of positions with native currency
 * @param portfolioCurrency - Portfolio's base currency
 * @returns Positions with computed values
 */
export interface PositionWithFX {
  symbol: string;
  quantity: number;
  avg_cost: number;  // Native currency
  avg_cost_portfolio: number;  // Portfolio currency
  current_price: number;  // Native currency
  native_currency: string;
  // Computed
  market_value: number;  // Portfolio currency
  unrealized_pnl: number;  // Portfolio currency
  unrealized_pnl_pct: number;
}

export function usePositionsWithFX(
  positions: any[],
  portfolioCurrency: string = 'EUR'
): PositionWithFX[] {
  const { rates, getRate } = useFXRates();
  const [computed, setComputed] = useState<PositionWithFX[]>([]);

  useEffect(() => {
    if (!positions || positions.length === 0) {
      setComputed([]);
      return;
    }

    const computedPositions = positions.map((pos) => {
      const nativeCurrency = pos.native_currency || 'USD';
      const fxRate = getRate(nativeCurrency, portfolioCurrency);
      
      const currentPrice = pos.current_price || pos.avg_cost || 0;
      const avgCostPortfolio = pos.avg_cost_portfolio || (pos.avg_cost * fxRate);
      
      // Market value in portfolio currency
      const marketValue = pos.quantity * currentPrice * fxRate;
      
      // Cost basis in portfolio currency
      const costBasis = pos.quantity * avgCostPortfolio;
      
      // P&L in portfolio currency
      const unrealizedPnl = marketValue - costBasis;
      
      // P&L percentage (based on native prices)
      const unrealizedPnlPct = pos.avg_cost > 0 
        ? ((currentPrice - pos.avg_cost) / pos.avg_cost) * 100
        : 0;

      return {
        symbol: pos.symbol,
        quantity: pos.quantity,
        avg_cost: pos.avg_cost,
        avg_cost_portfolio: avgCostPortfolio,
        current_price: currentPrice,
        native_currency: nativeCurrency,
        market_value: marketValue,
        unrealized_pnl: unrealizedPnl,
        unrealized_pnl_pct: unrealizedPnlPct,
      };
    });

    setComputed(computedPositions);
  }, [positions, portfolioCurrency, rates, getRate]);

  return computed;
}

export default useFXRates;
