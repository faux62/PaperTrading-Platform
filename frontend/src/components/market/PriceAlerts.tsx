/**
 * Price Alerts Component
 * Manage price alerts for stocks
 */
import { useState, useEffect, useCallback } from 'react';
import { 
  Bell, 
  Plus, 
  Trash2, 
  TrendingUp, 
  TrendingDown,
  ToggleLeft,
  ToggleRight,
  CheckCircle,
  Clock,
  AlertTriangle
} from 'lucide-react';
import Card, { CardContent, CardHeader } from '../common/Card';
import Button from '../common/Button';
import { tokenStorage } from '../../services/tokenStorage';

// Types
type AlertType = 'price_above' | 'price_below' | 'percent_change_up' | 'percent_change_down';
type AlertStatus = 'active' | 'triggered' | 'expired' | 'disabled';

interface Alert {
  id: number;
  user_id: number;
  symbol: string;
  alert_type: AlertType;
  target_value: number;
  status: AlertStatus;
  is_recurring: boolean;
  note: string | null;
  triggered_at: string | null;
  triggered_price: number | null;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
}

interface AlertSummary {
  total: number;
  active: number;
  triggered: number;
  disabled: number;
  expired: number;
}

interface PriceAlertsProps {
  symbol?: string;
}

const ALERT_TYPE_LABELS: Record<AlertType, string> = {
  price_above: 'Price Above',
  price_below: 'Price Below',
  percent_change_up: '% Change Up',
  percent_change_down: '% Change Down',
};

const STATUS_COLORS: Record<AlertStatus, string> = {
  active: 'text-green-500',
  triggered: 'text-blue-500',
  disabled: 'text-gray-500',
  expired: 'text-red-500',
};

