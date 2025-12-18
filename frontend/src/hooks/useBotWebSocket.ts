/**
 * Bot WebSocket Hook for Trading Assistant Bot Real-Time Notifications
 * 
 * Connects to /ws/bot endpoint for real-time:
 * - Trade signals (ADVISORY ONLY)
 * - Position alerts
 * - Risk warnings
 * - Report notifications
 * - Bot status updates
 */
/* eslint-disable no-console */
import { useEffect, useRef, useCallback, useState } from 'react';
import { useAuthStore } from '../store/authStore';

// ==================== Types ====================

export type BotConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

export type BotNotificationType = 
  | 'connected'
  | 'new_signal'
  | 'signal_update'
  | 'position_alert'
  | 'risk_warning'
  | 'market_alert'
  | 'report_ready'
  | 'bot_status'
  | 'pre_market_briefing'
  | 'market_close_summary'
  | 'preferences_updated'
  | 'pong'
  | 'error';

export interface BotSignalData {
  id: number;
  signal_type: string;
  priority: string;
  status: string;
  symbol: string | null;
  direction: string | null;
  title: string;
  message: string;
  rationale: string;
  current_price: number | null;
  suggested_entry: number | null;
  suggested_stop_loss: number | null;
  suggested_take_profit: number | null;
  suggested_quantity: number | null;
  risk_reward_ratio: number | null;
  confidence_score: number | null;
  ml_model_used: string | null;
  source: string;
  portfolio_id: number | null;
  valid_until: string | null;
  created_at: string | null;
}

export interface BotNotification {
  type: BotNotificationType;
  category?: string;
  advisory_notice?: string;
  signal?: BotSignalData;
  alert?: BotSignalData;
  warning?: Record<string, unknown>;
  report?: Record<string, unknown>;
  briefing?: Record<string, unknown>;
  summary?: Record<string, unknown>;
  signal_id?: number;
  status?: string;
  data?: Record<string, unknown>;
  details?: Record<string, unknown>;
  message?: string;
  preferences?: NotificationPreferences;
  timestamp: string;
}

export interface NotificationPreferences {
  trade_signals: boolean;
  position_alerts: boolean;
  risk_warnings: boolean;
  market_alerts: boolean;
  reports: boolean;
  bot_status: boolean;
}

