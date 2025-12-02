/**
 * WebSocket Hook for PaperTrading Platform
 * Manages WebSocket connection with automatic reconnection
 */
import { useEffect, useRef, useCallback, useState } from 'react';
import { useAuthStore } from '../store/authStore';

export type WebSocketStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

export interface WebSocketMessage {
  type: string;
  data?: unknown;
  symbol?: string;
  message?: string;
  error?: string;
  timestamp?: number;
}

interface UseWebSocketOptions {
  url: string;
  onMessage?: (message: WebSocketMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
  autoConnect?: boolean;
  reconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  pingInterval?: number;
}

interface UseWebSocketReturn {
  status: WebSocketStatus;
  connect: () => void;
  disconnect: () => void;
  send: (message: WebSocketMessage) => void;
  subscribe: (symbol: string) => void;
  unsubscribe: (symbol: string) => void;
  subscribedSymbols: string[];
}

export function useWebSocket({
  url,
  onMessage,
  onConnect,
  onDisconnect,
  onError,
  autoConnect = true,
  reconnect = true,
  reconnectInterval = 3000,
  maxReconnectAttempts = 10,
  pingInterval = 30000,
}: UseWebSocketOptions): UseWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  
  const [status, setStatus] = useState<WebSocketStatus>('disconnected');
  const [subscribedSymbols, setSubscribedSymbols] = useState<string[]>([]);
  
  const { accessToken } = useAuthStore();

  const clearTimers = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.log('[WebSocket] Already connected');
      return;
    }

    if (!accessToken) {
      console.warn('[WebSocket] No access token available');
      return;
    }

    clearTimers();
    setStatus('connecting');

    // Build URL with token
    const wsUrl = new URL(url);
    wsUrl.searchParams.set('token', accessToken);

    try {
      wsRef.current = new WebSocket(wsUrl.toString());

      wsRef.current.onopen = () => {
        console.log('[WebSocket] Connected');
        setStatus('connected');
        reconnectAttemptsRef.current = 0;
        onConnect?.();

        // Start ping interval
        pingIntervalRef.current = setInterval(() => {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'ping' }));
          }
        }, pingInterval);

        // Re-subscribe to symbols after reconnection
        subscribedSymbols.forEach(symbol => {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'subscribe', symbol }));
          }
        });
      };

      wsRef.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          
          // Handle pong silently
          if (message.type === 'pong') {
            return;
          }

          // Handle subscription confirmations
          if (message.type === 'subscribed' && message.symbol) {
            setSubscribedSymbols(prev => 
              prev.includes(message.symbol!) ? prev : [...prev, message.symbol!]
            );
          }

          if (message.type === 'unsubscribed' && message.symbol) {
            setSubscribedSymbols(prev => prev.filter(s => s !== message.symbol));
          }

          onMessage?.(message);
        } catch (error) {
          console.error('[WebSocket] Failed to parse message:', error);
        }
      };

      wsRef.current.onerror = (error) => {
        console.error('[WebSocket] Error:', error);
        setStatus('error');
        onError?.(error);
      };

      wsRef.current.onclose = () => {
        console.log('[WebSocket] Disconnected');
        setStatus('disconnected');
        clearTimers();
        onDisconnect?.();

        // Attempt reconnection
        if (reconnect && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++;
          console.log(
            `[WebSocket] Reconnecting... attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts}`
          );
          reconnectTimeoutRef.current = setTimeout(connect, reconnectInterval);
        }
      };
    } catch (error) {
      console.error('[WebSocket] Failed to create connection:', error);
      setStatus('error');
    }
  }, [
    url,
    accessToken,
    onConnect,
    onDisconnect,
    onError,
    onMessage,
    reconnect,
    reconnectInterval,
    maxReconnectAttempts,
    pingInterval,
    clearTimers,
    subscribedSymbols,
  ]);

  const disconnect = useCallback(() => {
    clearTimers();
    reconnectAttemptsRef.current = maxReconnectAttempts; // Prevent auto-reconnect
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    setStatus('disconnected');
  }, [clearTimers, maxReconnectAttempts]);

  const send = useCallback((message: WebSocketMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('[WebSocket] Cannot send message, not connected');
    }
  }, []);

  const subscribe = useCallback((symbol: string) => {
    if (!subscribedSymbols.includes(symbol)) {
      send({ type: 'subscribe', symbol });
    }
  }, [send, subscribedSymbols]);

  const unsubscribe = useCallback((symbol: string) => {
    if (subscribedSymbols.includes(symbol)) {
      send({ type: 'unsubscribe', symbol });
    }
  }, [send, subscribedSymbols]);

  // Auto-connect on mount if enabled
  useEffect(() => {
    if (autoConnect && accessToken) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, accessToken]); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    status,
    connect,
    disconnect,
    send,
    subscribe,
    unsubscribe,
    subscribedSymbols,
  };
}

// Convenience hook for market data stream
export function useMarketWebSocket(onQuote?: (quote: MarketQuote) => void) {
  const WS_URL = `${import.meta.env.VITE_WS_URL || 'ws://localhost:8000'}/api/v1/ws/market`;

  return useWebSocket({
    url: WS_URL,
    onMessage: (message) => {
      if (message.type === 'quote' && onQuote) {
        onQuote(message.data as MarketQuote);
      }
    },
  });
}

// Market quote type
export interface MarketQuote {
  symbol: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  timestamp: number;
  bid?: number;
  ask?: number;
  high?: number;
  low?: number;
  open?: number;
}

// Portfolio update types
export interface PortfolioUpdate {
  portfolio_id: number;
  total_value: number;
  cash: number;
  positions_value: number;
  daily_pnl: number;
  daily_pnl_percent: number;
  total_pnl: number;
  total_pnl_percent: number;
  timestamp: number;
}

export interface OrderStatusUpdate {
  order_id: number;
  symbol: string;
  status: 'pending' | 'filled' | 'partial' | 'cancelled' | 'rejected';
  filled_quantity: number;
  filled_price: number;
  message?: string;
  timestamp: number;
}

export interface TradeExecutionUpdate {
  trade_id: number;
  order_id: number;
  symbol: string;
  quantity: number;
  price: number;
  side: 'buy' | 'sell';
  timestamp: number;
}

// Convenience hook for portfolio real-time updates
export function usePortfolioWebSocket(options?: {
  onPortfolioUpdate?: (update: PortfolioUpdate) => void;
  onOrderStatus?: (update: OrderStatusUpdate) => void;
  onTradeExecution?: (update: TradeExecutionUpdate) => void;
}) {
  const WS_URL = `${import.meta.env.VITE_WS_URL || 'ws://localhost:8000'}/api/v1/ws/portfolio`;

  return useWebSocket({
    url: WS_URL,
    onMessage: (message) => {
      switch (message.type) {
        case 'portfolio_update':
          options?.onPortfolioUpdate?.(message.data as PortfolioUpdate);
          break;
        case 'order_status':
          options?.onOrderStatus?.(message.data as OrderStatusUpdate);
          break;
        case 'trade_execution':
          options?.onTradeExecution?.(message.data as TradeExecutionUpdate);
          break;
      }
    },
  });
}
