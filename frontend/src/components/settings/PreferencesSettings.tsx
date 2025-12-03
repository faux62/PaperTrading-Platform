/**
 * Preferences Settings Component
 * User preferences for notifications, display, etc.
 */
import React, { useState } from 'react';
import { Card, CardContent, CardHeader, Button } from '../common';
import { Bell, Eye, Palette, Save } from 'lucide-react';

interface PreferencesData {
  theme: 'dark' | 'light' | 'system';
  notifications: {
    email: boolean;
    push: boolean;
    priceAlerts: boolean;
    tradeConfirmations: boolean;
    dailySummary: boolean;
  };
  display: {
    compactMode: boolean;
    showPnLPercentage: boolean;
    defaultCurrency: string;
  };
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
    },
    display: {
      compactMode: initialData.display?.compactMode ?? false,
      showPnLPercentage: initialData.display?.showPnLPercentage ?? true,
      defaultCurrency: initialData.display?.defaultCurrency || 'USD',
    },
  });
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

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

  const handleThemeChange = (theme: PreferencesData['theme']) => {
    setPreferences(prev => ({ ...prev, theme }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!onSave) return;

    setIsLoading(true);
    setMessage(null);

    try {
      await onSave(preferences);
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

            <div>
              <label className="block text-sm font-medium text-surface-300 mb-2">
                Default Currency
              </label>
              <select
                value={preferences.display.defaultCurrency}
                onChange={(e) => handleDisplayChange('defaultCurrency', e.target.value)}
                className="w-full px-3 py-2 bg-surface-700 border border-surface-600 rounded-lg text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              >
                <option value="USD">USD ($)</option>
                <option value="EUR">EUR (€)</option>
                <option value="GBP">GBP (£)</option>
                <option value="JPY">JPY (¥)</option>
                <option value="CHF">CHF (Fr)</option>
              </select>
            </div>
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
