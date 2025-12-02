/**
 * ModelDashboard Page
 * 
 * Comprehensive ML model performance dashboard
 */
import React, { useState } from 'react';
import { clsx } from 'clsx';
import { Layout } from '../components/layout';
import {
  Brain,
  Activity,
  Target,
  TrendingUp,
  RefreshCw,
  Download,
  Settings,
} from 'lucide-react';

import {
  ModelPerformance,
  ConfusionMatrix,
  ROCCurve,
  FeatureImportanceChart,
  BacktestResults,
} from '../components/ml';

// Mock data
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

const mockConfusionMatrix = {
  truePositive: 4532,
  falsePositive: 1423,
  trueNegative: 7036,
  falseNegative: 2856,
};

// Generate ROC curve data
const generateROCData = () => {
  const points = [];
  for (let i = 0; i <= 100; i += 5) {
    const fpr = i / 100;
    // Simulate a reasonably good model's TPR
    const tpr = Math.min(1, fpr + (1 - fpr) * (0.5 + Math.random() * 0.3));
    points.push({
      fpr,
      tpr,
      threshold: 1 - (i / 100),
    });
  }
  // Ensure endpoints
  points[0] = { fpr: 0, tpr: 0, threshold: 1 };
  points[points.length - 1] = { fpr: 1, tpr: 1, threshold: 0 };
  return points.sort((a, b) => a.fpr - b.fpr);
};

const mockROCData = generateROCData();

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
  { name: 'Market Volatility', importance: 0.038, category: 'market' },
  { name: 'Stochastic %K', importance: 0.035, category: 'technical' },
  { name: 'OBV Trend', importance: 0.032, category: 'volume' },
  { name: 'ADX', importance: 0.028, category: 'technical' },
  { name: 'CCI', importance: 0.024, category: 'technical' },
];

const mockBacktestMetrics = {
  totalReturn: 0.342,
  annualizedReturn: 0.182,
  sharpeRatio: 1.67,
  maxDrawdown: -0.128,
  winRate: 0.58,
  profitFactor: 1.89,
  totalTrades: 1247,
  avgTradeReturn: 0.0027,
  bestTrade: 0.089,
  worstTrade: -0.067,
  startDate: '2023-01-01',
  endDate: '2024-01-01',
};

type Tab = 'overview' | 'performance' | 'features' | 'backtest';

const ModelDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [selectedModel, setSelectedModel] = useState('lstm');
  const [loading, setLoading] = useState(false);

  const handleRefresh = () => {
    setLoading(true);
    setTimeout(() => setLoading(false), 1500);
  };

  const tabs: { id: Tab; label: string; icon: React.ElementType }[] = [
    { id: 'overview', label: 'Overview', icon: Brain },
    { id: 'performance', label: 'Model Performance', icon: Target },
    { id: 'features', label: 'Feature Analysis', icon: Activity },
    { id: 'backtest', label: 'Backtest Results', icon: TrendingUp },
  ];

  const models = [
    { id: 'lstm', name: 'LSTM Predictor v2.3' },
    { id: 'transformer', name: 'Transformer v1.2' },
    { id: 'ensemble', name: 'Ensemble v3.0' },
  ];

  return (
    <Layout>
      <div className="container mx-auto px-4 py-6 space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              Model Dashboard
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Monitor and analyze ML model performance
            </p>
          </div>
          
          <div className="flex items-center gap-3">
            {/* Model Selector */}
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-sm"
            >
              {models.map((model) => (
                <option key={model.id} value={model.id}>
                  {model.name}
                </option>
              ))}
            </select>
            
            <button
              onClick={handleRefresh}
              disabled={loading}
              className={clsx(
                'p-2 rounded-lg transition-colors border border-gray-300 dark:border-gray-600',
                'hover:bg-gray-100 dark:hover:bg-gray-700',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
            >
              <RefreshCw className={clsx('w-5 h-5', loading && 'animate-spin')} />
            </button>
            
            <button className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 border border-gray-300 dark:border-gray-600">
              <Download className="w-5 h-5" />
            </button>
            
            <button className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 border border-gray-300 dark:border-gray-600">
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
                'flex items-center gap-2 flex-1 py-2.5 px-4 rounded-md text-sm font-medium transition-all',
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
        <div className="min-h-[600px]">
          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <ModelPerformance 
                metrics={mockModelMetrics} 
                loading={loading}
              />
              
              <ConfusionMatrix 
                data={mockConfusionMatrix}
                loading={loading}
              />
              
              <ROCCurve 
                data={mockROCData}
                auc={0.82}
                loading={loading}
              />
              
              <FeatureImportanceChart 
                features={mockFeatures.slice(0, 8)}
                maxFeatures={8}
                height={280}
                loading={loading}
              />
            </div>
          )}

          {/* Model Performance Tab */}
          {activeTab === 'performance' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <ConfusionMatrix 
                data={mockConfusionMatrix}
                loading={loading}
              />
              
              <ROCCurve 
                data={mockROCData}
                auc={0.82}
                height={350}
                loading={loading}
              />
              
              <div className="lg:col-span-2">
                <ModelPerformance 
                  metrics={mockModelMetrics} 
                  loading={loading}
                />
              </div>
            </div>
          )}

          {/* Feature Analysis Tab */}
          {activeTab === 'features' && (
            <div className="space-y-6">
              <FeatureImportanceChart 
                features={mockFeatures}
                maxFeatures={15}
                height={500}
                loading={loading}
              />
            </div>
          )}

          {/* Backtest Results Tab */}
          {activeTab === 'backtest' && (
            <div className="space-y-6">
              <BacktestResults 
                metrics={mockBacktestMetrics}
                loading={loading}
              />
              
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <ModelPerformance 
                  metrics={mockModelMetrics} 
                  loading={loading}
                />
                
                <FeatureImportanceChart 
                  features={mockFeatures.slice(0, 8)}
                  maxFeatures={8}
                  height={300}
                  title="Top Features During Backtest"
                  loading={loading}
                />
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 pt-4 border-t border-gray-200 dark:border-gray-700">
          <span>Model: {models.find(m => m.id === selectedModel)?.name}</span>
          <span>Last updated: {new Date().toLocaleString()}</span>
        </div>
      </div>
    </Layout>
  );
};

export default ModelDashboard;
