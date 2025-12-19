/**
 * Layered Symbol Selector
 * 
 * A user-friendly, hierarchical stock selector:
 * 1. Select Market/Region (US, EU, UK, Asia)
 * 2. Select Sector (Technology, Healthcare, etc.)
 * 3. Select Stock from filtered list
 * 
 * Data is fetched from the market_universe table via API.
 * Price is fetched only when a stock is selected.
 */
import { useState, useMemo, useEffect } from 'react';
import { 
  ChevronDown, 
  Globe, 
  Building2, 
  TrendingUp, 
  Loader2,
  Search,
  X,
  Check,
  AlertCircle
} from 'lucide-react';
import { clsx } from 'clsx';
import { marketDataApi, universeApi, UniverseSymbol } from '../../services/api';

interface LayeredSymbolSelectorProps {
  onSelect: (symbol: string, price: number | null, name: string, currency: string) => void;
  initialSymbol?: string;
  className?: string;
  disabled?: boolean;
}

// Region metadata for display
const REGION_INFO: Record<string, { name: string; flag: string }> = {
  US: { name: 'United States', flag: '🇺🇸' },
  UK: { name: 'United Kingdom', flag: '🇬🇧' },
  EU: { name: 'Europe', flag: '🇪🇺' },
  ASIA: { name: 'Asia Pacific', flag: '🌏' },
};

