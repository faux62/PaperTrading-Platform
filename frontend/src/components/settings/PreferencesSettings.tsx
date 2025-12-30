/**
 * Preferences Settings Component
 * User preferences for notifications, display, etc.
 */
import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, Button } from '../common';
import { Bell, Eye, Palette, Save, DollarSign, RefreshCw, Clock } from 'lucide-react';
import { authApi, currencyApi, settingsApi } from '../../services/api';

interface NotificationSchedule {
  startTime: string;  // HH:mm format
  endTime: string;    // HH:mm format
  days: {
    monday: boolean;
    tuesday: boolean;
    wednesday: boolean;
    thursday: boolean;
    friday: boolean;
    saturday: boolean;
    sunday: boolean;
  };
}

interface PreferencesData {
  theme: 'dark' | 'light' | 'system';
  notifications: {
    email: boolean;
    push: boolean;
    priceAlerts: boolean;
    tradeConfirmations: boolean;
    dailySummary: boolean;
    schedule: NotificationSchedule;
  };
  display: {
    compactMode: boolean;
    showPnLPercentage: boolean;
    defaultCurrency: string;
  };
}

interface Currency {
  code: string;
  name: string;
  symbol: string;
}

interface PreferencesSettingsProps {
  initialData?: Partial<PreferencesData>;
  onSave?: (data: PreferencesData) => Promise<void>;
}

