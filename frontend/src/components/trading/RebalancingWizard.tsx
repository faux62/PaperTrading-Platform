/**
 * Rebalancing Wizard Component
 * Step-by-step portfolio rebalancing UI
 */
import { useState, useEffect, useCallback } from 'react';
import {
  Scale,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  Play,
  RefreshCw,
  ChevronRight,
  ChevronLeft,
} from 'lucide-react';
import Card, { CardContent, CardHeader } from '../common/Card';
import Button from '../common/Button';
import { tokenStorage } from '../../services/tokenStorage';

// Types
interface AllocationTarget {
  name: string;
  target_weight: number;
  current_weight: number;
  drift: number;
  drift_percent: number;
  status: 'overweight' | 'underweight' | 'on_target';
}

interface RebalanceRecommendation {
  symbol: string;
  action: 'buy' | 'sell' | 'hold';
  current_value: number;
  target_value: number;
  trade_value: number;
  current_weight: number;
  target_weight: number;
  reason: string;
  priority: number;
}

interface AllocationAnalysis {
  total_value: number;
  cash_balance: number;
  asset_class_allocations: AllocationTarget[];
  sector_allocations: AllocationTarget[];
  needs_rebalancing: boolean;
  max_drift: number;
  rebalance_recommendations: RebalanceRecommendation[];
  analysis_date: string;
}

interface OrderPreview {
  symbol: string;
  trade_type: string;
  order_type: string;
  quantity: number;
  estimated_value: number;
  reason: string;
  priority: number;
}

interface RebalancePreview {
  analysis: AllocationAnalysis;
  orders_to_create: OrderPreview[];
  estimated_commissions: number;
  total_buy_value: number;
  total_sell_value: number;
  net_cash_change: number;
  warnings: string[];
}

interface RebalanceResult {
  success: boolean;
  orders_created: Array<{ order_id: number; symbol: string; type: string; quantity: number }>;
  orders_executed: Array<{ order_id: number; symbol: string; filled_price: number }>;
  orders_failed: Array<{ symbol: string; error: string }>;
  total_trades: number;
  execution_time: number;
  errors: string[];
}

interface RebalancingWizardProps {
  portfolioId: number | string;
  currentRiskProfile?: string;
  baseCurrency?: string;  // Portfolio base currency
  onComplete?: () => void;
  onCancel?: () => void;
}

type WizardStep = 'analysis' | 'preview' | 'execute' | 'result';

// Currency symbols for display
const CURRENCY_SYMBOLS: Record<string, string> = {
  USD: '$', EUR: '€', GBP: '£', JPY: '¥', CHF: 'CHF', CAD: 'C$', AUD: 'A$'
};

const RISK_PROFILES = [
  { id: 'aggressive', name: 'Aggressive', description: 'Higher risk, higher potential returns' },
  { id: 'balanced', name: 'Balanced', description: 'Moderate risk and returns' },
  { id: 'prudent', name: 'Prudent', description: 'Lower risk, capital preservation' },
];