export function LayeredSymbolSelector({
  onSelect,
  initialSymbol: _initialSymbol = '',
  className,
  disabled = false
}: LayeredSymbolSelectorProps) {
  // Note: _initialSymbol could be used for pre-selection in future
  
  // Data from API
  const [allSymbols, setAllSymbols] = useState<UniverseSymbol[]>([]);
  const [isLoadingSymbols, setIsLoadingSymbols] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  
  // Selection state
  const [selectedRegion, setSelectedRegion] = useState<string | null>(null);
  const [selectedSector, setSelectedSector] = useState<string | null>(null);
  const [selectedStock, setSelectedStock] = useState<UniverseSymbol | null>(null);
  
  // UI state
  const [isLoadingPrice, setIsLoadingPrice] = useState(false);
  const [currentPrice, setCurrentPrice] = useState<number | null>(null);
  const [priceError, setPriceError] = useState<string | null>(null);
  
  // Quick search state
  const [quickSearchQuery, setQuickSearchQuery] = useState('');
  const [showQuickSearch, setShowQuickSearch] = useState(false);
  const [searchResults, setSearchResults] = useState<UniverseSymbol[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  // Load all symbols on mount
  useEffect(() => {
    const loadSymbols = async () => {
      try {
        setIsLoadingSymbols(true);
        setLoadError(null);
        const symbols = await universeApi.getAllSymbols();
        setAllSymbols(symbols);
      } catch (err) {
        console.error('Failed to load market universe:', err);
        setLoadError('Failed to load symbols. Please refresh.');
      } finally {
        setIsLoadingSymbols(false);
      }
    };
    loadSymbols();
  }, []);

  // Get available regions from loaded data
  const availableRegions = useMemo(() => {
    const regions = new Set<string>();
    allSymbols.forEach(s => regions.add(s.region));
    return Array.from(regions).sort();
  }, [allSymbols]);

  // Get available sectors based on selected region
  const availableSectors = useMemo(() => {
    if (!selectedRegion) return [];
    const sectors = new Set<string>();
    allSymbols
      .filter(s => s.region === selectedRegion && s.sector)
      .forEach(s => sectors.add(s.sector!));
    return Array.from(sectors).sort();
  }, [allSymbols, selectedRegion]);

  // Get available stocks based on selected region and sector
  const availableStocks = useMemo(() => {
    if (!selectedRegion || !selectedSector) return [];
    return allSymbols
      .filter(s => s.region === selectedRegion && s.sector === selectedSector)
      .sort((a, b) => (a.priority || 999) - (b.priority || 999));
  }, [allSymbols, selectedRegion, selectedSector]);

  // Quick search with debounce
  useEffect(() => {
    if (!quickSearchQuery || quickSearchQuery.length < 2) {
      setSearchResults([]);
      return;
    }

    const searchTimer = setTimeout(async () => {
      setIsSearching(true);
      try {
        const results = await universeApi.search(quickSearchQuery, 20);
        setSearchResults(results);
      } catch (err) {
        console.error('Search failed:', err);
        setSearchResults([]);
      } finally {
        setIsSearching(false);
      }
    }, 300);

    return () => clearTimeout(searchTimer);
  }, [quickSearchQuery]);

  // Fetch price when a stock is selected
  const fetchPrice = async (symbol: string) => {
    setIsLoadingPrice(true);
    setPriceError(null);
    
    try {
      const quote = await marketDataApi.getQuote(symbol);
      setCurrentPrice(quote.price);
      return quote.price;
    } catch (err) {
      console.error('Failed to fetch price:', err);
      setPriceError('Price unavailable');
      setCurrentPrice(null);
      return null;
    } finally {
      setIsLoadingPrice(false);
    }
  };

  // Handle region selection
  const handleRegionSelect = (region: string) => {
    setSelectedRegion(region);
    setSelectedSector(null);
    setSelectedStock(null);
    setCurrentPrice(null);
  };

  // Handle sector selection
  const handleSectorSelect = (sector: string) => {
    setSelectedSector(sector);
    setSelectedStock(null);
    setCurrentPrice(null);
  };

  // Handle stock selection
  const handleStockSelect = async (stock: UniverseSymbol) => {
    setSelectedStock(stock);
    const price = await fetchPrice(stock.symbol);
    onSelect(stock.symbol, price, stock.name || stock.symbol, stock.currency);
  };

  // Handle quick search selection
  const handleQuickSearchSelect = async (stock: UniverseSymbol) => {
    setSelectedRegion(stock.region);
    setSelectedSector(stock.sector);
    setSelectedStock(stock);
    setShowQuickSearch(false);
    setQuickSearchQuery('');
    setSearchResults([]);
    const price = await fetchPrice(stock.symbol);
    onSelect(stock.symbol, price, stock.name || stock.symbol, stock.currency);
  };

  // Reset selection
  const handleReset = () => {
    setSelectedRegion(null);
    setSelectedSector(null);
    setSelectedStock(null);
    setCurrentPrice(null);
    setPriceError(null);
    setQuickSearchQuery('');
    setSearchResults([]);
  };

  // Loading state
  if (isLoadingSymbols) {
    return (
      <div className={clsx('flex items-center justify-center py-8', className)}>
        <Loader2 className="h-6 w-6 animate-spin text-blue-500 mr-2" />
        <span className="text-gray-600 dark:text-gray-400">Loading market universe...</span>
      </div>
    );
  }

  // Error state
  if (loadError) {
    return (
      <div className={clsx('flex items-center justify-center py-8 text-red-500', className)}>
        <AlertCircle className="h-5 w-5 mr-2" />
        <span>{loadError}</span>
      </div>
    );
  }

  return (
    <div className={clsx('space-y-4', className)}>
      {/* Quick Search Toggle */}
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => setShowQuickSearch(!showQuickSearch)}
          className={clsx(
            'flex items-center gap-2 text-sm font-medium transition-colors',
            showQuickSearch 
              ? 'text-blue-600 dark:text-blue-400' 
              : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
          )}
        >
          <Search className="h-4 w-4" />
          {showQuickSearch ? 'Hide Quick Search' : 'Quick Search'}
        </button>
        
        {selectedStock && (
          <button
            type="button"
            onClick={handleReset}
            className="text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 flex items-center gap-1"
          >
            <X className="h-3 w-3" />
            Reset
          </button>
        )}
      </div>

      {/* Quick Search Input */}
      {showQuickSearch && (
        <div className="relative">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              value={quickSearchQuery}
              onChange={(e) => setQuickSearchQuery(e.target.value)}
              placeholder="Type symbol or company name (min 2 chars)..."
              className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              autoFocus
            />
            {isSearching && (
              <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin text-gray-400" />
            )}
          </div>
          
          {/* Quick Search Results */}
          {searchResults.length > 0 && (
            <div className="absolute z-50 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg max-h-64 overflow-y-auto">
              {searchResults.map((stock) => (
                <button
                  key={stock.symbol}
                  type="button"
                  onClick={() => handleQuickSearchSelect(stock)}
                  className="w-full px-4 py-2.5 text-left hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center justify-between border-b border-gray-100 dark:border-gray-700 last:border-0"
                >
                  <div>
                    <span className="font-semibold text-gray-900 dark:text-white">
                      {stock.symbol}
                    </span>
                    <span className="text-sm text-gray-500 dark:text-gray-400 ml-2">
                      {stock.name}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-gray-400">
                    <span>{REGION_INFO[stock.region]?.flag || '🌍'}</span>
                    <span>{stock.exchange}</span>
                    <span className="text-gray-300">|</span>
                    <span>{stock.sector || 'N/A'}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
          
          {/* No results message */}
          {quickSearchQuery.length >= 2 && !isSearching && searchResults.length === 0 && (
            <div className="absolute z-50 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-4 text-center text-gray-500">
              No symbols found for "{quickSearchQuery}"
            </div>
          )}
        </div>
      )}

      {/* Layered Selection */}
      {!showQuickSearch && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Region Selection */}
          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              <Globe className="h-4 w-4" />
              Region
            </label>
            <div className="relative">
              <select
                value={selectedRegion || ''}
                onChange={(e) => handleRegionSelect(e.target.value)}
                disabled={disabled}
                className={clsx(
                  'w-full appearance-none px-4 py-2.5 rounded-lg border bg-white dark:bg-gray-700',
                  'text-gray-900 dark:text-white',
                  'focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                  'disabled:opacity-50 disabled:cursor-not-allowed',
                  selectedRegion 
                    ? 'border-blue-500 dark:border-blue-400' 
                    : 'border-gray-300 dark:border-gray-600'
                )}
              >
                <option value="">Select region...</option>
                {availableRegions.map((region) => (
                  <option key={region} value={region}>
                    {REGION_INFO[region]?.flag || '🌍'} {REGION_INFO[region]?.name || region}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
            </div>
          </div>

          {/* Sector Selection */}
          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              <Building2 className="h-4 w-4" />
              Sector
            </label>
            <div className="relative">
              <select
                value={selectedSector || ''}
                onChange={(e) => handleSectorSelect(e.target.value)}
                disabled={disabled || !selectedRegion}
                className={clsx(
                  'w-full appearance-none px-4 py-2.5 rounded-lg border bg-white dark:bg-gray-700',
                  'text-gray-900 dark:text-white',
                  'focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                  'disabled:opacity-50 disabled:cursor-not-allowed',
                  selectedSector 
                    ? 'border-blue-500 dark:border-blue-400' 
                    : 'border-gray-300 dark:border-gray-600'
                )}
              >
                <option value="">
                  {selectedRegion ? `Select sector (${availableSectors.length})...` : 'Select region first'}
                </option>
                {availableSectors.map((sector) => (
                  <option key={sector} value={sector}>
                    {sector}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
            </div>
          </div>

          {/* Stock Selection */}
          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              <TrendingUp className="h-4 w-4" />
              Stock
            </label>
            <div className="relative">
              <select
                value={selectedStock?.symbol || ''}
                onChange={(e) => {
                  const stock = availableStocks.find(s => s.symbol === e.target.value);
                  if (stock) handleStockSelect(stock);
                }}
                disabled={disabled || !selectedSector}
                className={clsx(
                  'w-full appearance-none px-4 py-2.5 rounded-lg border bg-white dark:bg-gray-700',
                  'text-gray-900 dark:text-white',
                  'focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                  'disabled:opacity-50 disabled:cursor-not-allowed',
                  selectedStock 
                    ? 'border-green-500 dark:border-green-400' 
                    : 'border-gray-300 dark:border-gray-600'
                )}
              >
                <option value="">
                  {selectedSector 
                    ? `Select stock (${availableStocks.length})...` 
                    : 'Select sector first'}
                </option>
                {availableStocks.map((stock) => (
                  <option key={stock.symbol} value={stock.symbol}>
                    {stock.symbol} - {stock.name || 'Unknown'}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
            </div>
          </div>
        </div>
      )}

      {/* Selected Stock Display with Price */}
      {selectedStock && (
        <div className={clsx(
          'p-4 rounded-xl border-2',
          'bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20',
          'border-green-200 dark:border-green-700'
        )}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-10 h-10 rounded-full bg-green-100 dark:bg-green-800">
                <Check className="h-5 w-5 text-green-600 dark:text-green-400" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-lg font-bold text-gray-900 dark:text-white">
                    {selectedStock.symbol}
                  </span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
                    {REGION_INFO[selectedStock.region]?.flag || '🌍'} {selectedStock.exchange || selectedStock.region}
                  </span>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {selectedStock.name || selectedStock.symbol}
                </p>
              </div>
            </div>
            
            {/* Price Display */}
            <div className="text-right">
              {isLoadingPrice ? (
                <div className="flex items-center gap-2 text-gray-500">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span className="text-sm">Loading price...</span>
                </div>
              ) : priceError ? (
                <span className="text-sm text-amber-600 dark:text-amber-400">
                  {priceError}
                </span>
              ) : currentPrice !== null ? (
                <div>
                  <span className="text-xs text-gray-500 dark:text-gray-400 block">
                    Current Price
                  </span>
                  <span className="text-2xl font-bold text-green-600 dark:text-green-400">
                    {selectedStock.currency === 'USD' && '$'}
                    {selectedStock.currency === 'EUR' && '€'}
                    {selectedStock.currency === 'GBP' && '£'}
                    {selectedStock.currency === 'JPY' && '¥'}
                    {selectedStock.currency === 'HKD' && 'HK$'}
                    {selectedStock.currency === 'CHF' && 'CHF '}
                    {currentPrice.toLocaleString(undefined, {
                      // JPY doesn't use decimal places
                      minimumFractionDigits: selectedStock.currency === 'JPY' ? 0 : 2,
                      maximumFractionDigits: selectedStock.currency === 'JPY' ? 0 : 2
                    })}
                  </span>
                  <span className="text-xs text-gray-500 dark:text-gray-400 ml-1">
                    {selectedStock.currency}
                  </span>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      )}

      {/* Help text when nothing selected */}
      {!selectedStock && !showQuickSearch && (
        <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-2">
          Select Region → Sector → Stock, or use Quick Search ({allSymbols.length} symbols available)
        </p>
      )}
    </div>
  );
}

export default LayeredSymbolSelector;
