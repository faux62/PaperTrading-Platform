/**
 * PaperTrading Platform - API Service
 * Axios instance with interceptors for auth and error handling
 */
import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import type { ApiError } from '../types';
import { tokenStorage } from './tokenStorage';

// API Base URL from environment
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// Create Axios instance
const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - Add auth token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = tokenStorage.getAccessToken();
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor - Handle errors and token refresh
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiError>) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // Skip redirect for login/register endpoints - they handle their own 401s
    const isAuthEndpoint = originalRequest.url?.includes('/auth/login') || 
                          originalRequest.url?.includes('/auth/register');

    // Handle 401 - Try to refresh token (but not for auth endpoints)
    if (error.response?.status === 401 && !originalRequest._retry && !isAuthEndpoint) {
      originalRequest._retry = true;

      const refreshToken = tokenStorage.getRefreshToken();
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });

          const { access_token, refresh_token } = response.data;
          tokenStorage.setTokens(access_token, refresh_token);

          // Retry original request with new token
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${access_token}`;
          }
          return api(originalRequest);
        } catch {
          // Refresh failed - clear tokens and redirect (only if not on login page)
          tokenStorage.clearTokens();
          if (!window.location.pathname.includes('/login')) {
            window.location.href = '/login';
          }
          return Promise.reject(error);
        }
      } else if (!window.location.pathname.includes('/login')) {
        // No refresh token - redirect to login (only if not already there)
        tokenStorage.clearTokens();
        window.location.href = '/login';
      }
    }

    // Format error message
    let errorMessage = 'An unexpected error occurred';
    if (error.response?.data?.detail) {
      if (typeof error.response.data.detail === 'string') {
        errorMessage = error.response.data.detail;
      } else if (Array.isArray(error.response.data.detail)) {
        errorMessage = error.response.data.detail.map((e) => e.msg).join(', ');
      }
    } else if (error.message) {
      errorMessage = error.message;
    }

    return Promise.reject(new Error(errorMessage));
  }
);

// ============================================
// Auth API
// ============================================
export const authApi = {
  login: async (emailOrUsername: string, password: string) => {
    const response = await api.post('/auth/login/json', { email_or_username: emailOrUsername, password });
    return response.data;
  },

  register: async (data: { email: string; username: string; password: string; full_name?: string }) => {
    const response = await api.post('/auth/register', data);
    return response.data;
  },

  logout: async () => {
    const response = await api.post('/auth/logout');
    return response.data;
  },

  logoutAll: async () => {
    const response = await api.post('/auth/logout/all');
    return response.data;
  },

  getMe: async () => {
    const response = await api.get('/auth/me');
    return response.data;
  },

  updateMe: async (data: { base_currency?: string; full_name?: string }) => {
    const response = await api.patch('/auth/me', data);
    return response.data;
  },

  changePassword: async (currentPassword: string, newPassword: string) => {
    const response = await api.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
    return response.data;
  },

  getSessions: async () => {
    const response = await api.get('/auth/sessions');
    return response.data;
  },

  revokeSession: async (sessionId: string) => {
    const response = await api.delete(`/auth/sessions/${sessionId}`);
    return response.data;
  },
};

// ============================================
// Portfolio API
// ============================================
export const portfolioApi = {
  getAll: async () => {
    const response = await api.get('/portfolios/');
    return response.data.portfolios || response.data || [];
  },

  getById: async (id: number) => {
    const response = await api.get(`/portfolios/${id}`);
    return response.data;
  },

  create: async (data: { 
    name: string; 
    description?: string;
    initial_capital: number; 
    risk_profile: string; 
    currency?: string;
    strategy_period_weeks?: number;
    is_active?: boolean;
  }) => {
    const response = await api.post('/portfolios/', data);
    return response.data;
  },

  update: async (id: number, data: Partial<{ 
    name: string; 
    description: string;
    risk_profile: string;
    strategy_period_weeks: number;
    is_active: boolean;
  }>) => {
    const response = await api.put(`/portfolios/${id}`, data);
    return response.data;
  },

  delete: async (id: number) => {
    const response = await api.delete(`/portfolios/${id}`);
    return response.data;
  },

  getPositions: async (portfolioId: number) => {
    const response = await api.get(`/positions/portfolio/${portfolioId}`);
    return response.data.positions || [];
  },
};

// ============================================
// Trading API
// ============================================
export const tradingApi = {
  createOrder: async (data: {
    portfolio_id: number;
    symbol: string;
    trade_type: 'buy' | 'sell';
    order_type: 'market' | 'limit' | 'stop' | 'stop_limit';
    quantity: number;
    limit_price?: number;
    stop_price?: number;
    notes?: string;
  }) => {
    const response = await api.post('/trades/orders', data);
    return response.data;
  },

  submitOrder: async (data: {
    portfolio_id: number;
    symbol: string;
    side: 'buy' | 'sell';
    order_type: string;
    quantity: number;
    limit_price?: number;
    stop_price?: number;
  }) => {
    const response = await api.post('/trades/orders', data);
    return response.data;
  },

  getOrders: async (portfolioId: number) => {
    const response = await api.get(`/trades/orders`, { params: { portfolio_id: portfolioId } });
    return response.data;
  },

  cancelOrder: async (orderId: number) => {
    const response = await api.delete(`/trades/orders/${orderId}`);
    return response.data;
  },

  getTradeHistory: async (portfolioId: number, filters?: { symbol?: string; start_date?: string; end_date?: string }) => {
    const params: any = {};
    if (filters?.symbol) params.symbol = filters.symbol;
    if (filters?.start_date) params.start_date = filters.start_date;
    if (filters?.end_date) params.end_date = filters.end_date;
    const response = await api.get(`/trades/history/${portfolioId}`, { params });
    return Array.isArray(response.data) ? response.data : [];
  },

  getTrades: async (portfolioId: number, status?: string) => {
    const params: any = { portfolio_id: portfolioId };
    if (status) params.status = status;
    const response = await api.get('/trades/', { params });
    return response.data;
  },

  getPnL: async (portfolioId: number, timeFrame: string = 'all_time') => {
    const response = await api.get(`/trades/pnl/${portfolioId}`, { params: { time_frame: timeFrame } });
    return response.data;
  },

  getTradeSummary: async (portfolioId: number, days: number = 30) => {
    const response = await api.get(`/trades/summary/${portfolioId}`, { params: { days } });
    return response.data;
  },
};

// ============================================
// Market Data API
// ============================================
export const marketApi = {
  getQuote: async (symbol: string) => {
    const response = await api.get(`/market/quote/${symbol}`);
    return response.data;
  },

  getQuotes: async (symbols: string[]) => {
    const response = await api.get('/market/quotes', { params: { symbols: symbols.join(',') } });
    return response.data;
  },

  // Public endpoint - no auth required
  getIndices: async () => {
    const response = await api.get('/market/indices');
    return response.data;
  },

  getHistorical: async (symbol: string, period: string = '1M') => {
    const response = await api.get(`/market/history/${symbol}`, { params: { period } });
    return response.data;
  },

  search: async (query: string) => {
    const response = await api.get('/market/search', { params: { query } });
    return response.data;
  },

  getMarketHours: async () => {
    const response = await api.get('/market/market-hours');
    return response.data;
  },

  // Market Movers endpoints
  getTopGainers: async (limit: number = 10) => {
    const response = await api.get('/market/movers/gainers', { params: { limit } });
    return response.data;
  },

  getTopLosers: async (limit: number = 10) => {
    const response = await api.get('/market/movers/losers', { params: { limit } });
    return response.data;
  },

  getMostActive: async (limit: number = 10) => {
    const response = await api.get('/market/movers/most-active', { params: { limit } });
    return response.data;
  },

  getTrending: async (limit: number = 10) => {
    const response = await api.get('/market/movers/trending', { params: { limit } });
    return response.data;
  },
};

// ============================================
// Watchlist API
// ============================================
export const watchlistApi = {
  getAll: async () => {
    const response = await api.get('/watchlists');
    return response.data;
  },

  create: async (name: string) => {
    const response = await api.post('/watchlists', { name });
    return response.data;
  },

  addSymbol: async (watchlistId: number, symbol: string) => {
    const response = await api.post(`/watchlists/${watchlistId}/symbols`, { symbol });
    return response.data;
  },

  removeSymbol: async (watchlistId: number, symbol: string) => {
    const response = await api.delete(`/watchlists/${watchlistId}/symbols/${symbol}`);
    return response.data;
  },

  delete: async (watchlistId: number) => {
    const response = await api.delete(`/watchlists/${watchlistId}`);
    return response.data;
  },
};

// ============================================
// Analytics API
// ============================================
export const analyticsApi = {
  getPortfolioMetrics: async (portfolioId: number) => {
    const response = await api.get(`/analytics/portfolio/${portfolioId}/metrics`);
    return response.data;
  },

  getPerformanceHistory: async (portfolioId: number, period: string = '1M') => {
    const response = await api.get(`/analytics/portfolio/${portfolioId}/performance`, {
      params: { period },
    });
    return response.data;
  },
};

// ============================================
// Currency API
// ============================================
export const currencyApi = {
  getSupportedCurrencies: async () => {
    const response = await api.get('/currency/supported');
    return response.data;
  },

  getRates: async (base: string = 'USD') => {
    const response = await api.get('/currency/rates', { params: { base } });
    return response.data;
  },

  convert: async (amount: number, fromCurrency: string, toCurrency: string) => {
    const response = await api.post('/currency/convert', {
      amount,
      from_currency: fromCurrency,
      to_currency: toCurrency,
    });
    return response.data;
  },

  // ========== Portfolio Currency Management (IBKR-style) ==========
  
  // Get all currency balances for a portfolio
  getPortfolioBalances: async (portfolioId: number) => {
    const response = await api.get(`/currency/portfolio/${portfolioId}/balances`);
    return response.data;
  },

  // Deposit funds in a specific currency
  deposit: async (portfolioId: number, currency: string, amount: number) => {
    const response = await api.post(`/currency/portfolio/${portfolioId}/deposit`, {
      currency,
      amount,
    });
    return response.data;
  },

  // Withdraw funds from a specific currency
  withdraw: async (portfolioId: number, currency: string, amount: number) => {
    const response = await api.post(`/currency/portfolio/${portfolioId}/withdraw`, {
      currency,
      amount,
    });
    return response.data;
  },

  // Convert between currencies (FX transaction)
  convertFx: async (
    portfolioId: number, 
    fromCurrency: string, 
    toCurrency: string, 
    amount: number
  ) => {
    const response = await api.post(`/currency/portfolio/${portfolioId}/fx-convert`, {
      from_currency: fromCurrency,
      to_currency: toCurrency,
      amount,
    });
    return response.data;
  },

  // Get FX transaction history for a portfolio
  getFxHistory: async (portfolioId: number, limit: number = 50) => {
    const response = await api.get(`/currency/portfolio/${portfolioId}/fx-history`, {
      params: { limit },
    });
    return response.data;
  },
};

// ============================================
// Settings API
// ============================================
export const settingsApi = {
  getSettings: async () => {
    const response = await api.get('/settings/');
    return response.data;
  },

  updateSettings: async (settings: {
    theme?: string;
    display?: {
      theme?: string;
      compact_mode?: boolean;
      show_percent_change?: boolean;
      default_chart_period?: string;
      chart_type?: string;
    };
    notifications?: {
      email?: boolean;
      push?: boolean;
      trade_execution?: boolean;
      price_alerts?: boolean;
      portfolio_updates?: boolean;
      market_news?: boolean;
    };
  }) => {
    const response = await api.patch('/settings/', settings);
    return response.data;
  },

  saveApiKey: async (provider: string, apiKey: string) => {
    const response = await api.post('/settings/api-keys', {
      provider,
      api_key: apiKey,
    });
    return response.data;
  },

  deleteApiKey: async (provider: string) => {
    const response = await api.delete(`/settings/api-keys/${provider}`);
    return response.data;
  },

  testConnection: async (provider: string) => {
    const response = await api.post('/settings/api-keys/test', { provider });
    return response.data;
  },

  importFromEnv: async () => {
    const response = await api.post('/settings/api-keys/import-from-env');
    return response.data;
  },
};

// ============================================
// ML Predictions API
// ============================================
export const mlApi = {
  /**
   * Get all active ML signals
   */
  getActiveSignals: async (symbol?: string) => {
    const params = symbol ? { symbol } : {};
    const response = await api.get('/ml/signals/active', { params });
    return response.data;
  },

  /**
   * Get ML prediction for a specific symbol
   */
  getPrediction: async (symbol: string) => {
    const response = await api.get(`/ml/predictions/${symbol.toUpperCase()}`);
    return response.data;
  },

  /**
   * Get ML predictions for multiple symbols
   */
  getPredictions: async (symbols?: string[]) => {
    const params = symbols ? { symbols: symbols.join(',') } : {};
    const response = await api.get('/ml/predictions', { params });
    return response.data;
  },

  /**
   * Manually trigger the ML predictions job
   */
  runJob: async (force: boolean = false) => {
    const response = await api.post('/ml/job/run', null, { params: { force } });
    return response.data;
  },

  /**
   * Get ML job status
   */
  getJobStatus: async () => {
    const response = await api.get('/ml/job/status');
    return response.data;
  },
};

export default api;
