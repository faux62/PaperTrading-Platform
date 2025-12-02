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

    // Handle 401 - Try to refresh token
    if (error.response?.status === 401 && !originalRequest._retry) {
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
          // Refresh failed - clear tokens and redirect
          tokenStorage.clearTokens();
          window.location.href = '/login';
          return Promise.reject(error);
        }
      } else {
        // No refresh token - redirect to login
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
  login: async (email: string, password: string) => {
    const response = await api.post('/auth/login/json', { email, password });
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
    const response = await api.get('/portfolios');
    return response.data;
  },

  getById: async (id: number) => {
    const response = await api.get(`/portfolios/${id}`);
    return response.data;
  },

  create: async (data: { name: string; initial_capital: number; risk_profile: string }) => {
    const response = await api.post('/portfolios', data);
    return response.data;
  },

  update: async (id: number, data: Partial<{ name: string; risk_profile: string }>) => {
    const response = await api.put(`/portfolios/${id}`, data);
    return response.data;
  },

  delete: async (id: number) => {
    const response = await api.delete(`/portfolios/${id}`);
    return response.data;
  },

  getPositions: async (portfolioId: number) => {
    const response = await api.get(`/portfolios/${portfolioId}/positions`);
    return response.data;
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

  getTradeHistory: async (portfolioId: number) => {
    const response = await api.get(`/trades/history/${portfolioId}`);
    return response.data;
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
    const response = await api.get(`/market-data/quote/${symbol}`);
    return response.data;
  },

  getQuotes: async (symbols: string[]) => {
    const response = await api.post('/market-data/quotes', { symbols });
    return response.data;
  },

  getHistorical: async (symbol: string, period: string = '1M') => {
    const response = await api.get(`/market-data/historical/${symbol}`, { params: { period } });
    return response.data;
  },

  search: async (query: string) => {
    const response = await api.get('/market-data/search', { params: { q: query } });
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

export default api;