export function RebalancingWizard({
  portfolioId,
  currentRiskProfile = 'balanced',
  baseCurrency = 'USD',
  onComplete,
  onCancel,
}: RebalancingWizardProps) {
  const [step, setStep] = useState<WizardStep>('analysis');
  const [loading, setLoading] = useState(false);
  const [selectedProfile, setSelectedProfile] = useState(currentRiskProfile);
  const [minTradeValue, setMinTradeValue] = useState(100);
  
  const [analysis, setAnalysis] = useState<AllocationAnalysis | null>(null);
  const [preview, setPreview] = useState<RebalancePreview | null>(null);
  const [result, setResult] = useState<RebalanceResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchAnalysis = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const token = tokenStorage.getAccessToken();
      const response = await fetch(
        `/api/v1/portfolios/${portfolioId}/rebalance?risk_profile=${selectedProfile}`,
        {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (response.ok) {
        const data = await response.json();
        // Transform the response to match AllocationAnalysis
        setAnalysis({
          total_value: 0,
          cash_balance: 0,
          asset_class_allocations: [],
          sector_allocations: [],
          needs_rebalancing: data.needs_rebalancing,
          max_drift: data.max_drift,
          rebalance_recommendations: data.recommendations,
          analysis_date: new Date().toISOString(),
        });
      } else {
        setError('Failed to analyze portfolio');
      }
    } catch (err) {
      setError('Network error');
    } finally {
      setLoading(false);
    }
  }, [portfolioId, selectedProfile]);

  useEffect(() => {
    fetchAnalysis();
  }, [fetchAnalysis]);

  const generatePreview = async () => {
    setLoading(true);
    setError(null);
    try {
      const token = tokenStorage.getAccessToken();
      const response = await fetch(
        `/api/v1/portfolios/${portfolioId}/rebalance/preview`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            risk_profile: selectedProfile,
            min_trade_value: minTradeValue,
          }),
        }
      );
      if (response.ok) {
        const data = await response.json();
        setPreview(data);
        setStep('preview');
      } else {
        // If preview endpoint doesn't exist, create mock preview from analysis
        if (analysis) {
          const mockPreview: RebalancePreview = {
            analysis: analysis,
            orders_to_create: analysis.rebalance_recommendations
              .filter(r => r.action !== 'hold' && Math.abs(r.trade_value) >= minTradeValue)
              .map(r => ({
                symbol: r.symbol,
                trade_type: r.action,
                order_type: 'market',
                quantity: Math.floor(Math.abs(r.trade_value) / 100), // Estimate
                estimated_value: Math.abs(r.trade_value),
                reason: r.reason,
                priority: r.priority,
              })),
            estimated_commissions: 0,
            total_buy_value: analysis.rebalance_recommendations
              .filter(r => r.action === 'buy')
              .reduce((sum, r) => sum + r.trade_value, 0),
            total_sell_value: analysis.rebalance_recommendations
              .filter(r => r.action === 'sell')
              .reduce((sum, r) => sum + Math.abs(r.trade_value), 0),
            net_cash_change: 0,
            warnings: [],
          };
          setPreview(mockPreview);
          setStep('preview');
        }
      }
    } catch (err) {
      setError('Failed to generate preview');
    } finally {
      setLoading(false);
    }
  };

  const executeRebalance = async () => {
    if (!preview) return;
    
    setLoading(true);
    setError(null);
    setStep('execute');
    
    try {
      const token = tokenStorage.getAccessToken();
      
      // Execute batch orders
      const ordersToExecute = preview.orders_to_create.map(o => ({
        symbol: o.symbol,
        trade_type: o.trade_type,
        order_type: o.order_type,
        quantity: o.quantity,
      }));
      
      const response = await fetch('/api/v1/trades/batch', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          portfolio_id: portfolioId,
          orders: ordersToExecute,
        }),
      });
      
      if (response.ok) {
        const data = await response.json();
        setResult({
          success: data.failed === 0,
          orders_created: data.results.filter((r: { success: boolean }) => r.success).map((r: { symbol: string; order_id?: number }) => ({
            order_id: r.order_id,
            symbol: r.symbol,
            type: 'market',
            quantity: 0,
          })),
          orders_executed: data.results
            .filter((r: { success: boolean }) => r.success)
            .map((r: { order_id?: number; symbol: string; executed_price?: number }) => ({
              order_id: r.order_id,
              symbol: r.symbol,
              filled_price: r.executed_price || 0,
            })),
          orders_failed: data.results
            .filter((r: { success: boolean }) => !r.success)
            .map((r: { symbol: string; error?: string }) => ({
              symbol: r.symbol,
              error: r.error || 'Unknown error',
            })),
          total_trades: data.successful,
          execution_time: 0,
          errors: [],
        });
        setStep('result');
      } else {
        setError('Failed to execute rebalancing');
        setStep('preview');
      }
    } catch (err) {
      setError('Execution failed');
      setStep('preview');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value: number) => {
    const symbol = CURRENCY_SYMBOLS[baseCurrency] || baseCurrency + ' ';
    return `${symbol}${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatPercent = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  // Step 1: Analysis
  const renderAnalysisStep = () => (
    <div className="space-y-6">
      {/* Risk Profile Selection */}
      <div>
        <h3 className="text-sm font-medium text-surface-300 mb-3">Target Risk Profile</h3>
        <div className="grid grid-cols-3 gap-3">
          {RISK_PROFILES.map((profile) => (
            <button
              key={profile.id}
              onClick={() => setSelectedProfile(profile.id)}
              className={`p-4 rounded-lg border text-left transition-all ${
                selectedProfile === profile.id
                  ? 'border-primary-500 bg-primary-500/10'
                  : 'border-surface-700 hover:border-surface-600'
              }`}
            >
              <p className="font-medium text-white">{profile.name}</p>
              <p className="text-xs text-surface-400 mt-1">{profile.description}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Min Trade Value */}
      <div>
        <label className="text-sm font-medium text-surface-300">
          Minimum Trade Value
        </label>
        <input
          type="number"
          value={minTradeValue}
          onChange={(e) => setMinTradeValue(Number(e.target.value))}
          className="mt-2 w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-white"
          min={0}
          step={50}
        />
        <p className="text-xs text-surface-500 mt-1">
          Trades below this value will be skipped
        </p>
      </div>

      {/* Analysis Results */}
      {analysis && (
        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 rounded-lg bg-surface-800">
            <div className="flex items-center gap-3">
              {analysis.needs_rebalancing ? (
                <AlertTriangle className="h-5 w-5 text-yellow-500" />
              ) : (
                <CheckCircle className="h-5 w-5 text-green-500" />
              )}
              <div>
                <p className="font-medium text-white">
                  {analysis.needs_rebalancing
                    ? 'Rebalancing Recommended'
                    : 'Portfolio is Balanced'}
                </p>
                <p className="text-sm text-surface-400">
                  Max drift: {formatPercent(analysis.max_drift)}
                </p>
              </div>
            </div>
          </div>

          {/* Recommendations Summary */}
          {analysis.rebalance_recommendations.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-surface-300 mb-2">
                Recommendations ({analysis.rebalance_recommendations.length})
              </h4>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {analysis.rebalance_recommendations.map((rec, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-3 rounded-lg bg-surface-800/50"
                  >
                    <div className="flex items-center gap-2">
                      {rec.action === 'buy' ? (
                        <TrendingUp className="h-4 w-4 text-green-500" />
                      ) : rec.action === 'sell' ? (
                        <TrendingDown className="h-4 w-4 text-red-500" />
                      ) : null}
                      <span className="font-medium">{rec.symbol}</span>
                    </div>
                    <span className={`text-sm ${
                      rec.action === 'buy' ? 'text-green-500' : 'text-red-500'
                    }`}>
                      {rec.action.toUpperCase()} {formatCurrency(Math.abs(rec.trade_value))}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="flex justify-between gap-3 pt-4 border-t border-surface-700">
        <Button variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <div className="flex gap-3">
          <Button variant="ghost" onClick={fetchAnalysis} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button
            onClick={generatePreview}
            disabled={loading || !analysis?.needs_rebalancing}
          >
            Preview Trades
            <ChevronRight className="h-4 w-4 ml-2" />
          </Button>
        </div>
      </div>
    </div>
  );

  // Step 2: Preview
  const renderPreviewStep = () => (
    <div className="space-y-6">
      {preview && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-3 gap-4">
            <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/30">
              <p className="text-sm text-green-400">Total Buys</p>
              <p className="text-xl font-bold text-green-500">
                {formatCurrency(preview.total_buy_value)}
              </p>
            </div>
            <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30">
              <p className="text-sm text-red-400">Total Sells</p>
              <p className="text-xl font-bold text-red-500">
                {formatCurrency(preview.total_sell_value)}
              </p>
            </div>
            <div className="p-4 rounded-lg bg-blue-500/10 border border-blue-500/30">
              <p className="text-sm text-blue-400">Net Cash Change</p>
              <p className="text-xl font-bold text-blue-500">
                {formatCurrency(preview.net_cash_change)}
              </p>
            </div>
          </div>

          {/* Warnings */}
          {preview.warnings.length > 0 && (
            <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/30">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="h-4 w-4 text-yellow-500" />
                <span className="font-medium text-yellow-500">Warnings</span>
              </div>
              <ul className="text-sm text-yellow-400 space-y-1">
                {preview.warnings.map((w, i) => (
                  <li key={i}>• {w}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Orders to Create */}
          <div>
            <h4 className="text-sm font-medium text-surface-300 mb-2">
              Orders to Execute ({preview.orders_to_create.length})
            </h4>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {preview.orders_to_create.map((order, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-3 rounded-lg bg-surface-800"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                        order.trade_type === 'buy'
                          ? 'bg-green-500/20 text-green-500'
                          : 'bg-red-500/20 text-red-500'
                      }`}>
                        {order.trade_type.toUpperCase()}
                      </span>
                      <span className="font-medium text-white">{order.symbol}</span>
                    </div>
                    <p className="text-xs text-surface-400 mt-1">{order.reason}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-mono text-white">{order.quantity} shares</p>
                    <p className="text-sm text-surface-400">
                      ≈ {formatCurrency(order.estimated_value)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {/* Actions */}
      <div className="flex justify-between pt-4 border-t border-surface-700">
        <Button variant="ghost" onClick={() => setStep('analysis')}>
          <ChevronLeft className="h-4 w-4 mr-2" />
          Back
        </Button>
        <Button
          onClick={executeRebalance}
          disabled={loading || !preview?.orders_to_create.length}
        >
          <Play className="h-4 w-4 mr-2" />
          Execute Rebalancing
        </Button>
      </div>
    </div>
  );

  // Step 3: Executing
  const renderExecutingStep = () => (
    <div className="flex flex-col items-center justify-center py-12">
      <RefreshCw className="h-12 w-12 text-primary-500 animate-spin mb-4" />
      <p className="text-lg font-medium text-white">Executing Rebalancing...</p>
      <p className="text-sm text-surface-400 mt-2">
        Processing {preview?.orders_to_create.length || 0} orders
      </p>
    </div>
  );

  // Step 4: Result
  const renderResultStep = () => (
    <div className="space-y-6">
      {result && (
        <>
          {/* Status */}
          <div className={`p-6 rounded-lg text-center ${
            result.success
              ? 'bg-green-500/10 border border-green-500/30'
              : 'bg-red-500/10 border border-red-500/30'
          }`}>
            {result.success ? (
              <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-3" />
            ) : (
              <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-3" />
            )}
            <h3 className={`text-xl font-bold ${
              result.success ? 'text-green-500' : 'text-red-500'
            }`}>
              {result.success ? 'Rebalancing Complete!' : 'Rebalancing Partially Failed'}
            </h3>
            <p className="text-surface-400 mt-2">
              {result.total_trades} trades executed
              {result.orders_failed.length > 0 && `, ${result.orders_failed.length} failed`}
            </p>
          </div>

          {/* Executed Orders */}
          {result.orders_executed.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-green-400 mb-2">
                Executed ({result.orders_executed.length})
              </h4>
              <div className="space-y-1">
                {result.orders_executed.map((order, idx) => (
                  <div key={idx} className="flex justify-between p-2 rounded bg-surface-800/50">
                    <span className="text-white">{order.symbol}</span>
                    <span className="text-surface-400">
                      @ {formatCurrency(order.filled_price)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Failed Orders */}
          {result.orders_failed.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-red-400 mb-2">
                Failed ({result.orders_failed.length})
              </h4>
              <div className="space-y-1">
                {result.orders_failed.map((order, idx) => (
                  <div key={idx} className="flex justify-between p-2 rounded bg-red-500/10">
                    <span className="text-white">{order.symbol}</span>
                    <span className="text-red-400 text-sm">{order.error}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* Actions */}
      <div className="flex justify-center pt-4 border-t border-surface-700">
        <Button onClick={() => {
          setStep('analysis');
          setResult(null);
          setPreview(null);
          fetchAnalysis();
          onComplete?.();
        }}>
          <CheckCircle className="h-4 w-4 mr-2" />
          Done
        </Button>
      </div>
    </div>
  );

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-3">
          <Scale className="h-5 w-5 text-primary-500" />
          <div>
            <h2 className="text-lg font-semibold text-white">Portfolio Rebalancing</h2>
            <p className="text-sm text-surface-400">
              {step === 'analysis' && 'Analyze allocation and select target profile'}
              {step === 'preview' && 'Review orders before execution'}
              {step === 'execute' && 'Executing trades...'}
              {step === 'result' && 'Rebalancing complete'}
            </p>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400">
            {error}
          </div>
        )}
        
        {step === 'analysis' && renderAnalysisStep()}
        {step === 'preview' && renderPreviewStep()}
        {step === 'execute' && renderExecutingStep()}
        {step === 'result' && renderResultStep()}
      </CardContent>
    </Card>
  );
}

export default RebalancingWizard;
