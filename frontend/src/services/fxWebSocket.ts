/**
 * FX Rate WebSocket Service
 * 
 * Manages real-time FX rate updates via WebSocket.
 * Broadcasts rate updates to subscribed components.
 */
import { tokenStorage } from './tokenStorage';
import { refreshAccessToken } from './api';

// WebSocket URL
const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/api/v1/ws';

export interface FXRates {
  USD: number;
  EUR: number;
  GBP: number;
  JPY: number;
  CHF: number;
  CAD: number;
  AUD: number;
  [key: string]: number;
}

export interface FXRateMessage {
  type: 'fx_rates' | 'ping' | 'pong';
  rates?: FXRates;
  base?: string;
  timestamp?: string;
}

type FXRateCallback = (rates: FXRates, timestamp: string) => void;

class FXWebSocketService {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private callbacks: Set<FXRateCallback> = new Set();
  private currentRates: FXRates | null = null;
  private lastTimestamp: string | null = null;
  private pingInterval: NodeJS.Timeout | null = null;
  private isRefreshingToken = false;

  /**
   * Connect to FX WebSocket
   */
  connect(): void {
    const token = tokenStorage.getAccessToken();
    if (!token) {
      console.warn('FX WebSocket: No auth token available');
      return;
    }

    if (this.ws?.readyState === WebSocket.OPEN) {
      console.log('FX WebSocket: Already connected');
      return;
    }

    try {
      this.ws = new WebSocket(`${WS_BASE_URL}/fx?token=${token}`);

      this.ws.onopen = () => {
        console.log('FX WebSocket: Connected');
        this.reconnectAttempts = 0;
        this.startPingInterval();
      };

      this.ws.onmessage = (event) => {
        try {
          const message: FXRateMessage = JSON.parse(event.data);
          this.handleMessage(message);
        } catch (e) {
          console.error('FX WebSocket: Failed to parse message', e);
        }
      };

      this.ws.onclose = (event) => {
        console.log('FX WebSocket: Disconnected', event.code, event.reason);
        this.stopPingInterval();
        
        // Handle token expired codes - try to refresh token first
        // 4001 = backend custom code, 4003 = standard forbidden
        if (event.code === 4001 || event.code === 1008 || event.code === 403 || event.code === 4003) {
          this.handleTokenExpired();
        } else {
          this.attemptReconnect();
        }
      };

      this.ws.onerror = (error) => {
        console.error('FX WebSocket: Error', error);
      };
    } catch (e) {
      console.error('FX WebSocket: Connection failed', e);
      this.attemptReconnect();
    }
  }

  /**
   * Handle token expired - refresh and reconnect
   */
  private async handleTokenExpired(): Promise<void> {
    if (this.isRefreshingToken) {
      return;
    }

    this.isRefreshingToken = true;
    console.log('FX WebSocket: Token expired, attempting refresh...');

    try {
      const newToken = await refreshAccessToken();
      if (newToken) {
        console.log('FX WebSocket: Token refreshed, reconnecting...');
        this.reconnectAttempts = 0; // Reset attempts after successful refresh
        this.connect();
      } else {
        console.log('FX WebSocket: Token refresh failed, giving up');
        // Don't redirect - let the API interceptor handle it
      }
    } catch (error) {
      console.error('FX WebSocket: Token refresh error:', error);
    } finally {
      this.isRefreshingToken = false;
    }
  }

  /**
   * Disconnect from WebSocket
   */
  disconnect(): void {
    this.stopPingInterval();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.reconnectAttempts = this.maxReconnectAttempts; // Prevent auto-reconnect
  }

  /**
   * Subscribe to FX rate updates
   */
  subscribe(callback: FXRateCallback): () => void {
    this.callbacks.add(callback);

    // Send current rates immediately if available
    if (this.currentRates && this.lastTimestamp) {
      callback(this.currentRates, this.lastTimestamp);
    }

    // Return unsubscribe function
    return () => {
      this.callbacks.delete(callback);
    };
  }

  /**
   * Get current rates (synchronous)
   */
  getCurrentRates(): FXRates | null {
    return this.currentRates;
  }

  /**
   * Get exchange rate between two currencies
   */
  getRate(fromCurrency: string, toCurrency: string): number {
    if (!this.currentRates) return 1;
    if (fromCurrency === toCurrency) return 1;

    const fromRate = this.currentRates[fromCurrency] || 1;
    const toRate = this.currentRates[toCurrency] || 1;

    // Rates are based on USD, so: toRate / fromRate
    return toRate / fromRate;
  }

  /**
   * Request fresh rates from server
   */
  requestRates(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'get_rates' }));
    }
  }

  private handleMessage(message: FXRateMessage): void {
    switch (message.type) {
      case 'fx_rates':
        if (message.rates) {
          this.currentRates = message.rates;
          this.lastTimestamp = message.timestamp || new Date().toISOString();
          
          // Notify all subscribers
          this.callbacks.forEach((callback) => {
            callback(this.currentRates!, this.lastTimestamp!);
          });
        }
        break;

      case 'ping':
        // Respond to server ping
        if (this.ws?.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify({ type: 'pong' }));
        }
        break;

      case 'pong':
        // Server acknowledged our ping
        break;
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('FX WebSocket: Max reconnect attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    
    console.log(`FX WebSocket: Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
    
    setTimeout(() => {
      this.connect();
    }, delay);
  }

  private startPingInterval(): void {
    this.stopPingInterval();
    this.pingInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000); // Ping every 30 seconds
  }

  private stopPingInterval(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }
}

// Export singleton instance
export const fxWebSocket = new FXWebSocketService();

// Export hook-friendly helpers
export const connectFXWebSocket = () => fxWebSocket.connect();
export const disconnectFXWebSocket = () => fxWebSocket.disconnect();
export const subscribeFXRates = (callback: FXRateCallback) => fxWebSocket.subscribe(callback);
export const getCurrentFXRates = () => fxWebSocket.getCurrentRates();
export const getFXRate = (from: string, to: string) => fxWebSocket.getRate(from, to);
