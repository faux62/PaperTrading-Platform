/**
 * Markets Page
 * Real-time market data and watchlists
 */
import { useState, useEffect } from 'react';
import { Layout } from '../components/layout';
import { Card, CardContent } from '../components/common';
import { Globe, Search, TrendingUp, Clock, Zap, X } from 'lucide-react';
import { WatchlistComponent, PriceAlerts } from '../components/market';
import { useMarketWebSocket } from '../hooks/useWebSocket';
import { marketApi } from '../services/api';

// Popular stocks for quick access
const POPULAR_STOCKS = [
  'AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM'
];

interface SearchResult {
  symbol: string;
  name: string;
  exchange: string;
  sector: string;
}

interface StockQuote {
  symbol: string;
  name: string;
  price: number;
  change: number;
  change_percent: number;
  volume: number;
  high: number;
  low: number;
  open: number;
}

const Markets = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [showSearchResults, setShowSearchResults] = useState(false);
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [selectedQuote, setSelectedQuote] = useState<StockQuote | null>(null);
  const [popularQuotes, setPopularQuotes] = useState<Map<string, StockQuote>>(new Map());
  const [isSearching, setIsSearching] = useState(false);

  // WebSocket connection status (for display)
  const { status } = useMarketWebSocket();

  // Load popular stocks quotes on mount
  useEffect(() => {
    loadPopularQuotes();
  }, []);

  const loadPopularQuotes = async () => {
    try {
      const result = await marketApi.getQuotes(POPULAR_STOCKS);
      if (result.quotes) {
        const quotesMap = new Map<string, StockQuote>();
        result.quotes.forEach((q: StockQuote) => {
          quotesMap.set(q.symbol, q);
        });
        setPopularQuotes(quotesMap);
      }
    } catch (err) {
      console.error('Failed to load popular quotes:', err);
    }
  };

  // Search symbols with debounce
  useEffect(() => {
    if (searchQuery.length < 1) {
      setSearchResults([]);
      setShowSearchResults(false);
      return;
    }

    const timer = setTimeout(async () => {
      setIsSearching(true);
      try {
        const result = await marketApi.search(searchQuery);
        setSearchResults(result.results || []);
        setShowSearchResults(true);
      } catch (err) {
        console.error('Search failed:', err);
        setSearchResults([]);
      } finally {
        setIsSearching(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Handle search result selection
  const handleSelectResult = async (result: SearchResult) => {
    setSelectedSymbol(result.symbol);
    setShowSearchResults(false);
    setSearchQuery('');
    
    // Load quote for selected symbol
    try {
      const quote = await marketApi.getQuote(result.symbol);
      setSelectedQuote(quote);
    } catch (err) {
      console.error('Failed to load quote:', err);
    }
  };

  // Handle search button click
  const handleSearch = async () => {
    if (searchQuery.trim()) {
      const symbol = searchQuery.toUpperCase().trim();
      setSelectedSymbol(symbol);
      setShowSearchResults(false);
      setSearchQuery('');
      
      try {
        const quote = await marketApi.getQuote(symbol);
        if (!quote.error) {
          setSelectedQuote(quote);
        } else {
          setSelectedQuote(null);
        }
      } catch (err) {
        console.error('Failed to load quote:', err);
        setSelectedQuote(null);
      }
    }
  };

  // Handle symbol click from popular stocks
  const handleSymbolClick = async (symbol: string) => {
    setSelectedSymbol(symbol);
    const quote = popularQuotes.get(symbol);
    if (quote) {
      setSelectedQuote(quote);
    } else {
      try {
        const q = await marketApi.getQuote(symbol);
        setSelectedQuote(q);
      } catch (err) {
        console.error('Failed to load quote:', err);
      }
    }
  };

  return (
    <Layout title="Markets">
      <div className="space-y-6">
        {/* Header Section */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-secondary-500/20 rounded-lg flex items-center justify-center">
              <Globe className="w-5 h-5 text-secondary-400" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-white">Markets</h1>
              <p className="text-sm text-surface-400">Real-time quotes and watchlists</p>
            </div>
          </div>
          
          {/* Connection Status */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-surface-800 border border-surface-700">
            <span 
              className={`w-2 h-2 rounded-full ${
                status === 'connected' ? 'bg-green-500' : 
                status === 'connecting' ? 'bg-yellow-500 animate-pulse' : 
                'bg-red-500'
              }`} 
            />
            <span className="text-xs text-surface-400">
              {status === 'connected' ? 'Live Data' : 
               status === 'connecting' ? 'Connecting...' : 'Offline'}
            </span>
          </div>
        </div>

        {/* Search Bar */}
        <Card>
          <CardContent className="p-4">
            <div className="flex gap-3">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-400" />
                <input
                  type="text"
                  placeholder="Search symbol (e.g., AAPL, MSFT, TSLA)..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value.toUpperCase())}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  onFocus={() => searchResults.length > 0 && setShowSearchResults(true)}
                  className="w-full pl-10 pr-4 py-2.5 bg-surface-800 border border-surface-700 rounded-lg text-white placeholder:text-surface-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
                {/* Search Results Dropdown */}
                {showSearchResults && searchResults.length > 0 && (
                  <div className="absolute top-full left-0 right-0 mt-1 bg-surface-800 border border-surface-700 rounded-lg shadow-xl z-50 max-h-60 overflow-y-auto">
                    {searchResults.map((result) => (
                      <button
                        key={result.symbol}
                        onClick={() => handleSelectResult(result)}
                        className="w-full px-4 py-3 text-left hover:bg-surface-700 flex items-center justify-between border-b border-surface-700 last:border-0"
                      >
                        <div>
                          <span className="font-semibold text-white">{result.symbol}</span>
                          <span className="text-surface-400 ml-2 text-sm">{result.name}</span>
                        </div>
                        <span className="text-xs text-surface-500">{result.exchange}</span>
                      </button>
                    ))}
                  </div>
                )}
                {isSearching && (
                  <div className="absolute top-full left-0 right-0 mt-1 bg-surface-800 border border-surface-700 rounded-lg p-3 text-surface-400 text-sm">
                    Searching...
                  </div>
                )}
              </div>
              <button
                onClick={handleSearch}
                disabled={!searchQuery.trim()}
                className="px-6 py-2.5 bg-primary-600 hover:bg-primary-500 disabled:bg-surface-700 disabled:text-surface-500 text-white font-medium rounded-lg transition-colors"
              >
                Search
              </button>
            </div>
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Watchlists & Alerts */}
          <div className="lg:col-span-1 space-y-6">
            <WatchlistComponent onSymbolClick={handleSymbolClick} />
            <PriceAlerts />
          </div>

          {/* Right Column - Market Data */}
          <div className="lg:col-span-2 space-y-6">
            {/* Selected Symbol Detail */}
            {selectedSymbol && (
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <Zap className="w-4 h-4 text-yellow-500" />
                      <h2 className="font-semibold text-white">Selected Stock</h2>
                    </div>
                    <button 
                      onClick={() => { setSelectedSymbol(null); setSelectedQuote(null); }}
                      className="text-surface-400 hover:text-white"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                  {selectedQuote ? (
                    <div className="p-4 bg-surface-800 rounded-lg">
                      <div className="flex items-center justify-between mb-3">
                        <div>
                          <span className="text-2xl font-bold text-white">{selectedQuote.symbol}</span>
                          <p className="text-surface-400 text-sm">{selectedQuote.name}</p>
                        </div>
                        <div className="text-right">
                          <span className="text-2xl font-bold text-white">${selectedQuote.price?.toFixed(2)}</span>
                          <p className={`text-sm font-medium ${selectedQuote.change >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                            {selectedQuote.change >= 0 ? '+' : ''}{selectedQuote.change?.toFixed(2)} ({selectedQuote.change_percent?.toFixed(2)}%)
                          </p>
                        </div>
                      </div>
                      <div className="grid grid-cols-4 gap-4 text-sm">
                        <div>
                          <p className="text-surface-400">Open</p>
                          <p className="text-white font-medium">${selectedQuote.open?.toFixed(2)}</p>
                        </div>
                        <div>
                          <p className="text-surface-400">High</p>
                          <p className="text-white font-medium">${selectedQuote.high?.toFixed(2)}</p>
                        </div>
                        <div>
                          <p className="text-surface-400">Low</p>
                          <p className="text-white font-medium">${selectedQuote.low?.toFixed(2)}</p>
                        </div>
                        <div>
                          <p className="text-surface-400">Volume</p>
                          <p className="text-white font-medium">{(selectedQuote.volume / 1000000).toFixed(1)}M</p>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="p-4 bg-surface-800 rounded-lg text-center text-surface-400">
                      {selectedSymbol} not found in database
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Popular Stocks */}
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-green-500" />
                    <h2 className="font-semibold text-white">Popular Stocks</h2>
                  </div>
                  <button
                    onClick={loadPopularQuotes}
                    className="text-xs text-primary-400 hover:text-primary-300 transition-colors"
                  >
                    Refresh All
                  </button>
                </div>
                
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {POPULAR_STOCKS.map((symbol) => {
                    const quote = popularQuotes.get(symbol);
                    return (
                      <button
                        key={symbol}
                        onClick={() => handleSymbolClick(symbol)}
                        className="flex items-center justify-between p-3 bg-surface-800 rounded-lg hover:bg-surface-700 transition-colors text-left"
                      >
                        <span className="font-medium text-white">{symbol}</span>
                        {quote ? (
                          <div className="text-right">
                            <span className="text-white font-medium">${quote.price?.toFixed(2)}</span>
                            <span className={`ml-2 text-sm ${quote.change >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                              {quote.change >= 0 ? '+' : ''}{quote.change_percent?.toFixed(2)}%
                            </span>
                          </div>
                        ) : (
                          <span className="text-surface-400 text-sm">Loading...</span>
                        )}
                      </button>
                    );
                  })}
                </div>
              </CardContent>
            </Card>

            {/* Market Hours Info */}
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-2 mb-3">
                  <Clock className="w-4 h-4 text-blue-400" />
                  <h2 className="font-semibold text-white">Market Hours</h2>
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="p-3 rounded-lg bg-surface-800">
                    <p className="text-surface-400 mb-1">US Markets (NYSE/NASDAQ)</p>
                    <p className="text-white font-medium">9:30 AM - 4:00 PM ET</p>
                    <p className="text-xs text-surface-500 mt-1">Pre-market: 4:00 AM | After-hours: 8:00 PM</p>
                  </div>
                  <div className="p-3 rounded-lg bg-surface-800">
                    <p className="text-surface-400 mb-1">Crypto Markets</p>
                    <p className="text-white font-medium">24/7</p>
                    <p className="text-xs text-surface-500 mt-1">Always open for trading</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default Markets;
