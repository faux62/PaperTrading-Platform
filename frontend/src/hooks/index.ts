/**
 * Hooks Index
 * Export all custom hooks
 */
export { useWebSocket, useMarketWebSocket, usePortfolioWebSocket } from './useWebSocket';
export type { 
  WebSocketStatus, 
  WebSocketMessage, 
  MarketQuote,
  PortfolioUpdate,
  OrderStatusUpdate,
  TradeExecutionUpdate,
} from './useWebSocket';

export { useBotWebSocket } from './useBotWebSocket';
export type {
  BotConnectionStatus,
  BotNotificationType,
  BotSignalData,
  BotNotification,
  NotificationPreferences,
} from './useBotWebSocket';
