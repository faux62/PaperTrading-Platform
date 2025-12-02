/**
 * MLInsightsPanel Component
 * 
 * Main panel combining all ML insights
 */
import React, { useState } from 'react';
import { clsx } from 'clsx';
import { 
  Brain,
  Sparkles,
  Activity,
  BarChart3,
  RefreshCw,
  Settings,
} from 'lucide-react';
import { PredictionCard, PredictionDirection } from './PredictionCard';
import { SignalsList } from './SignalsList';
import { SignalType } from './SignalIndicator';
import { ModelPerformance } from './ModelPerformance';
import { FeatureImportance } from './FeatureImportance';

interface MLInsightsPanelProps {
  className?: string;
}

// Mock data types
interface TradingSignal {
  id: string;
  symbol: string;
  signal: SignalType;
  confidence: number;
  price: number;
  change24h: number;
  timestamp: Date;
  source: string;
}

// Mock data for demonstration
const mockPrediction = {
  symbol: 'AAPL',
  direction: 'bullish' as PredictionDirection,
  confidence: 0.78,
  predictedChange: 3.03,
  timeHorizon: '7 days',
};

const mockSignals: TradingSignal[] = [
  {
    id: '1',
    symbol: 'AAPL',
    signal: 'strong_buy',
    confidence: 0.85,
    price: 189.75,
    change24h: 2.3,
    timestamp: new Date(),
    source: 'LSTM-V2',
  },
  {
    id: '2',
    symbol: 'MSFT',
    signal: 'hold',
    confidence: 0.62,
    price: 374.50,
    change24h: -0.5,
    timestamp: new Date(Date.now() - 3600000),
    source: 'Transformer',
  },
  {
    id: '3',
    symbol: 'GOOGL',
    signal: 'sell',
    confidence: 0.71,
    price: 138.25,
    change24h: -1.8,
    timestamp: new Date(Date.now() - 7200000),
    source: 'LSTM-V2',
  },
  {
    id: '4',
    symbol: 'NVDA',
    signal: 'strong_buy',
    confidence: 0.92,
    price: 485.20,
    change24h: 4.2,
    timestamp: new Date(Date.now() - 10800000),
    source: 'Ensemble',
  },
];

const mockModelMetrics = {
  modelName: 'LSTM Price Predictor',
  version: '2.3.1',
  accuracy: 0.73,
  precision: 0.76,
  recall: 0.71,
  f1Score: 0.73,
  directionalAccuracy: 0.68,
  lastTrained: new Date(Date.now() - 86400000 * 3),
  totalPredictions: 15847,
  correctPredictions: 11568,
};

const mockFeatures = [
  { name: 'RSI (14)', importance: 0.142, category: 'technical' },
  { name: 'MACD Signal', importance: 0.128, category: 'technical' },
  { name: 'Volume Change', importance: 0.115, category: 'volume' },
  { name: 'Price Momentum', importance: 0.098, category: 'price' },
  { name: 'Bollinger %B', importance: 0.087, category: 'technical' },
  { name: 'SMA Cross', importance: 0.076, category: 'technical' },
  { name: 'ATR', importance: 0.065, category: 'technical' },
  { name: 'Volume SMA Ratio', importance: 0.054, category: 'volume' },
  { name: 'Price/SMA200', importance: 0.048, category: 'price' },
  { name: 'Sector Momentum', importance: 0.042, category: 'market' },
];

type Tab = 'overview' | 'signals' | 'models' | 'features';

export const MLInsightsPanel: React.FC<MLInsightsPanelProps> = ({
  className,
}) => {
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [loading, setLoading] = useState(false);

  const handleRefresh = () => {
    setLoading(true);
    setTimeout(() => setLoading(false), 1500);
  };

  const tabs: { id: Tab; label: string; icon: React.ElementType }[] = [
    { id: 'overview', label: 'Overview', icon: Brain },
    { id: 'signals', label: 'Signals', icon: Sparkles },
    { id: 'models', label: 'Models', icon: Activity },
    { id: 'features', label: 'Features', icon: BarChart3 },
  ];

  return (
    <div className={clsx('space-y-6', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-r from-purple-500 to-indigo-500 rounded-lg">
            <Brain className="w-6 h-6 text-white" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">
              ML Insights
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              AI-powered trading signals and predictions
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={handleRefresh}
            disabled={loading}
            className={clsx(
              'p-2 rounded-lg transition-colors',
              'hover:bg-gray-100 dark:hover:bg-gray-700',
              'disabled:opacity-50 disabled:cursor-not-allowed'
            )}
          >
            <RefreshCw className={clsx('w-5 h-5', loading && 'animate-spin')} />
          </button>
          <button className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
            <Settings className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={clsx(
              'flex items-center gap-2 flex-1 py-2 px-4 rounded-md text-sm font-medium transition-all',
              activeTab === tab.id
                ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
            )}
          >
            <tab.icon className="w-4 h-4" />
            <span className="hidden sm:inline">{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="min-h-[500px]">
        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <PredictionCard
              symbol={mockPrediction.symbol}
              direction={mockPrediction.direction}
              confidence={mockPrediction.confidence}
              predictedChange={mockPrediction.predictedChange}
              timeHorizon={mockPrediction.timeHorizon}
            />
            
            <ModelPerformance 
              metrics={mockModelMetrics} 
              loading={loading}
            />
            
            <div className="lg:col-span-2">
              <SignalsList 
                signals={mockSignals.slice(0, 3)} 
                loading={loading}
              />
            </div>
          </div>
        )}

        {/* Signals Tab */}
        {activeTab === 'signals' && (
          <SignalsList 
            signals={mockSignals} 
            loading={loading}
          />
        )}

        {/* Models Tab */}
        {activeTab === 'models' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <ModelPerformance 
              metrics={mockModelMetrics} 
              loading={loading}
            />
            <ModelPerformance 
              metrics={{
                ...mockModelMetrics,
                modelName: 'Transformer Predictor',
                version: '1.2.0',
                accuracy: 0.71,
                precision: 0.74,
                recall: 0.68,
                f1Score: 0.71,
                totalPredictions: 8432,
                correctPredictions: 5987,
              }} 
              loading={loading}
            />
            <ModelPerformance 
              metrics={{
                ...mockModelMetrics,
                modelName: 'Ensemble Model',
                version: '3.0.0',
                accuracy: 0.78,
                precision: 0.81,
                recall: 0.75,
                f1Score: 0.78,
                totalPredictions: 4521,
                correctPredictions: 3526,
              }} 
              loading={loading}
            />
          </div>
        )}

        {/* Features Tab */}
        {activeTab === 'features' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <FeatureImportance 
              features={mockFeatures} 
              title="LSTM Model Features"
              loading={loading}
            />
            <FeatureImportance 
              features={mockFeatures.map(f => ({
                ...f,
                importance: f.importance * (0.8 + Math.random() * 0.4)
              }))} 
              title="Transformer Model Features"
              loading={loading}
            />
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 pt-4 border-t border-gray-200 dark:border-gray-700">
        <span>
          Last updated: {new Date().toLocaleTimeString()}
        </span>
        <span>
          Models running on latest market data
        </span>
      </div>
    </div>
  );
};

export default MLInsightsPanel;
