/**
 * Trading Assistant Bot - Signal Card Component
 * Displays individual bot signals with action buttons
 */
import React from 'react';
import { 
  CheckCircle, 
  XCircle, 
  AlertTriangle, 
  TrendingUp, 
  TrendingDown,
  Clock,
  Target,
  Shield,
  Brain,
  Bell
} from 'lucide-react';

interface Signal {
  id: number;
  signal_type: string;
  priority: string;
  status: string;
  symbol?: string;
  direction?: string;
  title: string;
  message: string;
  rationale?: string;
  current_price?: number;
  suggested_entry?: number;
  suggested_stop_loss?: number;
  suggested_take_profit?: number;
  suggested_quantity?: number;
  risk_reward_ratio?: number;
  confidence_score?: number;
  ml_model_used?: string;
  created_at: string;
  valid_until?: string;
  is_actionable: boolean;
}

interface SignalCardProps {
  signal: Signal;
  onAccept: (signalId: number, notes?: string) => void;
  onIgnore: (signalId: number, notes?: string) => void;
  compact?: boolean;
}

const priorityColors = {
  urgent: 'border-red-500 bg-red-50 dark:bg-red-900/20',
  high: 'border-orange-500 bg-orange-50 dark:bg-orange-900/20',
  medium: 'border-blue-500 bg-blue-50 dark:bg-blue-900/20',
  low: 'border-gray-400 bg-gray-50 dark:bg-gray-800/50',
};

const priorityBadgeColors = {
  urgent: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  high: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  medium: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  low: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200',
};

const signalTypeIcons: Record<string, React.ReactNode> = {
  trade_suggestion: <Target className="w-5 h-5" />,
  position_alert: <AlertTriangle className="w-5 h-5" />,
  risk_warning: <Shield className="w-5 h-5" />,
  market_alert: <Bell className="w-5 h-5" />,
  ml_prediction: <Brain className="w-5 h-5" />,
  trailing_stop: <TrendingUp className="w-5 h-5" />,
};