export function PriceAlerts({ symbol }: PriceAlertsProps) {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [summary, setSummary] = useState<AlertSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  
  // Form state
  const [newAlert, setNewAlert] = useState({
    symbol: symbol || '',
    alert_type: 'price_above' as AlertType,
    target_value: '',
    note: '',
    is_recurring: false,
  });

  const fetchAlerts = useCallback(async () => {
    try {
      const token = tokenStorage.getAccessToken();
      const url = symbol 
        ? `/api/v1/alerts/?symbol=${symbol}` 
        : '/api/v1/alerts/';
      
      const response = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      if (response.ok) {
        const data = await response.json();
        setAlerts(data);
      }
    } catch (error) {
      console.error('Failed to fetch alerts:', error);
    } finally {
      setLoading(false);
    }
  }, [symbol]);

  const fetchSummary = useCallback(async () => {
    try {
      const token = tokenStorage.getAccessToken();
      const response = await fetch('/api/v1/alerts/summary', {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      if (response.ok) {
        const data = await response.json();
        setSummary(data);
      }
    } catch (error) {
      console.error('Failed to fetch summary:', error);
    }
  }, []);

  useEffect(() => {
    fetchAlerts();
    fetchSummary();
  }, [fetchAlerts, fetchSummary]);

  // Create alert
  const createAlert = async () => {
    if (!newAlert.symbol || !newAlert.target_value) return;

    try {
      const token = tokenStorage.getAccessToken();
      const response = await fetch('/api/v1/alerts/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          symbol: newAlert.symbol.toUpperCase(),
          alert_type: newAlert.alert_type,
          target_value: parseFloat(newAlert.target_value),
          note: newAlert.note || null,
          is_recurring: newAlert.is_recurring,
        }),
      });

      if (response.ok) {
        const created = await response.json();
        setAlerts((prev) => [created, ...prev]);
        setShowCreateForm(false);
        setNewAlert({
          symbol: symbol || '',
          alert_type: 'price_above',
          target_value: '',
          note: '',
          is_recurring: false,
        });
        fetchSummary();
      }
    } catch (error) {
      console.error('Failed to create alert:', error);
    }
  };

  // Toggle alert
  const toggleAlert = async (alertId: number) => {
    try {
      const token = tokenStorage.getAccessToken();
      const response = await fetch(`/api/v1/alerts/${alertId}/toggle`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const updated = await response.json();
        setAlerts((prev) =>
          prev.map((a) => (a.id === alertId ? updated : a))
        );
        fetchSummary();
      }
    } catch (error) {
      console.error('Failed to toggle alert:', error);
    }
  };

  // Delete alert
  const deleteAlert = async (alertId: number) => {
    try {
      const token = tokenStorage.getAccessToken();
      const response = await fetch(`/api/v1/alerts/${alertId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        setAlerts((prev) => prev.filter((a) => a.id !== alertId));
        fetchSummary();
      }
    } catch (error) {
      console.error('Failed to delete alert:', error);
    }
  };

  const getAlertIcon = (alertType: AlertType) => {
    switch (alertType) {
      case 'price_above':
      case 'percent_change_up':
        return <TrendingUp className="h-4 w-4 text-green-500" />;
      case 'price_below':
      case 'percent_change_down':
        return <TrendingDown className="h-4 w-4 text-red-500" />;
    }
  };

  const getStatusIcon = (status: AlertStatus) => {
    switch (status) {
      case 'active':
        return <Clock className="h-4 w-4 text-green-500" />;
      case 'triggered':
        return <CheckCircle className="h-4 w-4 text-blue-500" />;
      case 'disabled':
        return <ToggleLeft className="h-4 w-4 text-gray-500" />;
      case 'expired':
        return <AlertTriangle className="h-4 w-4 text-red-500" />;
    }
  };

  // Get currency prefix based on stock ticker suffix
  const getCurrencyPrefix = (sym: string): string => {
    if (!sym) return '$';
    
    const upperSymbol = sym.toUpperCase();
    
    if (upperSymbol.endsWith('.L')) return 'GBX ';
    if (upperSymbol.endsWith('.HK')) return 'HK$';
    if (upperSymbol.endsWith('.T')) return '¥';
    if (upperSymbol.endsWith('.MI') || upperSymbol.endsWith('.PA') || 
        upperSymbol.endsWith('.AS') || upperSymbol.endsWith('.BR') ||
        upperSymbol.endsWith('.DE') || upperSymbol.endsWith('.F')) return '€';
    if (upperSymbol.endsWith('.SW')) return 'CHF ';
    if (upperSymbol.endsWith('.TO')) return 'C$';
    if (upperSymbol.endsWith('.AX')) return 'A$';
    if (upperSymbol.endsWith('.SI')) return 'S$';
    if (upperSymbol.endsWith('.NS') || upperSymbol.endsWith('.BO')) return '₹';
    
    return '$';
  };

  const formatValue = (alertType: AlertType, value: number, sym: string = '') => {
    if (alertType.includes('percent')) {
      return `${value.toFixed(2)}%`;
    }
    const prefix = getCurrencyPrefix(sym);
    return `${prefix}${value.toFixed(2)}`;
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Bell className="h-5 w-5 text-yellow-500" />
            Price Alerts
          </h3>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 bg-muted animate-pulse rounded-lg" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold flex items-center gap-2 text-white">
            <Bell className="h-5 w-5 text-yellow-500" />
            Price Alerts
            {summary && (
              <span className="text-xs font-normal text-gray-400">
                ({summary.active} active)
              </span>
            )}
          </h3>
          <Button size="sm" variant="outline" onClick={() => setShowCreateForm(true)}>
            <Plus className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Summary Stats */}
        {summary && !symbol && (
          <div className="grid grid-cols-4 gap-2 p-3 bg-surface-800 rounded-lg mb-4">
            <div className="text-center">
              <p className="text-lg font-bold text-green-500">{summary.active}</p>
              <p className="text-xs text-gray-400">Active</p>
            </div>
            <div className="text-center">
              <p className="text-lg font-bold text-blue-500">{summary.triggered}</p>
              <p className="text-xs text-gray-400">Triggered</p>
            </div>
            <div className="text-center">
              <p className="text-lg font-bold text-gray-500">{summary.disabled}</p>
              <p className="text-xs text-gray-400">Disabled</p>
            </div>
            <div className="text-center">
              <p className="text-lg font-bold text-red-500">{summary.expired}</p>
              <p className="text-xs text-gray-400">Expired</p>
            </div>
          </div>
        )}

        {/* Create Form */}
        {showCreateForm && (
          <div className="p-4 border border-gray-600 rounded-lg bg-gray-800 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <input
                type="text"
                placeholder="Symbol (e.g., AAPL)"
                value={newAlert.symbol}
                onChange={(e) => setNewAlert({ ...newAlert, symbol: e.target.value.toUpperCase() })}
                className="px-3 py-2 bg-gray-900 border border-gray-600 rounded-md text-sm text-white placeholder:text-gray-500"
                disabled={!!symbol}
              />
              <select
                value={newAlert.alert_type}
                onChange={(e) => setNewAlert({ ...newAlert, alert_type: e.target.value as AlertType })}
                className="px-3 py-2 bg-gray-900 border border-gray-600 rounded-md text-sm text-white"
              >
                {Object.entries(ALERT_TYPE_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <input
                type="number"
                placeholder={newAlert.alert_type.includes('percent') ? 'Percentage (e.g., 5)' : 'Price (e.g., 150.00)'}
                value={newAlert.target_value}
                onChange={(e) => setNewAlert({ ...newAlert, target_value: e.target.value })}
                className="px-3 py-2 bg-gray-900 border border-gray-600 rounded-md text-sm text-white placeholder:text-gray-500"
                step="0.01"
              />
              <input
                type="text"
                placeholder="Note (optional)"
                value={newAlert.note}
                onChange={(e) => setNewAlert({ ...newAlert, note: e.target.value })}
                className="px-3 py-2 bg-gray-900 border border-gray-600 rounded-md text-sm text-white placeholder:text-gray-500"
              />
            </div>
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 text-sm text-gray-300">
                <input
                  type="checkbox"
                  checked={newAlert.is_recurring}
                  onChange={(e) => setNewAlert({ ...newAlert, is_recurring: e.target.checked })}
                  className="rounded"
                />
                Recurring (re-activate after trigger)
              </label>
              <div className="flex gap-2">
                <Button size="sm" onClick={createAlert}>Create Alert</Button>
                <Button size="sm" variant="ghost" onClick={() => setShowCreateForm(false)}>Cancel</Button>
              </div>
            </div>
          </div>
        )}

        {/* Alerts List */}
        {alerts.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-6">
            No alerts yet. Create one to get notified when prices change.
          </p>
        ) : (
          <div className="space-y-2">
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className="flex items-center justify-between p-3 border border-gray-700 rounded-lg hover:bg-gray-800 transition-colors"
              >
                <div className="flex items-center gap-3">
                  {getAlertIcon(alert.alert_type)}
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-white">{alert.symbol}</span>
                      <span className="text-sm text-gray-400">
                        {ALERT_TYPE_LABELS[alert.alert_type]}
                      </span>
                      <span className="font-mono text-sm text-white">
                        {formatValue(alert.alert_type, alert.target_value, alert.symbol)}
                      </span>
                    </div>
                    {alert.note && (
                      <p className="text-xs text-gray-400">{alert.note}</p>
                    )}
                    {alert.triggered_at && (
                      <p className="text-xs text-blue-400">
                        Triggered at {getCurrencyPrefix(alert.symbol)}{alert.triggered_price?.toFixed(2)} on{' '}
                        {new Date(alert.triggered_at).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                </div>
                
                <div className="flex items-center gap-2">
                  <div className="flex items-center gap-1">
                    {getStatusIcon(alert.status)}
                    <span className={`text-xs capitalize ${STATUS_COLORS[alert.status]}`}>
                      {alert.status}
                    </span>
                  </div>
                  
                  {(alert.status === 'active' || alert.status === 'disabled') && (
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-8 w-8 p-0"
                      onClick={() => toggleAlert(alert.id)}
                    >
                      {alert.status === 'active' ? (
                        <ToggleRight className="h-4 w-4 text-green-500" />
                      ) : (
                        <ToggleLeft className="h-4 w-4 text-gray-500" />
                      )}
                    </Button>
                  )}
                  
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-8 w-8 p-0"
                    onClick={() => deleteAlert(alert.id)}
                  >
                    <Trash2 className="h-4 w-4 text-red-500" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default PriceAlerts;
