/**
 * TradeCandidatesPanel Component
 * 
 * Display automatically identified trade candidates for the day with
 * full trading parameters (entry, stop-loss, take-profit, position sizing).
 * 
 * Implements FASE 1 of GUIDA-OPERATIVA-GIORNALIERA.md:
 * - Pre-Apertura (07:00 - 09:00)
 * - Automatic identification of 3-5 daily candidates
 * - Order preparation with all trading parameters
 */
import React, { useState, useEffect } from 'react';
import { clsx } from 'clsx';
import {
  Target,
  TrendingUp,
  TrendingDown,
  Shield,
  DollarSign,
  AlertTriangle,
  RefreshCw,
  ChevronRight,
  BarChart3,
  Minus,
} from 'lucide-react';

interface TradeCandidate {
  symbol: string;
  region: string;
  signal: string;
  confidence: number;
  current_price: number;
  currency: string;
  entry_price: number;
  stop_loss: number;
  stop_loss_percent: number;
  take_profit: number;
  take_profit_percent: number;
  max_position_value: number;
  suggested_shares: number;
  risk_reward_ratio: number;
  trend: string;
  volatility: string | null;
  ranking: number;
}

interface TradeCandidatesResponse {
  date: string;
  portfolio_value: number;
  portfolio_currency: string;
  max_position_percent: number;
  candidates: TradeCandidate[];
  eu_candidates: number;
  us_candidates: number;
  generated_at: string;
}

interface TradeCandidatesPanelProps {
  portfolioId: number;
  className?: string;
  onSelectCandidate?: (candidate: TradeCandidate) => void;
}

const TrendIcon: React.FC<{ trend: string }> = ({ trend }) => {
  switch (trend.toUpperCase()) {
    case 'UP':
      return <TrendingUp className="h-4 w-4 text-green-500" />;
    case 'DOWN':
      return <TrendingDown className="h-4 w-4 text-red-500" />;
    default:
      return <Minus className="h-4 w-4 text-gray-400" />;
  }
};

const formatCurrency = (value: number, currency: string): string => {
  return new Intl.NumberFormat('it-IT', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 2,
  }).format(value);
};

// formatPercent available for future use
// const formatPercent = (value: number): string => {
//   return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
// };

