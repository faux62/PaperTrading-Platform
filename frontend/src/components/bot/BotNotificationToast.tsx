/**
 * Bot Notification Toast Component
 * 
 * Displays real-time notifications from the Trading Assistant Bot.
 * Shows toast notifications for new signals, alerts, and warnings.
 * 
 * ALL signals are ADVISORY ONLY - requires manual user action.
 */
import React, { useEffect, useState, useCallback } from 'react';
import { 
  useBotWebSocket, 
  BotSignalData, 
  BotConnectionStatus as BotConnectionStatusType 
} from '../../hooks/useBotWebSocket';

// ==================== Types ====================

interface Toast {
  id: string;
  type: 'signal' | 'alert' | 'warning' | 'info' | 'error';
  title: string;
  message: string;
  priority: string;
  symbol?: string;
  timestamp: Date;
  dismissed: boolean;
  signal?: BotSignalData;
}

interface BotNotificationToastProps {
  maxToasts?: number;
  autoHideDuration?: number;
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left';
  onSignalClick?: (signal: BotSignalData) => void;
  onConnectionChange?: (status: BotConnectionStatusType) => void;
}

// ==================== Component ====================

export const BotNotificationToast: React.FC<BotNotificationToastProps> = ({
  maxToasts = 5,
  autoHideDuration = 15000,
  position = 'top-right',
  onSignalClick,
  onConnectionChange,
}) => {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [soundEnabled, setSoundEnabled] = useState(true);

  // Play notification sound
  const playNotificationSound = useCallback(() => {
    if (!soundEnabled) return;
    try {
      const audio = new Audio('/sounds/notification.mp3');
      audio.volume = 0.5;
      audio.play().catch(() => {
        // Ignore audio play errors (e.g., user hasn't interacted with page)
      });
    } catch {
      // Audio not supported
    }
  }, [soundEnabled]);

  // Dismiss toast
  const dismissToast = useCallback((id: string) => {
    setToasts(prev => prev.map(t => 
      t.id === id ? { ...t, dismissed: true } : t
    ));

    // Remove after animation
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 300);
  }, []);

  // Add toast
  const addToast = useCallback((toast: Omit<Toast, 'id' | 'timestamp' | 'dismissed'>) => {
    const newToast: Toast = {
      ...toast,
      id: `toast-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date(),
      dismissed: false,
    };

    setToasts(prev => {
      const updated = [newToast, ...prev].slice(0, maxToasts);
      return updated;
    });

    // Play sound for high priority
    if (toast.priority === 'HIGH' || toast.priority === 'CRITICAL') {
      playNotificationSound();
    }

    // Auto-hide after duration (except for critical alerts)
    if (toast.priority !== 'CRITICAL') {
      setTimeout(() => {
        dismissToast(newToast.id);
      }, autoHideDuration);
    }
  }, [maxToasts, autoHideDuration, playNotificationSound, dismissToast]);

  // WebSocket handlers
  const handleNewSignal = useCallback((signal: BotSignalData) => {
    addToast({
      type: 'signal',
      title: signal.title,
      message: `${signal.symbol} - ${signal.direction?.toUpperCase() || 'ALERT'}`,
      priority: signal.priority,
      symbol: signal.symbol || undefined,
      signal,
    });
  }, [addToast]);

  const handlePositionAlert = useCallback((alert: BotSignalData) => {
    addToast({
      type: 'alert',
      title: alert.title,
      message: alert.message?.substring(0, 100) || 'Position alert',
      priority: alert.priority,
      symbol: alert.symbol || undefined,
      signal: alert,
    });
  }, [addToast]);

  const handleRiskWarning = useCallback((warning: Record<string, unknown>) => {
    addToast({
      type: 'warning',
      title: (warning.title as string) || '⚠️ Risk Warning',
      message: (warning.message as string) || 'Review your risk exposure',
      priority: 'HIGH',
    });
  }, [addToast]);

  const handleBotStatus = useCallback((status: string, details?: Record<string, unknown>) => {
    if (status === 'error') {
      addToast({
        type: 'error',
        title: 'Bot Status',
        message: (details?.message as string) || 'Bot encountered an issue',
        priority: 'MEDIUM',
      });
    }
  }, [addToast]);

  // Initialize WebSocket
  const { status } = useBotWebSocket({
    onNewSignal: handleNewSignal,
    onPositionAlert: handlePositionAlert,
    onRiskWarning: handleRiskWarning,
    onBotStatus: handleBotStatus,
    autoConnect: true,
    reconnect: true,
  });

  // Notify parent of connection changes
  useEffect(() => {
    onConnectionChange?.(status);
  }, [status, onConnectionChange]);

  // Position classes
  const positionClasses: Record<string, string> = {
    'top-right': 'top-4 right-4',
    'top-left': 'top-4 left-4',
    'bottom-right': 'bottom-4 right-4',
    'bottom-left': 'bottom-4 left-4',
  };

  // Type-specific styling
  const getTypeClasses = (type: Toast['type'], priority: string) => {
    const base = 'border-l-4';
    
    if (priority === 'CRITICAL') {
      return `${base} border-red-500 bg-red-50 dark:bg-red-900/20`;
    }

    switch (type) {
      case 'signal':
        return `${base} border-blue-500 bg-blue-50 dark:bg-blue-900/20`;
      case 'alert':
        return `${base} border-yellow-500 bg-yellow-50 dark:bg-yellow-900/20`;
      case 'warning':
        return `${base} border-orange-500 bg-orange-50 dark:bg-orange-900/20`;
      case 'error':
        return `${base} border-red-500 bg-red-50 dark:bg-red-900/20`;
      default:
        return `${base} border-gray-500 bg-gray-50 dark:bg-gray-800`;
    }
  };

  const getPriorityBadge = (priority: string) => {
    const colors: Record<string, string> = {
      CRITICAL: 'bg-red-500 text-white',
      HIGH: 'bg-orange-500 text-white',
      MEDIUM: 'bg-yellow-500 text-gray-900',
      LOW: 'bg-gray-400 text-white',
    };
    return colors[priority] || colors.MEDIUM;
  };

  const getTypeIcon = (type: Toast['type']) => {
    switch (type) {
      case 'signal':
        return '💡';
      case 'alert':
        return '📈';
      case 'warning':
        return '⚠️';
      case 'error':
        return '❌';
      default:
        return 'ℹ️';
    }
  };

  return (
    <>
      {/* Connection Status Indicator */}
      <div className={`fixed ${positionClasses[position]} z-50`}>
        {/* Status Badge */}
        <div className="flex items-center justify-end mb-2 text-xs">
          <div className={`flex items-center gap-1 px-2 py-1 rounded-full ${
            status === 'connected' 
              ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
              : status === 'connecting'
              ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300'
              : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
          }`}>
            <span className={`w-2 h-2 rounded-full ${
              status === 'connected' ? 'bg-green-500 animate-pulse' : 
              status === 'connecting' ? 'bg-yellow-500 animate-pulse' : 'bg-gray-400'
            }`} />
            <span>Bot {status}</span>
          </div>
          
          {/* Sound Toggle */}
          <button
            onClick={() => setSoundEnabled(!soundEnabled)}
            className="ml-2 p-1 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
            title={soundEnabled ? 'Mute notifications' : 'Enable notification sounds'}
          >
            {soundEnabled ? '🔔' : '🔕'}
          </button>
        </div>

        {/* Toast Container */}
        <div className="flex flex-col gap-2 max-w-sm">
          {toasts.filter(t => !t.dismissed).map(toast => (
            <div
              key={toast.id}
              className={`
                ${getTypeClasses(toast.type, toast.priority)}
                rounded-lg shadow-lg p-4 cursor-pointer
                transform transition-all duration-300
                hover:scale-102 hover:shadow-xl
                ${toast.dismissed ? 'opacity-0 -translate-x-full' : 'opacity-100 translate-x-0'}
              `}
              onClick={() => {
                if (toast.signal && onSignalClick) {
                  onSignalClick(toast.signal);
                }
                dismissToast(toast.id);
              }}
            >
              {/* Header */}
              <div className="flex items-start justify-between mb-1">
                <div className="flex items-center gap-2">
                  <span className="text-lg">{getTypeIcon(toast.type)}</span>
                  <span className={`text-xs px-2 py-0.5 rounded ${getPriorityBadge(toast.priority)}`}>
                    {toast.priority}
                  </span>
                  {toast.symbol && (
                    <span className="text-xs font-mono bg-gray-200 dark:bg-gray-700 px-1 rounded">
                      {toast.symbol}
                    </span>
                  )}
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    dismissToast(toast.id);
                  }}
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  ✕
                </button>
              </div>

              {/* Title */}
              <h4 className="font-semibold text-gray-900 dark:text-white text-sm">
                {toast.title}
              </h4>

              {/* Message */}
              <p className="text-gray-600 dark:text-gray-300 text-xs mt-1 line-clamp-2">
                {toast.message}
              </p>

              {/* Advisory Notice for Signals */}
              {toast.type === 'signal' && (
                <p className="text-xs text-orange-600 dark:text-orange-400 mt-2 italic">
                  ⚠️ Advisory only - Manual execution required
                </p>
              )}

              {/* Timestamp */}
              <p className="text-xs text-gray-400 mt-2">
                {toast.timestamp.toLocaleTimeString()}
              </p>
            </div>
          ))}
        </div>
      </div>
    </>
  );
};

// ==================== Connection Status Component ====================

interface BotConnectionStatusProps {
  className?: string;
}

export const BotConnectionStatus: React.FC<BotConnectionStatusProps> = ({ className }) => {
  const { status } = useBotWebSocket({ autoConnect: false });

  const statusConfig: Record<BotConnectionStatusType, { color: string; label: string; pulse: boolean }> = {
    connected: { color: 'bg-green-500', label: 'Connected', pulse: true },
    connecting: { color: 'bg-yellow-500', label: 'Connecting...', pulse: true },
    disconnected: { color: 'bg-gray-400', label: 'Disconnected', pulse: false },
    error: { color: 'bg-red-500', label: 'Error', pulse: false },
  };

  const config = statusConfig[status];

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <span className={`w-2 h-2 rounded-full ${config.color} ${config.pulse ? 'animate-pulse' : ''}`} />
      <span className="text-sm text-gray-600 dark:text-gray-400">
        Bot: {config.label}
      </span>
    </div>
  );
};

export default BotNotificationToast;
