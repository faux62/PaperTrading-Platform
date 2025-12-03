/**
 * Data Provider Settings Component
 * Configure API keys for market data providers
 */
import React, { useState } from 'react';
import { Card, CardContent, CardHeader, Button, Input } from '../common';
import { Database, CheckCircle, XCircle, RefreshCw } from 'lucide-react';

interface ProviderConfig {
  name: string;
  key: string;
  description: string;
  enabled: boolean;
  status: 'connected' | 'disconnected' | 'error';
  lastChecked?: Date;
}

interface DataProviderSettingsProps {
  providers?: ProviderConfig[];
  onSaveProvider?: (provider: string, apiKey: string) => Promise<void>;
  onTestConnection?: (provider: string) => Promise<boolean>;
}

const DEFAULT_PROVIDERS: ProviderConfig[] = [
  {
    name: 'Alpha Vantage',
    key: 'alphavantage',
    description: 'Real-time and historical stock data',
    enabled: true,
    status: 'disconnected',
  },
  {
    name: 'Finnhub',
    key: 'finnhub',
    description: 'Stock market data and news',
    enabled: true,
    status: 'disconnected',
  },
  {
    name: 'Polygon.io',
    key: 'polygon',
    description: 'Real-time and historical market data',
    enabled: true,
    status: 'disconnected',
  },
  {
    name: 'Yahoo Finance',
    key: 'yahoo',
    description: 'Free market data (no API key required)',
    enabled: true,
    status: 'connected',
  },
];