export const TradeCandidatesPanel: React.FC<TradeCandidatesPanelProps> = ({
  portfolioId,
  className,
  onSelectCandidate,
}) => {
  const [data, setData] = useState<TradeCandidatesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [regionFilter, setRegionFilter] = useState<'all' | 'eu' | 'us'>('all');

  const fetchCandidates = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(
        `/api/v1/ml/trade-candidates/${portfolioId}?region=${regionFilter}&min_confidence=60&max_candidates=5`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }
      );
      
      if (!response.ok) {
        throw new Error(`Error ${response.status}: ${response.statusText}`);
      }
      
      const result = await response.json();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load candidates');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCandidates();
  }, [portfolioId, regionFilter]);

  if (loading) {
    return (
      <div className={clsx('bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6', className)}>
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/3" />
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-24 bg-gray-200 dark:bg-gray-700 rounded" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={clsx('bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6', className)}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Target className="h-5 w-5 text-blue-500" />
            Trade Candidates
          </h3>
        </div>
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <div className="flex items-center gap-2 text-red-700 dark:text-red-400">
            <AlertTriangle className="h-5 w-5" />
            <span>{error}</span>
          </div>
          <button
            onClick={fetchCandidates}
            className="mt-2 text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1"
          >
            <RefreshCw className="h-4 w-4" /> Riprova
          </button>
        </div>
      </div>
    );
  }

  const candidates = data?.candidates || [];

  return (
    <div className={clsx('bg-white dark:bg-gray-800 rounded-xl shadow-lg', className)}>
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Target className="h-5 w-5 text-blue-500" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Trade Candidates
            </h3>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              {data?.date}
            </span>
          </div>
          
          <div className="flex items-center gap-2">
            {/* Region Filter */}
            <select
              value={regionFilter}
              onChange={(e) => setRegionFilter(e.target.value as 'all' | 'eu' | 'us')}
              className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg 
                         bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200"
            >
              <option value="all">🌍 All Regions</option>
              <option value="eu">🇪🇺 Europe</option>
              <option value="us">🇺🇸 USA</option>
            </select>
            
            <button
              onClick={fetchCandidates}
              className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200
                         hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              title="Aggiorna candidati"
            >
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>
        </div>
        
        {/* Summary Stats */}
        {data && (
          <div className="mt-3 flex items-center gap-4 text-sm text-gray-600 dark:text-gray-400">
            <span>
              Portfolio: {formatCurrency(data.portfolio_value, data.portfolio_currency)}
            </span>
            <span>•</span>
            <span>Max Position: {data.max_position_percent}%</span>
            <span>•</span>
            <span>🇪🇺 {data.eu_candidates} EU</span>
            <span>•</span>
            <span>🇺🇸 {data.us_candidates} US</span>
          </div>
        )}
      </div>

      {/* Candidates List */}
      <div className="divide-y divide-gray-200 dark:divide-gray-700">
        {candidates.length === 0 ? (
          <div className="p-8 text-center text-gray-500 dark:text-gray-400">
            <BarChart3 className="h-12 w-12 mx-auto mb-3 opacity-30" />
            <p className="font-medium">Nessun candidato trovato</p>
            <p className="text-sm mt-1">
              Nessun segnale BUY con confidence {'>'} 60% per la regione selezionata
            </p>
          </div>
        ) : (
          candidates.map((candidate) => (
            <div
              key={candidate.symbol}
              className="p-4 border-l-4 border-l-transparent hover:border-l-blue-500 
                         hover:bg-blue-50/20 dark:hover:bg-blue-900/10 cursor-pointer
                         [transition:border-color_0s,background-color_0.15s]"
              onClick={() => onSelectCandidate?.(candidate)}
            >
              {/* Top Row: Symbol, Signal, Confidence */}
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <span className="bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 
                                   text-xs font-bold px-2 py-1 rounded">
                    #{candidate.ranking}
                  </span>
                  <div>
                    <span className="font-semibold text-gray-900 dark:text-white text-lg">
                      {candidate.symbol}
                    </span>
                    <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
                      {candidate.region}
                    </span>
                  </div>
                  <TrendIcon trend={candidate.trend} />
                </div>
                
                <div className="flex items-center gap-2">
                  <span className={clsx(
                    'px-3 py-1 rounded-full text-sm font-semibold',
                    candidate.signal === 'BUY' || candidate.signal === 'STRONG_BUY'
                      ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                      : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                  )}>
                    {candidate.signal}
                  </span>
                  <span className="text-lg font-bold text-gray-900 dark:text-white">
                    {candidate.confidence.toFixed(0)}%
                  </span>
                </div>
              </div>

              {/* Trading Parameters Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                {/* Entry Price */}
                <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-2">
                  <div className="text-gray-500 dark:text-gray-400 text-xs mb-1">
                    Entry (Limit)
                  </div>
                  <div className="font-semibold text-gray-900 dark:text-white">
                    {formatCurrency(candidate.entry_price, candidate.currency)}
                  </div>
                  <div className="text-xs text-gray-500">
                    Current: {formatCurrency(candidate.current_price, candidate.currency)}
                  </div>
                </div>

                {/* Stop-Loss */}
                <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-2">
                  <div className="text-red-600 dark:text-red-400 text-xs mb-1 flex items-center gap-1">
                    <Shield className="h-3 w-3" /> Stop-Loss
                  </div>
                  <div className="font-semibold text-red-700 dark:text-red-400">
                    {formatCurrency(candidate.stop_loss, candidate.currency)}
                  </div>
                  <div className="text-xs text-red-600 dark:text-red-400">
                    -{candidate.stop_loss_percent}%
                  </div>
                </div>

                {/* Take-Profit */}
                <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-2">
                  <div className="text-green-600 dark:text-green-400 text-xs mb-1 flex items-center gap-1">
                    <Target className="h-3 w-3" /> Take-Profit
                  </div>
                  <div className="font-semibold text-green-700 dark:text-green-400">
                    {formatCurrency(candidate.take_profit, candidate.currency)}
                  </div>
                  <div className="text-xs text-green-600 dark:text-green-400">
                    +{candidate.take_profit_percent.toFixed(1)}%
                  </div>
                </div>

                {/* Position Size */}
                <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-2">
                  <div className="text-blue-600 dark:text-blue-400 text-xs mb-1 flex items-center gap-1">
                    <DollarSign className="h-3 w-3" /> Position
                  </div>
                  <div className="font-semibold text-blue-700 dark:text-blue-400">
                    {candidate.suggested_shares} shares
                  </div>
                  <div className="text-xs text-blue-600 dark:text-blue-400">
                    {formatCurrency(candidate.max_position_value, candidate.currency)}
                  </div>
                </div>
              </div>

              {/* Bottom Row: Risk/Reward & Volatility */}
              <div className="mt-3 flex items-center justify-between text-sm">
                <div className="flex items-center gap-4">
                  <span className="text-gray-600 dark:text-gray-400">
                    R/R Ratio: 
                    <span className={clsx(
                      'ml-1 font-semibold',
                      candidate.risk_reward_ratio >= 2 
                        ? 'text-green-600 dark:text-green-400' 
                        : 'text-yellow-600 dark:text-yellow-400'
                    )}>
                      1:{candidate.risk_reward_ratio}
                    </span>
                  </span>
                  {candidate.volatility && (
                    <span className="text-gray-600 dark:text-gray-400">
                      Volatility: 
                      <span className={clsx(
                        'ml-1 font-medium',
                        candidate.volatility === 'HIGH' 
                          ? 'text-red-500' 
                          : 'text-green-500'
                      )}>
                        {candidate.volatility}
                      </span>
                    </span>
                  )}
                </div>
                
                <button className="flex items-center gap-1 text-blue-600 hover:text-blue-700 
                                   dark:text-blue-400 dark:hover:text-blue-300">
                  Prepara Ordine <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Footer */}
      {data && (
        <div className="p-3 border-t border-gray-200 dark:border-gray-700 text-xs text-gray-500 dark:text-gray-400 text-center">
          Generato: {new Date(data.generated_at).toLocaleString('it-IT')}
        </div>
      )}
    </div>
  );
};

export default TradeCandidatesPanel;
