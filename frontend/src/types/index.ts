/**
 * PaperTrading Platform - Type Definitions
 */

// ============================================
// User & Auth Types
// ============================================
export interface User {
  id: number;
  email: string;
  username: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  updated_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserWithToken extends User {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  username: string;
  password: string;
  full_name?: string;
}

// ============================================
// Portfolio Types
// ============================================
export type RiskProfile = 'aggressive' | 'balanced' | 'conservative';

export interface Portfolio {
  id: number;
  user_id: number;
  name: string;
  description: string | null;
  initial_capital: number;
  current_value: number;
  cash_balance: number;
  risk_profile: RiskProfile;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Position {
  id: number;
  portfolio_id: number;
  symbol: string;
  quantity: number;
  average_cost: number;
  average_price: number;
  current_price: number;
  current_value: number;
  market_value: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  unrealized_pnl_percent: number;
  created_at: string;
  updated_at: string;
}

// ============================================
// Trading Types
// ============================================
export type OrderType = 'market' | 'limit' | 'stop' | 'stop_limit';
export type OrderSide = 'buy' | 'sell';
export type OrderStatus = 'pending' | 'filled' | 'partial' | 'cancelled' | 'rejected';

export interface Order {
  id: number;
  portfolio_id: number;
  symbol: string;
  side: OrderSide;
  order_type: OrderType;
  quantity: number;
  limit_price: number | null;
  stop_price: number | null;
  status: OrderStatus;
  filled_quantity: number;
  filled_price: number | null;
  created_at: string;
  updated_at: string;
}

export interface Trade {
  id: number;
  portfolio_id: number;
  order_id?: number;
  symbol: string;
  side?: OrderSide;
  trade_type?: string;  // Backend uses trade_type (buy/sell)
  order_type?: string;
  status?: string;
  quantity: number;
  price: number;
  limit_price?: number;
  executed_price?: number;
  executed_quantity?: number;
  total_value: number;
  commission: number;
  realized_pnl?: number;
  executed_at?: string;
  created_at: string;
  notes?: string;
}

// ============================================
// Market Data Types
// ============================================
export interface Quote {
  symbol: string;
  price: number;
  change: number;
  change_percent: number;
  volume: number;
  high: number;
  low: number;
  open: number;
  previous_close: number;
  timestamp: string;
}

export interface HistoricalData {
  symbol: string;
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  adjusted_close?: number;
}

export interface WatchlistItem {
  id: number;
  symbol: string;
  name: string;
  added_at: string;
}

export interface Watchlist {
  id: number;
  user_id: number;
  name: string;
  symbols: WatchlistItem[];
  created_at: string;
  updated_at: string;
}

// ============================================
// Analytics Types
// ============================================
export interface PortfolioMetrics {
  total_value: number;
  total_gain_loss: number;
  total_gain_loss_percent: number;
  daily_change: number;
  daily_change_percent: number;
  cash_balance: number;
  invested_value: number;
}

export interface PerformanceData {
  date: string;
  value: number;
  benchmark_value?: number;
}

// ============================================
// UI Types
// ============================================
export type Theme = 'light' | 'dark' | 'system';

export interface Toast {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message?: string;
  duration?: number;
}

export interface TableColumn<T> {
  key: keyof T | string;
  label: string;
  sortable?: boolean;
  render?: (value: any, row: T) => React.ReactNode;
  className?: string;
}

// ============================================
// API Response Types
// ============================================
export interface ApiError {
  detail: string | { msg: string; type: string }[];
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ApiResponse<T> {
  data: T;
  message?: string;
}
