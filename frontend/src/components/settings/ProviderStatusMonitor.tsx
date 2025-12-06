/**
 * Provider Status Monitor Component
 * Real-time monitoring of data provider rate limits, health, and budget
 */
import React, { useState, useEffect } from 'react';
import { Activity, AlertCircle, CheckCircle, Clock, TrendingUp, DollarSign, RefreshCw } from 'lucide-react';

interface RateLimitInfo {
  configured: boolean;
  limits: {
    per_minute?: number;
    per_hour?: number;
    per_day?: number;
  };
  remaining: {
    per_minute?: number;
    per_hour?: number;
    per_day?: number;
  };
  can_proceed: boolean;
  wait_time: number;
}

interface HealthInfo {
  is_healthy: boolean;
  circuit_state: string;
  avg_latency_ms: number;
  error_rate: number;
}

interface BudgetInfo {
  daily_limit: number | null;
  daily_spent: number;
}

interface ProviderStatus {
  rate_limit: RateLimitInfo;
  health: HealthInfo;
  budget: BudgetInfo;
}

interface ProvidersStatusResponse {
  providers: Record<string, ProviderStatus>;
  total_providers: number;
  timestamp: string;
}

interface RateLimitsResponse {
  rate_limits: Record<string, {
    limits: Record<string, number>;
    remaining: Record<string, number>;
    can_proceed: boolean;
    wait_time_seconds: number;
    usage_percent: Record<string, number>;
  }>;
  timestamp: string;
}