export const PreferencesSettings: React.FC<PreferencesSettingsProps> = ({
  initialData = {},
  onSave,
}) => {
  const [preferences, setPreferences] = useState<PreferencesData>({
    theme: initialData.theme || 'dark',
    notifications: {
      email: initialData.notifications?.email ?? true,
      push: initialData.notifications?.push ?? true,
      priceAlerts: initialData.notifications?.priceAlerts ?? true,
      tradeConfirmations: initialData.notifications?.tradeConfirmations ?? true,
      dailySummary: initialData.notifications?.dailySummary ?? false,
      schedule: initialData.notifications?.schedule ?? {
        startTime: '08:00',
        endTime: '22:00',
        days: {
          monday: true,
          tuesday: true,
          wednesday: true,
          thursday: true,
          friday: true,
          saturday: false,
          sunday: false,
        },
      },
    },
    display: {
      compactMode: initialData.display?.compactMode ?? false,
      showPnLPercentage: initialData.display?.showPnLPercentage ?? true,
      defaultCurrency: initialData.display?.defaultCurrency || 'USD',
    },
  });
  const [isLoading, setIsLoading] = useState(false);
  const [isCurrencyLoading, setIsCurrencyLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [currencies, setCurrencies] = useState<Currency[]>([]);
  const [exchangeRates, setExchangeRates] = useState<Record<string, number>>({});

  // Fetch user's current settings, base currency and available currencies
  useEffect(() => {
    const fetchData = async () => {
      try {
        // Load theme from localStorage
        const savedTheme = localStorage.getItem('papertrading-theme') as PreferencesData['theme'] | null;
        if (savedTheme && ['dark', 'light', 'system'].includes(savedTheme)) {
          setPreferences(prev => ({ ...prev, theme: savedTheme }));
        }
        
        const [userData, currencyData, settingsData] = await Promise.all([
          authApi.getMe(),
          currencyApi.getSupportedCurrencies(),
          settingsApi.getSettings(),
        ]);
        
        // Load saved settings from backend
        setPreferences(prev => ({
          ...prev,
          theme: savedTheme || settingsData.theme || 'dark',
          notifications: {
            email: settingsData.notifications?.email ?? true,
            push: settingsData.notifications?.push ?? true,
            priceAlerts: settingsData.notifications?.price_alerts ?? true,
            tradeConfirmations: settingsData.notifications?.trade_execution ?? true,
            dailySummary: settingsData.notifications?.market_news ?? false,
          },
          display: {
            compactMode: settingsData.display?.compact_mode ?? false,
            showPnLPercentage: settingsData.display?.show_percent_change ?? true,
            defaultCurrency: userData.base_currency || 'USD',
          },
        }));
        
        setCurrencies(currencyData.currencies || []);
      } catch (error) {
        console.error('Failed to fetch user data:', error);
      }
    };
    fetchData();
  }, []);

  // Fetch exchange rates when currency changes
  const fetchRates = async () => {
    setIsCurrencyLoading(true);
    try {
      const ratesData = await currencyApi.getRates('USD');
      setExchangeRates(ratesData.rates || {});
      setMessage({ type: 'success', text: 'Exchange rates updated' });
      setTimeout(() => setMessage(null), 3000);
    } catch {
      setMessage({ type: 'error', text: 'Failed to fetch exchange rates' });
    } finally {
      setIsCurrencyLoading(false);
    }
  };

  const handleNotificationChange = (key: keyof PreferencesData['notifications']) => {
    setPreferences(prev => ({
      ...prev,
      notifications: {
        ...prev.notifications,
        [key]: !prev.notifications[key],
      },
    }));
  };

  const handleDisplayChange = (key: keyof PreferencesData['display'], value: boolean | string) => {
    setPreferences(prev => ({
      ...prev,
      display: {
        ...prev.display,
        [key]: value,
      },
    }));
  };

  const handleScheduleTimeChange = (key: 'startTime' | 'endTime', value: string) => {
    setPreferences(prev => ({
      ...prev,
      notifications: {
        ...prev.notifications,
        schedule: {
          ...prev.notifications.schedule,
          [key]: value,
        },
      },
    }));
  };

  const handleScheduleDayChange = (day: keyof NotificationSchedule['days']) => {
    setPreferences(prev => ({
      ...prev,
      notifications: {
        ...prev.notifications,
        schedule: {
          ...prev.notifications.schedule,
          days: {
            ...prev.notifications.schedule.days,
            [day]: !prev.notifications.schedule.days[day],
          },
        },
      },
    }));
  };

  const handleThemeChange = (theme: PreferencesData['theme']) => {
    setPreferences(prev => ({ ...prev, theme }));
    
    // Apply theme to DOM immediately - toggle 'light' class on body
    const body = document.body;
    if (theme === 'system') {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      body.classList.toggle('light', !prefersDark);
    } else {
      body.classList.toggle('light', theme === 'light');
    }
    
    // Persist to localStorage
    localStorage.setItem('papertrading-theme', theme);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    setIsLoading(true);
    setMessage(null);

    try {
      // Save base currency to backend
      await authApi.updateMe({ base_currency: preferences.display.defaultCurrency });
      
      // Save settings (theme, notifications, display) to settings API
      await settingsApi.updateSettings({
        theme: preferences.theme,
        display: {
          theme: preferences.theme,
          compact_mode: preferences.display.compactMode,
          show_percent_change: preferences.display.showPnLPercentage,
          default_chart_period: '1M',
          chart_type: 'candlestick',
        },
        notifications: {
          email: preferences.notifications.email,
          push: preferences.notifications.push,
          trade_execution: preferences.notifications.tradeConfirmations,
          price_alerts: preferences.notifications.priceAlerts,
          portfolio_updates: true,
          market_news: preferences.notifications.dailySummary,
        },
      });
      
      // Call optional onSave for other preferences
      if (onSave) {
        await onSave(preferences);
      }
      
      setMessage({ type: 'success', text: 'Preferences saved successfully' });
    } catch {
      setMessage({ type: 'error', text: 'Failed to save preferences' });
    } finally {
      setIsLoading(false);
    }
  };

  const Toggle: React.FC<{ checked: boolean; onChange: () => void; label: string }> = ({
    checked,
    onChange,
    label,
  }) => (
    <label className="flex items-center justify-between py-2 cursor-pointer">
      <span className="text-surface-300">{label}</span>
      <button
        type="button"
        onClick={onChange}
        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
          checked ? 'bg-primary-500' : 'bg-surface-600'
        }`}
      >
        <span
          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
            checked ? 'translate-x-6' : 'translate-x-1'
          }`}
        />
      </button>
    </label>
  );

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Theme Settings */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Palette className="w-5 h-5 text-primary-500" />
            <h3 className="text-lg font-semibold text-white">Appearance</h3>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-surface-300 mb-2">
                Theme
              </label>
              <div className="flex gap-3">
                {(['dark', 'light', 'system'] as const).map(theme => (
                  <button
                    key={theme}
                    type="button"
                    onClick={() => handleThemeChange(theme)}
                    className={`px-4 py-2 rounded-lg capitalize transition-colors ${
                      preferences.theme === theme
                        ? 'bg-primary-500 text-white'
                        : 'bg-surface-700 text-surface-300 hover:bg-surface-600'
                    }`}
                  >
                    {theme}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Notification Settings */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Bell className="w-5 h-5 text-primary-500" />
            <h3 className="text-lg font-semibold text-white">Notifications</h3>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-1 divide-y divide-surface-700">
            <Toggle
              checked={preferences.notifications.email}
              onChange={() => handleNotificationChange('email')}
              label="Email notifications"
            />
            <Toggle
              checked={preferences.notifications.push}
              onChange={() => handleNotificationChange('push')}
              label="Push notifications"
            />
            <Toggle
              checked={preferences.notifications.priceAlerts}
              onChange={() => handleNotificationChange('priceAlerts')}
              label="Price alerts"
            />
            <Toggle
              checked={preferences.notifications.tradeConfirmations}
              onChange={() => handleNotificationChange('tradeConfirmations')}
              label="Trade confirmations"
            />
            <Toggle
              checked={preferences.notifications.dailySummary}
              onChange={() => handleNotificationChange('dailySummary')}
              label="Daily portfolio summary"
            />
          </div>
        </CardContent>
      </Card>

      {/* Notification Schedule */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Clock className="w-5 h-5 text-primary-500" />
            <h3 className="text-lg font-semibold text-white">Notification Schedule</h3>
          </div>
          <p className="text-sm text-surface-400 mt-1">
            Configure when you want to receive notifications
          </p>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {/* Time Range */}
            <div>
              <label className="block text-sm font-medium text-surface-300 mb-3">
                Active Hours
              </label>
              <div className="flex items-center gap-4">
                <div className="flex-1">
                  <label className="block text-xs text-surface-400 mb-1">From</label>
                  <input
                    type="time"
                    value={preferences.notifications.schedule.startTime}
                    onChange={(e) => handleScheduleTimeChange('startTime', e.target.value)}
                    className="w-full px-3 py-2 bg-surface-700 border border-surface-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
                <span className="text-surface-400 pt-5">to</span>
                <div className="flex-1">
                  <label className="block text-xs text-surface-400 mb-1">To</label>
                  <input
                    type="time"
                    value={preferences.notifications.schedule.endTime}
                    onChange={(e) => handleScheduleTimeChange('endTime', e.target.value)}
                    className="w-full px-3 py-2 bg-surface-700 border border-surface-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>
            </div>

            {/* Days Selection */}
            <div>
              <label className="block text-sm font-medium text-surface-300 mb-3">
                Active Days
              </label>
              <div className="flex flex-wrap gap-2">
                {([
                  { key: 'monday', label: 'Mon' },
                  { key: 'tuesday', label: 'Tue' },
                  { key: 'wednesday', label: 'Wed' },
                  { key: 'thursday', label: 'Thu' },
                  { key: 'friday', label: 'Fri' },
                  { key: 'saturday', label: 'Sat' },
                  { key: 'sunday', label: 'Sun' },
                ] as const).map(({ key, label }) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => handleScheduleDayChange(key)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      preferences.notifications.schedule.days[key]
                        ? 'bg-primary-500 text-white'
                        : 'bg-surface-700 text-surface-400 hover:bg-surface-600'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <p className="text-xs text-surface-500 mt-2">
                💡 Tip: Select weekdays only for trading-related notifications
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Display Settings */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Eye className="w-5 h-5 text-primary-500" />
            <h3 className="text-lg font-semibold text-white">Display</h3>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="space-y-1 divide-y divide-surface-700">
              <Toggle
                checked={preferences.display.compactMode}
                onChange={() => handleDisplayChange('compactMode', !preferences.display.compactMode)}
                label="Compact mode"
              />
              <Toggle
                checked={preferences.display.showPnLPercentage}
                onChange={() => handleDisplayChange('showPnLPercentage', !preferences.display.showPnLPercentage)}
                label="Show P&L as percentage"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Base Currency Settings */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <DollarSign className="w-5 h-5 text-primary-500" />
              <h3 className="text-lg font-semibold text-white">Base Currency</h3>
            </div>
            <button
              type="button"
              onClick={fetchRates}
              disabled={isCurrencyLoading}
              className="p-2 hover:bg-surface-700 rounded-lg transition-colors disabled:opacity-50"
              title="Refresh exchange rates"
            >
              <RefreshCw className={`w-4 h-4 text-surface-400 ${isCurrencyLoading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-surface-300 mb-2">
                Your Base Currency
              </label>
              <p className="text-xs text-surface-500 mb-3">
                All portfolio totals will be converted to this currency using real-time exchange rates.
              </p>
              <select
                value={preferences.display.defaultCurrency}
                onChange={(e) => handleDisplayChange('defaultCurrency', e.target.value)}
                className="w-full px-3 py-2 bg-surface-700 border border-surface-600 rounded-lg text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              >
                {currencies.length > 0 ? (
                  currencies.map(currency => (
                    <option key={currency.code} value={currency.code}>
                      {currency.code} ({currency.symbol}) - {currency.name}
                    </option>
                  ))
                ) : (
                  <>
                    <option value="USD">USD ($) - US Dollar</option>
                    <option value="EUR">EUR (€) - Euro</option>
                    <option value="GBP">GBP (£) - British Pound</option>
                    <option value="JPY">JPY (¥) - Japanese Yen</option>
                    <option value="CHF">CHF - Swiss Franc</option>
                    <option value="CAD">CAD (C$) - Canadian Dollar</option>
                    <option value="AUD">AUD (A$) - Australian Dollar</option>
                  </>
                )}
              </select>
            </div>

            {/* Exchange Rates Preview */}
            {Object.keys(exchangeRates).length > 0 && (
              <div className="mt-4 p-3 bg-surface-800 rounded-lg">
                <p className="text-xs text-surface-400 mb-2">Current Exchange Rates (vs USD):</p>
                <div className="grid grid-cols-3 gap-2 text-sm">
                  {Object.entries(exchangeRates)
                    .filter(([code]) => code !== 'USD')
                    .map(([code, rate]) => (
                      <div key={code} className="text-surface-300">
                        <span className="font-medium">{code}:</span> {rate.toFixed(4)}
                      </div>
                    ))}
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {message && (
        <div className={`p-3 rounded ${
          message.type === 'success' 
            ? 'bg-success-500/10 text-success-500' 
            : 'bg-danger-500/10 text-danger-500'
        }`}>
          {message.text}
        </div>
      )}

      <div className="flex justify-end">
        <Button type="submit" disabled={isLoading}>
          <Save className="w-4 h-4 mr-2" />
          {isLoading ? 'Saving...' : 'Save Preferences'}
        </Button>
      </div>
    </form>
  );
};

export default PreferencesSettings;
