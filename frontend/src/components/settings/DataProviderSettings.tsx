/**
 * Data Provider Settings Component
 * Configure API keys for market data providers
 */
import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, Button, Input } from '../common';
import { Database, CheckCircle, XCircle, RefreshCw, Download } from 'lucide-react';
import { settingsApi } from '../../services/api';

interface ProviderConfig {
  name: string;
  key: string;
  description: string;
  enabled: boolean;
  status: 'connected' | 'disconnected' | 'error';
  maskedKey?: string;
  source?: 'personal' | 'system' | 'environment' | null;  // Where the key comes from
  isPersonal?: boolean;  // True if user has their own key
}

interface DataProviderSettingsProps {
  providers?: ProviderConfig[];
  onSaveProvider?: (provider: string, apiKey: string) => Promise<void>;
  onTestConnection?: (provider: string) => Promise<boolean>;
}

const DEFAULT_PROVIDERS: ProviderConfig[] = [
  // US Market Primary
  {
    name: 'Alpaca Markets',
    key: 'alpaca',
    description: 'WebSocket streaming for US stocks (real-time)',
    enabled: true,
    status: 'disconnected',
  },
  {
    name: 'Alpaca Secret Key',
    key: 'alpaca_secret',
    description: 'Secret key for Alpaca authentication',
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
  // Global Coverage
  {
    name: 'Finnhub',
    key: 'finnhub',
    description: '60+ exchanges, REST + WebSocket (recommended)',
    enabled: true,
    status: 'disconnected',
  },
  {
    name: 'Twelve Data',
    key: 'twelvedata',
    description: 'Batch queries up to 120 symbols',
    enabled: true,
    status: 'disconnected',
  },
  // Historical Data
  {
    name: 'EODHD',
    key: 'eodhd',
    description: 'Bulk API for end-of-day data',
    enabled: true,
    status: 'disconnected',
  },
  // Fundamentals
  {
    name: 'Financial Modeling Prep',
    key: 'fmp',
    description: 'Fundamental data and financial statements',
    enabled: true,
    status: 'disconnected',
  },
  {
    name: 'Alpha Vantage',
    key: 'alphavantage',
    description: 'Technical indicators and time series',
    enabled: true,
    status: 'disconnected',
  },
  // Additional Providers
  {
    name: 'Nasdaq Data Link',
    key: 'nasdaq',
    description: 'Ex-Quandl financial datasets',
    enabled: true,
    status: 'disconnected',
  },
  {
    name: 'Tiingo',
    key: 'tiingo',
    description: 'IEX data and crypto prices',
    enabled: true,
    status: 'disconnected',
  },
  {
    name: 'Marketstack',
    key: 'marketstack',
    description: 'Global stock exchange data',
    enabled: true,
    status: 'disconnected',
  },
  {
    name: 'StockData.org',
    key: 'stockdata',
    description: 'Stock market data API',
    enabled: true,
    status: 'disconnected',
  },
  {
    name: 'Intrinio',
    key: 'intrinio',
    description: 'Financial data and analytics',
    enabled: true,
    status: 'disconnected',
  },
  // No API Key Required
  {
    name: 'yfinance',
    key: 'yfinance',
    description: 'Yahoo Finance scraping (no key needed)',
    enabled: true,
    status: 'disconnected',
  },
  {
    name: 'Stooq',
    key: 'stooq',
    description: 'CSV download (no key needed)',
    enabled: true,
    status: 'disconnected',
  },
  {
    name: 'Investing.com',
    key: 'investingcom',
    description: 'investpy scraping (no key needed)',
    enabled: true,
    status: 'disconnected',
  },
];

export const DataProviderSettings: React.FC<DataProviderSettingsProps> = () => {
  const [providers, setProviders] = useState<ProviderConfig[]>(DEFAULT_PROVIDERS);
  const [apiKeys, setApiKeys] = useState<Record<string, string>>({});
  const [testingProvider, setTestingProvider] = useState<string | null>(null);
  const [savingProvider, setSavingProvider] = useState<string | null>(null);
  const [importingFromEnv, setImportingFromEnv] = useState(false);
  const [importMessage, setImportMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [messages, setMessages] = useState<Record<string, { type: 'success' | 'error'; text: string }>>({});

  // Load saved API keys on mount
  useEffect(() => {
    const loadSettings = async () => {
      try {
        const settings = await settingsApi.getSettings();
        if (settings.api_keys) {
          const updatedProviders = providers.map(p => {
            const savedKey = settings.api_keys.find((k: { 
              provider: string; 
              configured: boolean; 
              masked_key?: string;
              source?: string;
              is_personal?: boolean;
            }) => k.provider === p.key);
            return {
              ...p,
              status: savedKey?.configured ? 'connected' as const : 'disconnected' as const,
              maskedKey: savedKey?.masked_key,
              source: savedKey?.source as ProviderConfig['source'],
              isPersonal: savedKey?.is_personal || false,
            };
          });
          setProviders(updatedProviders);
        }
      } catch (error) {
        console.error('Failed to load settings:', error);
      }
    };
    loadSettings();
  }, []);

  const handleImportFromEnv = async () => {
    setImportingFromEnv(true);
    setImportMessage(null);
    try {
      const result = await settingsApi.importFromEnv();
      setImportMessage({
        type: 'success',
        text: `${result.message}. Imported: ${result.imported.join(', ') || 'none'}`,
      });
      // Reload settings to update UI
      const settings = await settingsApi.getSettings();
      if (settings.api_keys) {
        const updatedProviders = providers.map(p => {
          const savedKey = settings.api_keys.find((k: { 
            provider: string; 
            configured: boolean; 
            masked_key?: string;
            source?: string;
            is_personal?: boolean;
          }) => k.provider === p.key);
          return {
            ...p,
            status: savedKey?.configured ? 'connected' as const : 'disconnected' as const,
            maskedKey: savedKey?.masked_key,
            source: savedKey?.source as ProviderConfig['source'],
            isPersonal: savedKey?.is_personal || false,
          };
        });
        setProviders(updatedProviders);
      }
    } catch (error) {
      setImportMessage({ type: 'error', text: 'Failed to import API keys from environment' });
    } finally {
      setImportingFromEnv(false);
    }
  };

  const handleApiKeyChange = (providerKey: string, value: string) => {
    setApiKeys(prev => ({ ...prev, [providerKey]: value }));
  };

  const handleTestConnection = async (providerKey: string) => {
    setTestingProvider(providerKey);
    setMessages(prev => ({ ...prev, [providerKey]: { type: 'success', text: '' } }));

    try {
      const result = await settingsApi.testConnection(providerKey);
      setProviders(prev => prev.map(p => 
        p.key === providerKey 
          ? { ...p, status: result.success ? 'connected' : 'error' }
          : p
      ));
      setMessages(prev => ({
        ...prev,
        [providerKey]: {
          type: result.success ? 'success' : 'error',
          text: result.message,
        },
      }));
    } catch {
      setProviders(prev => prev.map(p => 
        p.key === providerKey ? { ...p, status: 'error' } : p
      ));
      setMessages(prev => ({
        ...prev,
        [providerKey]: { type: 'error', text: 'Connection test failed' },
      }));
    } finally {
      setTestingProvider(null);
    }
  };

  const handleSaveApiKey = async (providerKey: string) => {
    const apiKey = apiKeys[providerKey];
    if (!apiKey) return;

    setSavingProvider(providerKey);
    try {
      const result = await settingsApi.saveApiKey(providerKey, apiKey);
      setProviders(prev => prev.map(p => 
        p.key === providerKey 
          ? { ...p, status: 'connected', maskedKey: result.masked_key }
          : p
      ));
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

  const getStatusText = (status: ProviderConfig['status'], source?: ProviderConfig['source']) => {
    if (status !== 'connected') {
      return status === 'error' ? 'Error' : 'Not configured';
    }
    // Show source when connected
    switch (source) {
      case 'personal':
        return 'Personal key';
      case 'system':
        return 'System key';
      case 'environment':
        return 'Environment';
      default:
        return 'Connected';
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Database className="w-5 h-5 text-primary-500" />
              <h3 className="text-lg font-semibold text-white">Data Providers</h3>
            </div>
            <Button
              onClick={handleImportFromEnv}
              disabled={importingFromEnv}
              variant="secondary"
              className="flex items-center gap-2"
            >
              <Download className="w-4 h-4" />
              {importingFromEnv ? 'Importing...' : 'Import from Server Config'}
            </Button>
          </div>
          <p className="text-sm text-surface-400 mt-1">
            Configure your market data provider API keys. You can import existing keys from the server configuration.
          </p>
          {importMessage && (
            <p className={`text-sm mt-2 ${importMessage.type === 'success' ? 'text-success-500' : 'text-danger-500'}`}>
              {importMessage.text}
            </p>
          )}
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
                    {provider.maskedKey && (
                      <p className="text-xs text-surface-500 mt-1">
                        Current key: {provider.maskedKey}
                      </p>
                    )}
                    {provider.status === 'connected' && provider.source && provider.source !== 'personal' && (
                      <p className="text-xs text-primary-400 mt-1">
                        💡 You can override with your own key for separate rate limits
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {getStatusIcon(provider.status)}
                    <span className={`text-sm ${
                      provider.status === 'connected'
                        ? provider.source === 'personal' 
                          ? 'text-success-500' 
                          : 'text-primary-400'
                        : provider.status === 'error'
                        ? 'text-danger-500'
                        : 'text-surface-400'
                    }`}>
                      {getStatusText(provider.status, provider.source)}
                    </span>
                  </div>
                </div>

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
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-surface-400">
            <div className="space-y-2">
              <p>
                <strong className="text-white">Alpaca Markets:</strong>{' '}
                <a href="https://alpaca.markets/" className="text-primary-400 hover:underline" target="_blank" rel="noopener noreferrer">
                  alpaca.markets
                </a>
              </p>
              <p>
                <strong className="text-white">Polygon.io:</strong>{' '}
                <a href="https://polygon.io/pricing" className="text-primary-400 hover:underline" target="_blank" rel="noopener noreferrer">
                  polygon.io
                </a>
              </p>
              <p>
                <strong className="text-white">Finnhub:</strong>{' '}
                <a href="https://finnhub.io/register" className="text-primary-400 hover:underline" target="_blank" rel="noopener noreferrer">
                  finnhub.io
                </a>
              </p>
              <p>
                <strong className="text-white">Twelve Data:</strong>{' '}
                <a href="https://twelvedata.com/" className="text-primary-400 hover:underline" target="_blank" rel="noopener noreferrer">
                  twelvedata.com
                </a>
              </p>
              <p>
                <strong className="text-white">EODHD:</strong>{' '}
                <a href="https://eodhd.com/" className="text-primary-400 hover:underline" target="_blank" rel="noopener noreferrer">
                  eodhd.com
                </a>
              </p>
              <p>
                <strong className="text-white">FMP:</strong>{' '}
                <a href="https://financialmodelingprep.com/" className="text-primary-400 hover:underline" target="_blank" rel="noopener noreferrer">
                  financialmodelingprep.com
                </a>
              </p>
            </div>
            <div className="space-y-2">
              <p>
                <strong className="text-white">Alpha Vantage:</strong>{' '}
                <a href="https://www.alphavantage.co/support/#api-key" className="text-primary-400 hover:underline" target="_blank" rel="noopener noreferrer">
                  alphavantage.co
                </a>
              </p>
              <p>
                <strong className="text-white">Nasdaq Data Link:</strong>{' '}
                <a href="https://data.nasdaq.com/" className="text-primary-400 hover:underline" target="_blank" rel="noopener noreferrer">
                  data.nasdaq.com
                </a>
              </p>
              <p>
                <strong className="text-white">Tiingo:</strong>{' '}
                <a href="https://www.tiingo.com/" className="text-primary-400 hover:underline" target="_blank" rel="noopener noreferrer">
                  tiingo.com
                </a>
              </p>
              <p>
                <strong className="text-white">Marketstack:</strong>{' '}
                <a href="https://marketstack.com/" className="text-primary-400 hover:underline" target="_blank" rel="noopener noreferrer">
                  marketstack.com
                </a>
              </p>
              <p>
                <strong className="text-white">StockData.org:</strong>{' '}
                <a href="https://www.stockdata.org/" className="text-primary-400 hover:underline" target="_blank" rel="noopener noreferrer">
                  stockdata.org
                </a>
              </p>
              <p>
                <strong className="text-white">Intrinio:</strong>{' '}
                <a href="https://intrinio.com/" className="text-primary-400 hover:underline" target="_blank" rel="noopener noreferrer">
                  intrinio.com
                </a>
              </p>
            </div>
          </div>
          <p className="text-xs text-surface-500 mt-4">
            Note: yfinance, Stooq, and Investing.com do not require API keys.
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export default DataProviderSettings;