interface UseBotWebSocketOptions {
  onNewSignal?: (signal: BotSignalData) => void;
  onPositionAlert?: (alert: BotSignalData) => void;
  onRiskWarning?: (warning: Record<string, unknown>) => void;
  onMarketAlert?: (alert: Record<string, unknown>) => void;
  onReportReady?: (report: Record<string, unknown>) => void;
  onBotStatus?: (status: string, details?: Record<string, unknown>) => void;
  onPreMarketBriefing?: (briefing: Record<string, unknown>) => void;
  onMarketCloseSummary?: (summary: Record<string, unknown>) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  autoConnect?: boolean;
  reconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

interface UseBotWebSocketReturn {
  status: BotConnectionStatus;
  connect: () => void;
  disconnect: () => void;
  setPreferences: (preferences: Partial<NotificationPreferences>) => void;
  notifications: BotNotification[];
  clearNotifications: () => void;
  latestSignal: BotSignalData | null;
}

// ==================== Hook ====================

export function useBotWebSocket({
  onNewSignal,
  onPositionAlert,
  onRiskWarning,
  onMarketAlert,
  onReportReady,
  onBotStatus,
  onPreMarketBriefing,
  onMarketCloseSummary,
  onConnect,
  onDisconnect,
  autoConnect = true,
  reconnect = true,
  reconnectInterval = 5000,
  maxReconnectAttempts = 10,
}: UseBotWebSocketOptions = {}): UseBotWebSocketReturn {
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  
  const [status, setStatus] = useState<BotConnectionStatus>('disconnected');
  const [notifications, setNotifications] = useState<BotNotification[]>([]);
  const [latestSignal, setLatestSignal] = useState<BotSignalData | null>(null);
  
  const { accessToken, isAuthenticated } = useAuthStore();

  // Build WebSocket URL
  const getWebSocketUrl = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = import.meta.env.VITE_WS_HOST || window.location.host;
    const basePath = import.meta.env.VITE_API_BASE_PATH || '/api/v1';
    return `${protocol}//${host}${basePath}/ws/bot`;
  }, []);

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
      console.log('[BotWS] Already connected');
      return;
    }

    if (!accessToken) {
      console.warn('[BotWS] No access token available');
      return;
    }

    clearTimers();
    setStatus('connecting');

    const wsUrl = new URL(getWebSocketUrl());
    wsUrl.searchParams.set('token', accessToken);

    try {
      wsRef.current = new WebSocket(wsUrl.toString());

      wsRef.current.onopen = () => {
        console.log('[BotWS] Connected to Trading Assistant Bot');
        setStatus('connected');
        reconnectAttemptsRef.current = 0;
        onConnect?.();

        // Start ping interval (every 30 seconds)
        pingIntervalRef.current = setInterval(() => {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'ping' }));
          }
        }, 30000);
      };

      wsRef.current.onmessage = (event) => {
        try {
          const notification: BotNotification = JSON.parse(event.data);
          
          // Handle pong silently
          if (notification.type === 'pong') {
            return;
          }

          // Store all notifications (except pong)
          setNotifications(prev => [notification, ...prev].slice(0, 100));

          // Route to specific handlers
          switch (notification.type) {
            case 'connected':
              console.log('[BotWS] Bot confirmed connection:', notification.message);
              break;

            case 'new_signal':
              if (notification.signal) {
                setLatestSignal(notification.signal);
                onNewSignal?.(notification.signal);
              }
              break;

            case 'signal_update':
              // Handle signal status updates
              console.log('[BotWS] Signal update:', notification.signal_id, notification.status);
              break;

            case 'position_alert':
              if (notification.alert) {
                onPositionAlert?.(notification.alert);
              }
              break;

            case 'risk_warning':
              if (notification.warning) {
                onRiskWarning?.(notification.warning);
              }
              break;

            case 'market_alert':
              if (notification.alert) {
                onMarketAlert?.(notification.alert as unknown as Record<string, unknown>);
              }
              break;

            case 'report_ready':
              if (notification.report) {
                onReportReady?.(notification.report);
              }
              break;

            case 'bot_status':
              onBotStatus?.(notification.status || 'unknown', notification.details);
              break;

            case 'pre_market_briefing':
              if (notification.briefing) {
                onPreMarketBriefing?.(notification.briefing);
              }
              break;

            case 'market_close_summary':
              if (notification.summary) {
                onMarketCloseSummary?.(notification.summary);
              }
              break;

            case 'preferences_updated':
              console.log('[BotWS] Preferences updated:', notification.preferences);
              break;

            case 'error':
              console.error('[BotWS] Server error:', notification.message);
              break;

            default:
              console.log('[BotWS] Unknown message type:', notification.type);
          }
        } catch (error) {
          console.error('[BotWS] Failed to parse message:', error);
        }
      };

      wsRef.current.onerror = (error) => {
        console.error('[BotWS] Error:', error);
        setStatus('error');
      };

      wsRef.current.onclose = (event) => {
        console.log('[BotWS] Disconnected:', event.code, event.reason);
        setStatus('disconnected');
        clearTimers();
        onDisconnect?.();

        // Auto-reconnect logic
        if (reconnect && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++;
          console.log(`[BotWS] Reconnecting in ${reconnectInterval}ms (attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts})`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            if (isAuthenticated && accessToken) {
              connect();
            }
          }, reconnectInterval);
        }
      };

    } catch (error) {
      console.error('[BotWS] Failed to create WebSocket:', error);
      setStatus('error');
    }
  }, [
    accessToken,
    isAuthenticated,
    getWebSocketUrl,
    clearTimers,
    reconnect,
    reconnectInterval,
    maxReconnectAttempts,
    onConnect,
    onDisconnect,
    onNewSignal,
    onPositionAlert,
    onRiskWarning,
    onMarketAlert,
    onReportReady,
    onBotStatus,
    onPreMarketBriefing,
    onMarketCloseSummary,
  ]);

  const disconnect = useCallback(() => {
    clearTimers();
    reconnectAttemptsRef.current = maxReconnectAttempts; // Prevent reconnection
    
    if (wsRef.current) {
      wsRef.current.close(1000, 'User disconnect');
      wsRef.current = null;
    }
    
    setStatus('disconnected');
  }, [clearTimers, maxReconnectAttempts]);

  const setPreferences = useCallback((preferences: Partial<NotificationPreferences>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'set_preferences',
        preferences,
      }));
    }
  }, []);

  const clearNotifications = useCallback(() => {
    setNotifications([]);
  }, []);

  // Auto-connect effect
  useEffect(() => {
    if (autoConnect && isAuthenticated && accessToken) {
      connect();
    }

    return () => {
      disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoConnect, isAuthenticated, accessToken]); // Intentionally limited dependencies

  return {
    status,
    connect,
    disconnect,
    setPreferences,
    notifications,
    clearNotifications,
    latestSignal,
  };
}

export default useBotWebSocket;
