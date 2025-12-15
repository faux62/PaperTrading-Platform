/**
 * Symbol Search Component
 * 
 * User-friendly autocomplete search for stock symbols.
 * Shows symbol, company name, exchange, and current price.
 */
import { useState, useEffect, useRef } from 'react';
import { Search, Loader2, X } from 'lucide-react';
import { clsx } from 'clsx';
import { marketDataApi } from '../../services/api';

// Simple debounce implementation
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

interface SearchResult {
  symbol: string;
  name: string;
  exchange: string;
  sector: string;
  type: string;
  price: number | null;
  currency: string;
}

interface SymbolSearchProps {
  onSelect: (symbol: string, price: number | null, name: string) => void;
  initialValue?: string;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
}

export function SymbolSearch({
  onSelect,
  initialValue = '',
  placeholder = 'Search symbol or company name...',
  className,
  disabled = false
}: SymbolSearchProps) {
  const [query, setQuery] = useState(initialValue);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [error, setError] = useState<string | null>(null);
  
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Debounce the search query
  const debouncedQuery = useDebounce(query, 300);

  // Execute search when debounced query changes
  useEffect(() => {
    const searchSymbols = async () => {
      if (debouncedQuery.length < 1) {
        setResults([]);
        setIsOpen(false);
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        const response = await marketDataApi.searchSymbols(debouncedQuery, 15);
        setResults(response.results || []);
        setIsOpen(true);
        setSelectedIndex(-1);
      } catch (err) {
        console.error('Search error:', err);
        setError('Failed to search symbols');
        setResults([]);
      } finally {
        setIsLoading(false);
      }
    };

    searchSymbols();
  }, [debouncedQuery]);

  // Handle input change
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setQuery(value);
    // Search will be triggered by useEffect when debouncedQuery changes
  };

  // Handle result selection
  const handleSelect = (result: SearchResult) => {
    setQuery(result.symbol);
    setIsOpen(false);
    onSelect(result.symbol, result.price, result.name);
  };

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen || results.length === 0) {
      if (e.key === 'Enter' && query.length >= 1) {
        // Direct symbol entry - try to fetch price
        handleDirectSymbolEntry();
      }
      return;
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex(prev => 
          prev < results.length - 1 ? prev + 1 : prev
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex(prev => prev > 0 ? prev - 1 : -1);
        break;
      case 'Enter':
        e.preventDefault();
        if (selectedIndex >= 0 && results[selectedIndex]) {
          handleSelect(results[selectedIndex]);
        } else if (results.length > 0) {
          handleSelect(results[0]);
        }
        break;
      case 'Escape':
        setIsOpen(false);
        break;
    }
  };

  // Handle direct symbol entry (when user types and presses Enter without selecting)
  const handleDirectSymbolEntry = async () => {
    const symbol = query.trim().toUpperCase();
    if (!symbol) return;

    setIsLoading(true);
    try {
      // Try to get quote for the symbol
      const quote = await marketDataApi.getQuote(symbol);
      onSelect(symbol, quote.price, quote.name || symbol);
      setIsOpen(false);
    } catch (err) {
      setError(`Symbol "${symbol}" not found`);
    } finally {
      setIsLoading(false);
    }
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Clear search
  const handleClear = () => {
    setQuery('');
    setResults([]);
    setIsOpen(false);
    setError(null);
    inputRef.current?.focus();
  };

  return (
    <div className={clsx('relative', className)}>
      {/* Search Input */}
      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          {isLoading ? (
            <Loader2 className="h-5 w-5 text-gray-400 animate-spin" />
          ) : (
            <Search className="h-5 w-5 text-gray-400" />
          )}
        </div>
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={() => query.length >= 1 && setIsOpen(true)}
          placeholder={placeholder}
          disabled={disabled}
          className={clsx(
            'w-full pl-10 pr-10 py-3 text-lg',
            'border border-gray-300 dark:border-gray-600 rounded-lg',
            'bg-white dark:bg-gray-700 text-gray-900 dark:text-white',
            'focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder-gray-400 dark:placeholder-gray-500',
            'disabled:bg-gray-100 dark:disabled:bg-gray-800 disabled:cursor-not-allowed',
            'transition-all'
          )}
        />
        {query && (
          <button
            type="button"
            onClick={handleClear}
            className="absolute inset-y-0 right-0 pr-3 flex items-center"
          >
            <X className="h-5 w-5 text-gray-400 hover:text-gray-600" />
          </button>
        )}
      </div>

      {/* Error Message */}
      {error && (
        <p className="mt-1 text-sm text-red-500">{error}</p>
      )}

      {/* Results Dropdown */}
      {isOpen && results.length > 0 && (
        <div
          ref={dropdownRef}
          className={clsx(
            'absolute z-50 w-full mt-1',
            'bg-white dark:bg-gray-800 rounded-lg shadow-lg',
            'border border-gray-200 dark:border-gray-700',
            'max-h-80 overflow-y-auto'
          )}
        >
          {results.map((result, index) => (
            <button
              key={result.symbol}
              type="button"
              onClick={() => handleSelect(result)}
              className={clsx(
                'w-full px-4 py-3 text-left',
                'flex items-center justify-between',
                'hover:bg-gray-50 dark:hover:bg-gray-700',
                'border-b border-gray-100 dark:border-gray-700 last:border-b-0',
                'transition-colors',
                selectedIndex === index && 'bg-blue-50 dark:bg-blue-900/30'
              )}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-gray-900 dark:text-white">
                    {result.symbol}
                  </span>
                  <span className="text-xs px-2 py-0.5 bg-gray-100 dark:bg-gray-600 rounded text-gray-600 dark:text-gray-300">
                    {result.exchange || result.type}
                  </span>
                </div>
                <p className="text-sm text-gray-500 dark:text-gray-400 truncate">
                  {result.name}
                </p>
                {result.sector && (
                  <p className="text-xs text-gray-400 dark:text-gray-500">
                    {result.sector}
                  </p>
                )}
              </div>
              
              {/* Price Display */}
              {result.price !== null && (
                <div className="ml-4 text-right">
                  <div className="font-semibold text-gray-900 dark:text-white">
                    {result.currency === 'USD' ? '$' : result.currency + ' '}
                    {result.price.toFixed(2)}
                  </div>
                  <div className="text-xs text-gray-500">
                    per share
                  </div>
                </div>
              )}
            </button>
          ))}
        </div>
      )}

      {/* No Results */}
      {isOpen && !isLoading && query.length >= 1 && results.length === 0 && !error && (
        <div
          ref={dropdownRef}
          className={clsx(
            'absolute z-50 w-full mt-1 p-4',
            'bg-white dark:bg-gray-800 rounded-lg shadow-lg',
            'border border-gray-200 dark:border-gray-700',
            'text-center text-gray-500 dark:text-gray-400'
          )}
        >
          <p>No results found for "{query}"</p>
          <p className="text-sm mt-1">Try a different symbol or company name</p>
        </div>
      )}
    </div>
  );
}

export default SymbolSearch;