export const SignalCard: React.FC<SignalCardProps> = ({
  signal,
  onAccept,
  onIgnore,
  compact = false,
}) => {
  const [showDetails, setShowDetails] = React.useState(!compact);
  const [notes, setNotes] = React.useState('');

  const priorityColor = priorityColors[signal.priority as keyof typeof priorityColors] || priorityColors.medium;
  const badgeColor = priorityBadgeColors[signal.priority as keyof typeof priorityBadgeColors] || priorityBadgeColors.medium;

  const formatPrice = (price?: number) => price ? `$${price.toFixed(2)}` : '-';
  
  const timeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = Math.floor((now.getTime() - date.getTime()) / 1000 / 60);
    
    if (diff < 1) return 'Just now';
    if (diff < 60) return `${diff}m ago`;
    if (diff < 1440) return `${Math.floor(diff / 60)}h ago`;
    return `${Math.floor(diff / 1440)}d ago`;
  };

  const isExpiringSoon = () => {
    if (!signal.valid_until) return false;
    const validUntil = new Date(signal.valid_until);
    const now = new Date();
    const hoursLeft = (validUntil.getTime() - now.getTime()) / 1000 / 60 / 60;
    return hoursLeft > 0 && hoursLeft < 2;
  };

  return (
    <div className={`border-l-4 rounded-lg shadow-sm ${priorityColor} p-4 transition-all hover:shadow-md`}>
      {/* Header */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-gray-600 dark:text-gray-400">
            {signalTypeIcons[signal.signal_type] || <Bell className="w-5 h-5" />}
          </span>
          <h3 className="font-semibold text-gray-900 dark:text-white">
            {signal.title}
          </h3>
        </div>
        <div className="flex items-center gap-2">
          <span className={`px-2 py-1 text-xs font-medium rounded-full ${badgeColor}`}>
            {signal.priority.toUpperCase()}
          </span>
          {signal.symbol && (
            <span className="px-2 py-1 text-xs font-mono bg-gray-200 dark:bg-gray-700 rounded">
              {signal.symbol}
            </span>
          )}
        </div>
      </div>

      {/* Direction Badge */}
      {signal.direction && (
        <div className="mb-3">
          <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium ${
            signal.direction === 'long' 
              ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' 
              : signal.direction === 'short'
              ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
              : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
          }`}>
            {signal.direction === 'long' && <TrendingUp className="w-4 h-4" />}
            {signal.direction === 'short' && <TrendingDown className="w-4 h-4" />}
            {signal.direction.toUpperCase()}
          </span>
        </div>
      )}

      {/* Trade Details (if trade suggestion) */}
      {signal.signal_type === 'trade_suggestion' && signal.suggested_entry && (
        <div className="bg-white dark:bg-gray-800 rounded-lg p-3 mb-3 border border-gray-200 dark:border-gray-700">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            <div>
              <span className="text-gray-500 dark:text-gray-400 block">Entry</span>
              <span className="font-semibold text-gray-900 dark:text-white">
                {formatPrice(signal.suggested_entry)}
              </span>
            </div>
            <div>
              <span className="text-gray-500 dark:text-gray-400 block">Stop Loss</span>
              <span className="font-semibold text-red-600">
                {formatPrice(signal.suggested_stop_loss)}
              </span>
            </div>
            <div>
              <span className="text-gray-500 dark:text-gray-400 block">Take Profit</span>
              <span className="font-semibold text-green-600">
                {formatPrice(signal.suggested_take_profit)}
              </span>
            </div>
            <div>
              <span className="text-gray-500 dark:text-gray-400 block">R:R Ratio</span>
              <span className={`font-semibold ${
                (signal.risk_reward_ratio || 0) >= 2 
                  ? 'text-green-600' 
                  : (signal.risk_reward_ratio || 0) >= 1.5 
                  ? 'text-yellow-600' 
                  : 'text-red-600'
              }`}>
                {signal.risk_reward_ratio?.toFixed(1)}:1
              </span>
            </div>
          </div>
          {signal.suggested_quantity && (
            <div className="mt-2 pt-2 border-t border-gray-200 dark:border-gray-700">
              <span className="text-gray-500 dark:text-gray-400">Suggested Qty: </span>
              <span className="font-semibold">{signal.suggested_quantity} shares</span>
            </div>
          )}
        </div>
      )}

      {/* ML Confidence */}
      {signal.confidence_score && (
        <div className="flex items-center gap-2 mb-3">
          <Brain className="w-4 h-4 text-purple-500" />
          <div className="flex-1">
            <div className="flex justify-between text-sm mb-1">
              <span className="text-gray-600 dark:text-gray-400">ML Confidence</span>
              <span className="font-medium">{signal.confidence_score.toFixed(0)}%</span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div 
                className={`h-2 rounded-full ${
                  signal.confidence_score >= 75 ? 'bg-green-500' :
                  signal.confidence_score >= 60 ? 'bg-yellow-500' : 'bg-red-500'
                }`}
                style={{ width: `${signal.confidence_score}%` }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Message (collapsible) */}
      {showDetails && (
        <div className="prose prose-sm dark:prose-invert max-w-none mb-3">
          <div 
            className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap"
            dangerouslySetInnerHTML={{ __html: signal.message.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') }}
          />
        </div>
      )}

      {/* Rationale */}
      {showDetails && signal.rationale && (
        <div className="bg-gray-100 dark:bg-gray-800 rounded p-2 mb-3 text-sm">
          <span className="text-gray-500 dark:text-gray-400 font-medium">Rationale: </span>
          <span className="text-gray-700 dark:text-gray-300">{signal.rationale}</span>
        </div>
      )}

      {/* Timestamps */}
      <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 mb-3">
        <span className="flex items-center gap-1">
          <Clock className="w-3 h-3" />
          {timeAgo(signal.created_at)}
        </span>
        {signal.valid_until && (
          <span className={`flex items-center gap-1 ${isExpiringSoon() ? 'text-orange-500 font-medium' : ''}`}>
            {isExpiringSoon() && <AlertTriangle className="w-3 h-3" />}
            Expires: {new Date(signal.valid_until).toLocaleTimeString()}
          </span>
        )}
      </div>

      {/* Action Buttons */}
      {signal.is_actionable && signal.status === 'pending' && (
        <div className="flex flex-col gap-2">
          {/* Notes input */}
          <input
            type="text"
            placeholder="Add notes (optional)..."
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg 
                       bg-white dark:bg-gray-800 text-gray-900 dark:text-white
                       focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          
          {/* Buttons */}
          <div className="flex gap-2">
            <button
              onClick={() => onAccept(signal.id, notes || undefined)}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 
                         bg-green-600 hover:bg-green-700 text-white rounded-lg 
                         transition-colors font-medium"
            >
              <CheckCircle className="w-4 h-4" />
              Accept
            </button>
            <button
              onClick={() => onIgnore(signal.id, notes || undefined)}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 
                         bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 
                         text-gray-700 dark:text-gray-200 rounded-lg transition-colors font-medium"
            >
              <XCircle className="w-4 h-4" />
              Ignore
            </button>
          </div>
        </div>
      )}

      {/* Status Badge (for non-pending signals) */}
      {signal.status !== 'pending' && (
        <div className={`flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-sm font-medium ${
          signal.status === 'accepted' 
            ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
            : signal.status === 'ignored'
            ? 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
            : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
        }`}>
          {signal.status === 'accepted' && <CheckCircle className="w-4 h-4" />}
          {signal.status === 'ignored' && <XCircle className="w-4 h-4" />}
          {signal.status === 'expired' && <Clock className="w-4 h-4" />}
          {signal.status.charAt(0).toUpperCase() + signal.status.slice(1)}
        </div>
      )}

      {/* Toggle Details (compact mode) */}
      {compact && (
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 mt-2"
        >
          {showDetails ? 'Hide details' : 'Show details'}
        </button>
      )}
    </div>
  );
};

export default SignalCard;
