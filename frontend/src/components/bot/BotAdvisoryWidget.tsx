/**
 * Trading Assistant Bot - Advisory Widget
 * Dashboard widget showing pending signals and recent reports
 */
import React, { useState, useEffect } from 'react';
import { 
  Bot, 
  Bell, 
  FileText, 
  ChevronRight,
  RefreshCw,
  TrendingUp,
  AlertTriangle,
  CheckCircle2
} from 'lucide-react';
import { SignalCard } from './SignalCard';

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

interface Report {
  id: number;
  report_type: string;
  report_date: string;
  title: string;
  is_read: boolean;
}

interface BotStatus {
  is_running: boolean;
  pending_signals_count: number;
  unread_reports_count: number;
}

interface BotAdvisoryWidgetProps {
  onViewAllSignals?: () => void;
  onViewAllReports?: () => void;
  onViewReport?: (reportId: number) => void;
}

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const BotAdvisoryWidget: React.FC<BotAdvisoryWidgetProps> = ({
  onViewAllSignals,
  onViewAllReports,
  onViewReport,
}) => {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [status, setStatus] = useState<BotStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'signals' | 'reports'>('signals');

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const token = localStorage.getItem('token');
      const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      };

      // Fetch status
      const statusRes = await fetch(`${API_BASE}/api/v1/bot/status`, { headers });
      if (statusRes.ok) {
        const statusData = await statusRes.json();
        setStatus(statusData);
      }

      // Fetch pending signals
      const signalsRes = await fetch(`${API_BASE}/api/v1/bot/signals/pending?limit=5`, { headers });
      if (signalsRes.ok) {
        const signalsData = await signalsRes.json();
        setSignals(signalsData);
      }

      // Fetch recent reports
      const reportsRes = await fetch(`${API_BASE}/api/v1/bot/reports?limit=5`, { headers });
      if (reportsRes.ok) {
        const reportsData = await reportsRes.json();
        setReports(reportsData);
      }
    } catch (err) {
      setError('Failed to load bot data');
      console.error('Bot data fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    
    // Refresh every 60 seconds
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, []);

  const handleAcceptSignal = async (signalId: number, notes?: string) => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_BASE}/api/v1/bot/signals/${signalId}/action`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ action: 'accept', notes }),
      });

      if (res.ok) {
        // Remove from list
        setSignals(signals.filter(s => s.id !== signalId));
        if (status) {
          setStatus({ ...status, pending_signals_count: status.pending_signals_count - 1 });
        }
      }
    } catch (err) {
      console.error('Failed to accept signal:', err);
    }
  };

  const handleIgnoreSignal = async (signalId: number, notes?: string) => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_BASE}/api/v1/bot/signals/${signalId}/action`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ action: 'ignore', notes }),
      });

      if (res.ok) {
        setSignals(signals.filter(s => s.id !== signalId));
        if (status) {
          setStatus({ ...status, pending_signals_count: status.pending_signals_count - 1 });
        }
      }
    } catch (err) {
      console.error('Failed to ignore signal:', err);
    }
  };

  const formatReportDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getReportIcon = (reportType: string) => {
    switch (reportType) {
      case 'morning_briefing':
        return <TrendingUp className="w-4 h-4 text-blue-500" />;
      case 'daily_summary':
        return <FileText className="w-4 h-4 text-green-500" />;
      case 'weekly_report':
        return <FileText className="w-4 h-4 text-purple-500" />;
      default:
        return <FileText className="w-4 h-4 text-gray-500" />;
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bot className="w-6 h-6 text-white" />
            <h2 className="text-lg font-semibold text-white">Trading Assistant</h2>
          </div>
          <div className="flex items-center gap-2">
            {status && (
              <span className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
                status.is_running 
                  ? 'bg-green-500/20 text-green-100' 
                  : 'bg-red-500/20 text-red-100'
              }`}>
                <span className={`w-2 h-2 rounded-full ${
                  status.is_running ? 'bg-green-400 animate-pulse' : 'bg-red-400'
                }`} />
                {status.is_running ? 'Active' : 'Inactive'}
              </span>
            )}
            <button 
              onClick={fetchData}
              className="p-1.5 hover:bg-white/20 rounded-lg transition-colors"
              disabled={loading}
            >
              <RefreshCw className={`w-4 h-4 text-white ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Stats */}
        {status && (
          <div className="flex gap-4 mt-3">
            <div className="flex items-center gap-2">
              <Bell className="w-4 h-4 text-white/80" />
              <span className="text-white/80 text-sm">
                {status.pending_signals_count} pending signals
              </span>
            </div>
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-white/80" />
              <span className="text-white/80 text-sm">
                {status.unread_reports_count} unread reports
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 dark:border-gray-700">
        <button
          onClick={() => setActiveTab('signals')}
          className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium transition-colors ${
            activeTab === 'signals'
              ? 'border-b-2 border-blue-500 text-blue-600 dark:text-blue-400'
              : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          <AlertTriangle className="w-4 h-4" />
          Signals
          {status && status.pending_signals_count > 0 && (
            <span className="bg-red-500 text-white text-xs px-1.5 py-0.5 rounded-full">
              {status.pending_signals_count}
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab('reports')}
          className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium transition-colors ${
            activeTab === 'reports'
              ? 'border-b-2 border-blue-500 text-blue-600 dark:text-blue-400'
              : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          <FileText className="w-4 h-4" />
          Reports
          {status && status.unread_reports_count > 0 && (
            <span className="bg-blue-500 text-white text-xs px-1.5 py-0.5 rounded-full">
              {status.unread_reports_count}
            </span>
          )}
        </button>
      </div>

      {/* Content */}
      <div className="p-4 max-h-[500px] overflow-y-auto">
        {loading && (
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="w-6 h-6 animate-spin text-gray-400" />
          </div>
        )}

        {error && (
          <div className="text-center py-8 text-red-500">
            <AlertTriangle className="w-8 h-8 mx-auto mb-2" />
            <p>{error}</p>
          </div>
        )}

        {!loading && !error && activeTab === 'signals' && (
          <>
            {signals.length === 0 ? (
              <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                <CheckCircle2 className="w-12 h-12 mx-auto mb-3 text-green-500" />
                <p className="font-medium">All caught up!</p>
                <p className="text-sm">No pending signals at the moment.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {signals.map(signal => (
                  <SignalCard
                    key={signal.id}
                    signal={signal}
                    onAccept={handleAcceptSignal}
                    onIgnore={handleIgnoreSignal}
                    compact
                  />
                ))}
              </div>
            )}
          </>
        )}

        {!loading && !error && activeTab === 'reports' && (
          <>
            {reports.length === 0 ? (
              <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                <FileText className="w-12 h-12 mx-auto mb-3" />
                <p>No reports available yet.</p>
              </div>
            ) : (
              <div className="space-y-2">
                {reports.map(report => (
                  <button
                    key={report.id}
                    onClick={() => onViewReport?.(report.id)}
                    className={`w-full flex items-center gap-3 p-3 rounded-lg text-left transition-colors ${
                      !report.is_read 
                        ? 'bg-blue-50 dark:bg-blue-900/20 hover:bg-blue-100 dark:hover:bg-blue-900/30' 
                        : 'hover:bg-gray-100 dark:hover:bg-gray-700'
                    }`}
                  >
                    {getReportIcon(report.report_type)}
                    <div className="flex-1 min-w-0">
                      <p className={`text-sm truncate ${
                        !report.is_read ? 'font-semibold text-gray-900 dark:text-white' : 'text-gray-700 dark:text-gray-300'
                      }`}>
                        {report.title}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {formatReportDate(report.report_date)}
                      </p>
                    </div>
                    {!report.is_read && (
                      <span className="w-2 h-2 bg-blue-500 rounded-full" />
                    )}
                    <ChevronRight className="w-4 h-4 text-gray-400" />
                  </button>
                ))}
              </div>
            )}
          </>
        )}
      </div>

      {/* Footer */}
      <div className="border-t border-gray-200 dark:border-gray-700 p-3 bg-gray-50 dark:bg-gray-900">
        <div className="flex justify-between">
          {activeTab === 'signals' && onViewAllSignals && (
            <button
              onClick={onViewAllSignals}
              className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 font-medium flex items-center gap-1"
            >
              View all signals
              <ChevronRight className="w-4 h-4" />
            </button>
          )}
          {activeTab === 'reports' && onViewAllReports && (
            <button
              onClick={onViewAllReports}
              className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 font-medium flex items-center gap-1"
            >
              View all reports
              <ChevronRight className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default BotAdvisoryWidget;