const ProviderStatusMonitor: React.FC = () => {
  const [status, setStatus] = useState<ProvidersStatusResponse | null>(null);
  const [rateLimits, setRateLimits] = useState<RateLimitsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchStatus = async () => {
    try {
      const token = localStorage.getItem('token');
      const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      };

      const [statusRes, rateLimitsRes] = await Promise.all([
        fetch('/api/v1/providers/status', { headers }),
        fetch('/api/v1/providers/rate-limits', { headers }),
      ]);

      if (!statusRes.ok || !rateLimitsRes.ok) {
        throw new Error('Failed to fetch provider status');
      }

      const statusData = await statusRes.json();
      const rateLimitsData = await rateLimitsRes.json();

      setStatus(statusData);
      setRateLimits(rateLimitsData);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    
    let interval: NodeJS.Timeout | null = null;
    if (autoRefresh) {
      interval = setInterval(fetchStatus, 10000); // Refresh every 10 seconds
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh]);

  const getUsageColor = (percent: number): string => {
    if (percent >= 90) return 'text-red-500';
    if (percent >= 70) return 'text-yellow-500';
    return 'text-green-500';
  };

  const getUsageBarColor = (percent: number): string => {
    if (percent >= 90) return 'bg-red-500';
    if (percent >= 70) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const getCircuitStateColor = (state: string): string => {
    switch (state) {
      case 'closed': return 'text-green-500';
      case 'half_open': return 'text-yellow-500';
      case 'open': return 'text-red-500';
      default: return 'text-gray-500';
    }
  };

  const formatProviderName = (name: string): string => {
    return name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <RefreshCw className="w-6 h-6 animate-spin text-blue-500" />
        <span className="ml-2">Loading provider status...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
        <div className="flex items-center">
          <AlertCircle className="w-5 h-5 text-red-500 mr-2" />
          <span className="text-red-700 dark:text-red-300">{error}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="w-6 h-6 text-blue-500" />
          <h2 className="text-xl font-semibold">Provider Status Monitor</h2>
        </div>
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded border-gray-300"
            />
            <span className="text-sm">Auto-refresh (10s)</span>
          </label>
          <button
            onClick={fetchStatus}
            className="flex items-center gap-1 px-3 py-1.5 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400 mb-1">
            <TrendingUp className="w-4 h-4" />
            Total Providers
          </div>
          <div className="text-2xl font-bold">{status?.total_providers || 0}</div>
        </div>
        
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400 mb-1">
            <CheckCircle className="w-4 h-4 text-green-500" />
            Healthy
          </div>
          <div className="text-2xl font-bold text-green-500">
            {status?.providers
              ? Object.values(status.providers).filter(p => p.health?.is_healthy !== false).length
              : 0}
          </div>
        </div>
        
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400 mb-1">
            <Clock className="w-4 h-4" />
            Last Update
          </div>
          <div className="text-lg font-medium">
            {status?.timestamp
              ? new Date(status.timestamp).toLocaleTimeString()
              : '--'}
          </div>
        </div>
      </div>

      {/* Provider Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {rateLimits?.rate_limits && Object.entries(rateLimits.rate_limits).map(([name, data]) => {
          const providerStatus = status?.providers?.[name];
          
          return (
            <div
              key={name}
              className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700"
            >
              {/* Provider Header */}
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-lg">{formatProviderName(name)}</h3>
                <div className="flex items-center gap-2">
                  {providerStatus?.health?.is_healthy !== false ? (
                    <span className="flex items-center gap-1 text-green-500 text-sm">
                      <CheckCircle className="w-4 h-4" />
                      Healthy
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-red-500 text-sm">
                      <AlertCircle className="w-4 h-4" />
                      Unhealthy
                    </span>
                  )}
                </div>
              </div>

              {/* Rate Limits */}
              <div className="space-y-3">
                {data.usage_percent && Object.entries(data.usage_percent).map(([window, percent]) => (
                  <div key={window} className="space-y-1">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600 dark:text-gray-400 capitalize">
                        {window.replace(/_/g, ' ')}
                      </span>
                      <span className={getUsageColor(percent)}>
                        {data.remaining?.[window as keyof typeof data.remaining] || 0} / {data.limits?.[window as keyof typeof data.limits] || 0}
                        <span className="ml-2 text-xs">({percent.toFixed(1)}%)</span>
                      </span>
                    </div>
                    <div className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                      <div
                        className={`h-full transition-all duration-300 ${getUsageBarColor(percent)}`}
                        style={{ width: `${Math.min(percent, 100)}%` }}
                      />
                    </div>
                  </div>
                ))}

                {/* Can Proceed Status */}
                <div className="flex items-center justify-between pt-2 border-t border-gray-100 dark:border-gray-700">
                  <span className="text-sm text-gray-500">Can Proceed</span>
                  {data.can_proceed ? (
                    <span className="text-green-500 font-medium">Yes</span>
                  ) : (
                    <span className="text-red-500 font-medium">
                      No (wait {data.wait_time_seconds}s)
                    </span>
                  )}
                </div>

                {/* Health Info */}
                {providerStatus?.health && Object.keys(providerStatus.health).length > 0 && (
                  <div className="flex items-center justify-between pt-2 border-t border-gray-100 dark:border-gray-700">
                    <span className="text-sm text-gray-500">Circuit State</span>
                    <span className={`font-medium capitalize ${getCircuitStateColor(providerStatus.health.circuit_state)}`}>
                      {providerStatus.health.circuit_state}
                    </span>
                  </div>
                )}

                {providerStatus?.health?.avg_latency_ms !== undefined && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-500">Avg Latency</span>
                    <span className="font-medium">
                      {providerStatus.health.avg_latency_ms.toFixed(0)}ms
                    </span>
                  </div>
                )}

                {providerStatus?.health?.error_rate !== undefined && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-500">Error Rate</span>
                    <span className={`font-medium ${providerStatus.health.error_rate > 5 ? 'text-red-500' : 'text-green-500'}`}>
                      {providerStatus.health.error_rate.toFixed(1)}%
                    </span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* No providers message */}
      {(!rateLimits?.rate_limits || Object.keys(rateLimits.rate_limits).length === 0) && (
        <div className="text-center py-8 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <Activity className="w-12 h-12 mx-auto text-gray-400 mb-3" />
          <h3 className="text-lg font-medium text-gray-700 dark:text-gray-300 mb-1">
            No Providers Configured
          </h3>
          <p className="text-gray-500 dark:text-gray-400">
            Configure your data provider API keys in Settings to start monitoring.
          </p>
        </div>
      )}
    </div>
  );
};

export default ProviderStatusMonitor;
