/**
 * Markets Page
 * Real-time market data and watchlists
 */
import { useState, useCallback } from 'react';
import { Layout } from '../components/layout';
import { Card, CardContent } from '../components/common';
import { Globe, Search, TrendingUp, Clock, Zap } from 'lucide-react';
import { WatchlistComponent, RealTimeQuote } from '../components/market';
import { useMarketWebSocket, MarketQuote } from '../hooks/useWebSocket';

// Popular stocks for quick access
const POPULAR_STOCKS = [
  'AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM'
];

const Markets = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [quotes, setQuotes] = useState<Map<string, MarketQuote>>(new Map());

  // WebSocket connection for market data
  const { status, subscribe, subscribedSymbols } = useMarketWebSocket((quote) => {
    setQuotes((prev) => new Map(prev).set(quote.symbol, quote));
  });

  // Subscribe to popular stocks on mount
  const subscribeToPopular = useCallback(() => {
    POPULAR_STOCKS.forEach((symbol) => {
      if (!subscribedSymbols.includes(symbol)) {
        subscribe(symbol);
      }
    });
  }, [subscribe, subscribedSymbols]);

  // Handle search
  const handleSearch = () => {
    if (searchQuery.trim()) {
      const symbol = searchQuery.toUpperCase().trim();
      subscribe(symbol);
      setSelectedSymbol(symbol);
      setSearchQuery('');
    }
  };

  // Handle symbol click from watchlist
  const handleSymbolClick = (symbol: string) => {
    setSelectedSymbol(symbol);
    if (!subscribedSymbols.includes(symbol)) {
      subscribe(symbol);
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
                  className="w-full pl-10 pr-4 py-2.5 bg-surface-800 border border-surface-700 rounded-lg text-white placeholder:text-surface-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
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
          {/* Left Column - Watchlists */}
          <div className="lg:col-span-1">
            <WatchlistComponent onSymbolClick={handleSymbolClick} />
          </div>

          {/* Right Column - Market Data */}
          <div className="lg:col-span-2 space-y-6">
            {/* Selected Symbol Detail */}
            {selectedSymbol && (
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center gap-2 mb-4">
                    <Zap className="w-4 h-4 text-yellow-500" />
                    <h2 className="font-semibold text-white">Selected Stock</h2>
                  </div>
                  <RealTimeQuote
                    symbol={selectedSymbol}
                    quote={quotes.get(selectedSymbol)}
                    showVolume
                  />
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
                    onClick={subscribeToPopular}
                    className="text-xs text-primary-400 hover:text-primary-300 transition-colors"
                  >
                    Refresh All
                  </button>
                </div>
                
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {POPULAR_STOCKS.map((symbol) => (
                    <RealTimeQuote
                      key={symbol}
                      symbol={symbol}
                      quote={quotes.get(symbol)}
                      compact
                      onClick={() => handleSymbolClick(symbol)}
                    />
                  ))}
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
