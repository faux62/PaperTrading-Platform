/**
 * Market Store - Zustand store for real-time market data
 */
import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';
import type { MarketQuote } from '../hooks/useWebSocket';

export interface MarketState {
  // Quotes indexed by symbol
  quotes: Record<string, MarketQuote>;
  
  // Watchlist symbols
  watchlist: string[];
  
  // Connection status
  isConnected: boolean;
  
  // Last update timestamp
  lastUpdate: number | null;
  
  // Actions
  updateQuote: (quote: MarketQuote) => void;
  updateQuotes: (quotes: MarketQuote[]) => void;
  setConnected: (connected: boolean) => void;
  addToWatchlist: (symbol: string) => void;
  removeFromWatchlist: (symbol: string) => void;
  setWatchlist: (symbols: string[]) => void;
  clearQuotes: () => void;
  getQuote: (symbol: string) => MarketQuote | undefined;
}

export const useMarketStore = create<MarketState>()(
  subscribeWithSelector((set, get) => ({
    quotes: {},
    watchlist: [],
    isConnected: false,
    lastUpdate: null,

    updateQuote: (quote: MarketQuote) => {
      set((state) => ({
        quotes: {
          ...state.quotes,
          [quote.symbol]: quote,
        },
        lastUpdate: Date.now(),
      }));
    },

    updateQuotes: (quotes: MarketQuote[]) => {
      set((state) => {
        const newQuotes = { ...state.quotes };
        quotes.forEach((quote) => {
          newQuotes[quote.symbol] = quote;
        });
        return {
          quotes: newQuotes,
          lastUpdate: Date.now(),
        };
      });
    },

    setConnected: (connected: boolean) => {
      set({ isConnected: connected });
    },

    addToWatchlist: (symbol: string) => {
      set((state) => ({
        watchlist: state.watchlist.includes(symbol)
          ? state.watchlist
          : [...state.watchlist, symbol],
      }));
    },

    removeFromWatchlist: (symbol: string) => {
      set((state) => ({
        watchlist: state.watchlist.filter((s) => s !== symbol),
      }));
    },

    setWatchlist: (symbols: string[]) => {
      set({ watchlist: symbols });
    },

    clearQuotes: () => {
      set({ quotes: {}, lastUpdate: null });
    },

    getQuote: (symbol: string) => {
      return get().quotes[symbol];
    },
  }))
);

// Selectors
export const selectQuote = (symbol: string) => (state: MarketState) => 
  state.quotes[symbol];

export const selectWatchlistQuotes = (state: MarketState) =>
  state.watchlist.map((symbol) => state.quotes[symbol]).filter(Boolean);

export const selectIsConnected = (state: MarketState) => state.isConnected;

export const selectWatchlist = (state: MarketState) => state.watchlist;

// Utility function to format price
export const formatPrice = (price: number, decimals = 2): string => {
  return price.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
};

// Utility function to format change percent
export const formatChangePercent = (percent: number): string => {
  const sign = percent >= 0 ? '+' : '';
  return `${sign}${percent.toFixed(2)}%`;
};

// Utility function to get change color
export const getChangeColor = (change: number): string => {
  if (change > 0) return 'text-green-500';
  if (change < 0) return 'text-red-500';
  return 'text-gray-500';
};
