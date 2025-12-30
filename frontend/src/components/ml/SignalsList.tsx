/**
 * SignalsList Component
 * 
 * List of trading signals with filtering
 */
import React, { useState, useMemo } from 'react';
import { clsx } from 'clsx';
import { 
  Filter,
  ArrowUpDown,
  TrendingUp,
  TrendingDown,
  Globe,
} from 'lucide-react';
import { SignalIndicator, SignalType } from './SignalIndicator';

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

interface SignalsListProps {
  signals: TradingSignal[];
  onSignalClick?: (signal: TradingSignal) => void;
  loading?: boolean;
  className?: string;
}

type FilterType = 'all' | 'buy' | 'sell' | 'hold';
type RegionFilter = 'all' | 'US' | 'EU' | 'Asia';
type SortField = 'symbol' | 'confidence' | 'change24h' | 'timestamp';

// Helper to detect region from symbol suffix
const getRegionFromSymbol = (symbol: string): 'US' | 'EU' | 'Asia' => {
  const upperSymbol = symbol.toUpperCase();
  
  // European suffixes
  const euSuffixes = ['.DE', '.MI', '.PA', '.MC', '.AS', '.BR', '.SW', '.L', '.IR', '.VI', '.HE', '.CO', '.ST', '.OL', '.LS'];
  for (const suffix of euSuffixes) {
    if (upperSymbol.endsWith(suffix)) return 'EU';
  }
  
  // Asian suffixes
  const asiaSuffixes = ['.T', '.TYO', '.HK', '.SS', '.SZ', '.KS', '.TW', '.SI', '.AX', '.NS', '.BO'];
  for (const suffix of asiaSuffixes) {
    if (upperSymbol.endsWith(suffix)) return 'Asia';
  }
  
  // Default to US (no suffix or unknown)
  return 'US';
};

export const SignalsList: React.FC<SignalsListProps> = ({
  signals,
  onSignalClick,
  loading = false,
  className,
}) => {
  const [filter, setFilter] = useState<FilterType>('all');
  const [regionFilter, setRegionFilter] = useState<RegionFilter>('all');
  const [sortField, setSortField] = useState<SortField>('confidence');
  const [sortAsc, setSortAsc] = useState(false);

  // Filter and sort signals
  const filteredSignals = useMemo(() => {
    let result = [...signals];

    // Apply signal type filter
    if (filter !== 'all') {
      result = result.filter((s) => {
        if (filter === 'buy') return s.signal === 'buy' || s.signal === 'strong_buy';
        if (filter === 'sell') return s.signal === 'sell' || s.signal === 'strong_sell';
        if (filter === 'hold') return s.signal === 'hold';
        return true;
      });
    }

    // Apply region filter
    if (regionFilter !== 'all') {
      result = result.filter((s) => getRegionFromSymbol(s.symbol) === regionFilter);
    }

    // Apply sort
    result.sort((a, b) => {
      let comparison = 0;
      switch (sortField) {
        case 'symbol':
          comparison = a.symbol.localeCompare(b.symbol);
          break;
        case 'confidence':
          comparison = a.confidence - b.confidence;
          break;
        case 'change24h':
          comparison = a.change24h - b.change24h;
          break;
        case 'timestamp':
          comparison = a.timestamp.getTime() - b.timestamp.getTime();
          break;
      }
      return sortAsc ? comparison : -comparison;
    });

    return result;
  }, [signals, filter, regionFilter, sortField, sortAsc]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(false);
    }
  };

  if (loading) {
    return (
      <div className={clsx('space-y-3', className)}>
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className="h-16 bg-gray-100 dark:bg-gray-700 rounded-lg animate-pulse"
          />
        ))}
      </div>
    );
  }

  return (
    <div className={clsx('space-y-4', className)}>
      {/* Filters */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        {/* Signal type filter */}
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-500" />
          <div className="flex rounded-lg bg-gray-100 dark:bg-gray-700 p-1">
            {(['all', 'buy', 'sell', 'hold'] as FilterType[]).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={clsx(
                  'px-3 py-1 text-sm font-medium rounded-md transition-colors capitalize',
                  filter === f
                    ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                )}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        {/* Region filter */}
        <div className="flex items-center gap-2">
          <Globe className="w-4 h-4 text-gray-500" />
          <div className="flex rounded-lg bg-gray-100 dark:bg-gray-700 p-1">
            {(['all', 'US', 'EU', 'Asia'] as RegionFilter[]).map((r) => (
              <button
                key={r}
                onClick={() => setRegionFilter(r)}
                className={clsx(
                  'px-3 py-1 text-sm font-medium rounded-md transition-colors',
                  regionFilter === r
                    ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                )}
              >
                {r === 'all' ? '🌍 All' : r === 'US' ? '🇺🇸 US' : r === 'EU' ? '🇪🇺 EU' : '🌏 Asia'}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={() => handleSort('confidence')}
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
        >
          <ArrowUpDown className="w-4 h-4" />
          Sort by confidence
        </button>
      </div>

      {/* Signals list */}
      {filteredSignals.length === 0 ? (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          No signals match the current filter
        </div>
      ) : (
        <div className="space-y-2">
          {filteredSignals.map((signal) => (
            <div
              key={signal.id}
              onClick={() => onSignalClick?.(signal)}
              className={clsx(
                'flex items-center justify-between p-3 rounded-lg border border-gray-200 dark:border-gray-700',
                'bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700/50',
                'cursor-pointer transition-colors'
              )}
            >
              {/* Left: Symbol and Signal */}
              <div className="flex items-center gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-gray-900 dark:text-white">
                      {signal.symbol}
                    </span>
                    <SignalIndicator signal={signal.signal} size="sm" />
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {signal.source} · {signal.timestamp.toLocaleTimeString()}
                  </p>
                </div>
              </div>

              {/* Right: Price and Confidence */}
              <div className="flex items-center gap-6">
                {/* Price change */}
                <div className="text-right">
                  <p className="font-medium text-gray-900 dark:text-white">
                    ${signal.price.toFixed(2)}
                  </p>
                  <p
                    className={clsx(
                      'text-xs flex items-center justify-end gap-1',
                      signal.change24h >= 0 ? 'text-green-600' : 'text-red-600'
                    )}
                  >
                    {signal.change24h >= 0 ? (
                      <TrendingUp className="w-3 h-3" />
                    ) : (
                      <TrendingDown className="w-3 h-3" />
                    )}
                    {signal.change24h >= 0 ? '+' : ''}
                    {signal.change24h.toFixed(2)}%
                  </p>
                </div>

                {/* Confidence */}
                <div className="w-20">
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                    Confidence
                  </div>
                  <div className="h-2 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
                    <div
                      className={clsx(
                        'h-full rounded-full',
                        signal.confidence >= 0.7
                          ? 'bg-green-500'
                          : signal.confidence >= 0.5
                          ? 'bg-yellow-500'
                          : 'bg-gray-400'
                      )}
                      style={{ width: `${signal.confidence * 100}%` }}
                    />
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 text-right">
                    {Math.round(signal.confidence * 100)}%
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SignalsList;