export const DataProviderSettings: React.FC<DataProviderSettingsProps> = ({
  providers = DEFAULT_PROVIDERS,
  onSaveProvider,
  onTestConnection,
}) => {
  const [apiKeys, setApiKeys] = useState<Record<string, string>>({});
  const [testingProvider, setTestingProvider] = useState<string | null>(null);
  const [savingProvider, setSavingProvider] = useState<string | null>(null);
  const [providerStatuses, setProviderStatuses] = useState<Record<string, ProviderConfig['status']>>(
    Object.fromEntries(providers.map(p => [p.key, p.status]))
  );
  const [messages, setMessages] = useState<Record<string, { type: 'success' | 'error'; text: string }>>({});

  const handleApiKeyChange = (providerKey: string, value: string) => {
    setApiKeys(prev => ({ ...prev, [providerKey]: value }));
  };

  const handleTestConnection = async (providerKey: string) => {
    if (!onTestConnection) return;

    setTestingProvider(providerKey);
    setMessages(prev => ({ ...prev, [providerKey]: { type: 'success', text: '' } }));

    try {
      const success = await onTestConnection(providerKey);
      setProviderStatuses(prev => ({
        ...prev,
        [providerKey]: success ? 'connected' : 'error',
      }));
      setMessages(prev => ({
        ...prev,
        [providerKey]: {
          type: success ? 'success' : 'error',
          text: success ? 'Connection successful!' : 'Connection failed',
        },
      }));
    } catch {
      setProviderStatuses(prev => ({ ...prev, [providerKey]: 'error' }));
      setMessages(prev => ({
        ...prev,
        [providerKey]: { type: 'error', text: 'Connection test failed' },
      }));
    } finally {
      setTestingProvider(null);
    }
  };

  const handleSaveApiKey = async (providerKey: string) => {
    if (!onSaveProvider) return;

    const apiKey = apiKeys[providerKey];
    if (!apiKey) return;

    setSavingProvider(providerKey);
    try {
      await onSaveProvider(providerKey, apiKey);
      setMessages(prev => ({
        ...prev,
        [providerKey]: { type: 'success', text: 'API key saved successfully' },
      }));
      // Clear the input after saving
      setApiKeys(prev => ({ ...prev, [providerKey]: '' }));
    } catch {
      setMessages(prev => ({
        ...prev,
        [providerKey]: { type: 'error', text: 'Failed to save API key' },
      }));
    } finally {
      setSavingProvider(null);
    }
  };

  const getStatusIcon = (status: ProviderConfig['status']) => {
    switch (status) {
      case 'connected':
        return <CheckCircle className="w-5 h-5 text-success-500" />;
      case 'error':
        return <XCircle className="w-5 h-5 text-danger-500" />;
      default:
        return <XCircle className="w-5 h-5 text-surface-500" />;
    }
  };

  const getStatusText = (status: ProviderConfig['status']) => {
    switch (status) {
      case 'connected':
        return 'Connected';
      case 'error':
        return 'Error';
      default:
        return 'Not configured';
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Database className="w-5 h-5 text-primary-500" />
            <h3 className="text-lg font-semibold text-white">Data Providers</h3>
          </div>
          <p className="text-sm text-surface-400 mt-1">
            Configure your market data provider API keys
          </p>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {providers.map((provider) => (
              <div
                key={provider.key}
                className="p-4 bg-surface-700 rounded-lg space-y-4"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h4 className="font-medium text-white">{provider.name}</h4>
                    <p className="text-sm text-surface-400">{provider.description}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    {getStatusIcon(providerStatuses[provider.key])}
                    <span className={`text-sm ${
                      providerStatuses[provider.key] === 'connected'
                        ? 'text-success-500'
                        : providerStatuses[provider.key] === 'error'
                        ? 'text-danger-500'
                        : 'text-surface-400'
                    }`}>
                      {getStatusText(providerStatuses[provider.key])}
                    </span>
                  </div>
                </div>

                {provider.key !== 'yahoo' && (
                  <div className="flex gap-3">
                    <div className="flex-1">
                      <Input
                        type="password"
                        placeholder="Enter API key"
                        value={apiKeys[provider.key] || ''}
                        onChange={(e) => handleApiKeyChange(provider.key, e.target.value)}
                      />
                    </div>
                    <Button
                      onClick={() => handleSaveApiKey(provider.key)}
                      disabled={!apiKeys[provider.key] || savingProvider === provider.key}
                      variant="secondary"
                    >
                      {savingProvider === provider.key ? 'Saving...' : 'Save'}
                    </Button>
                    <Button
                      onClick={() => handleTestConnection(provider.key)}
                      disabled={testingProvider === provider.key}
                      variant="ghost"
                    >
                      <RefreshCw className={`w-4 h-4 ${testingProvider === provider.key ? 'animate-spin' : ''}`} />
                    </Button>
                  </div>
                )}

                {messages[provider.key]?.text && (
                  <p className={`text-sm ${
                    messages[provider.key].type === 'success'
                      ? 'text-success-500'
                      : 'text-danger-500'
                  }`}>
                    {messages[provider.key].text}
                  </p>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Data Provider Info */}
      <Card>
        <CardHeader>
          <h3 className="text-lg font-semibold text-white">Getting API Keys</h3>
        </CardHeader>
        <CardContent>
          <div className="space-y-3 text-sm text-surface-400">
            <p>
              <strong className="text-white">Alpha Vantage:</strong>{' '}
              Free tier available at{' '}
              <a href="https://www.alphavantage.co/support/#api-key" className="text-primary-400 hover:underline" target="_blank" rel="noopener noreferrer">
                alphavantage.co
              </a>
            </p>
            <p>
              <strong className="text-white">Finnhub:</strong>{' '}
              Free API key at{' '}
              <a href="https://finnhub.io/register" className="text-primary-400 hover:underline" target="_blank" rel="noopener noreferrer">
                finnhub.io
              </a>
            </p>
            <p>
              <strong className="text-white">Polygon.io:</strong>{' '}
              Sign up at{' '}
              <a href="https://polygon.io/pricing" className="text-primary-400 hover:underline" target="_blank" rel="noopener noreferrer">
                polygon.io
              </a>
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default DataProviderSettings;
