/**
 * Markets Page
 * Real-time market data and watchlists
 */
import { useState, useEffect } from 'react';
import { Layout } from '../components/layout';
import { Card, CardContent } from '../components/common';
import { Globe, Search, TrendingUp, TrendingDown, Clock, Zap, X, BarChart2, Activity, Flame, ArrowUp, ArrowDown } from 'lucide-react';
import { WatchlistComponent, PriceAlerts } from '../components/market';
import { CandlestickChart } from '../components/charts';
import type { CandlestickData } from '../components/charts/types';
import { useMarketWebSocket } from '../hooks/useWebSocket';
import { marketApi } from '../services/api';

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

interface MoverQuote {
  symbol: string;
  name: string;
  price: number;
  change: number;
  change_percent: number;
  volume: number;
  avg_volume?: number;
  volume_ratio?: number;
  trending_score?: number;
}

interface MarketHourInfo {
  code: string;
  name: string;
  region: string;
  is_open: boolean;
  session: string;
  local_time: string;
  timezone: string;
  open_time: string | null;
  close_time: string | null;
  day_type: string;
  reason: string | null;
}

type MoverTab = 'most-active' | 'gainers' | 'losers' | 'trending';

const Markets = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [showSearchResults, setShowSearchResults] = useState(false);
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [selectedQuote, setSelectedQuote] = useState<StockQuote | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  
  // Movers state
  const [activeMoversTab, setActiveMoversTab] = useState<MoverTab>('most-active');
  const [moversData, setMoversData] = useState<MoverQuote[]>([]);
  const [isLoadingMovers, setIsLoadingMovers] = useState(false);
  
  // Chart state
  const [chartData, setChartData] = useState<CandlestickData[]>([]);
  const [chartPeriod, setChartPeriod] = useState('1M');
  const [isLoadingChart, setIsLoadingChart] = useState(false);
  const [chartError, setChartError] = useState<string | null>(null);
  
  // Market hours state
  const [marketHours, setMarketHours] = useState<MarketHourInfo[]>([]);
  const [isLoadingMarketHours, setIsLoadingMarketHours] = useState(false);
  const [lastMarketHoursUpdate, setLastMarketHoursUpdate] = useState<Date | null>(null);

  // WebSocket connection status (for display)
  const { status } = useMarketWebSocket();

  // Load market hours on mount and every 30 seconds
  useEffect(() => {
    loadMarketHours();
    const interval = setInterval(loadMarketHours, 30000); // 30 seconds
    return () => clearInterval(interval);
  }, []);

  // Load movers data on mount and when tab changes
  useEffect(() => {
    loadMoversData(activeMoversTab);
  }, [activeMoversTab]);

  // Load chart data when symbol or period changes
  useEffect(() => {
    if (selectedSymbol) {
      loadChartData(selectedSymbol, chartPeriod);
    }
  }, [selectedSymbol, chartPeriod]);

  const loadMarketHours = async () => {
    setIsLoadingMarketHours(true);
    try {
      const response = await fetch('/api/v1/market/market-hours');
      const data = await response.json();
      if (data.markets) {
        setMarketHours(data.markets);
        setLastMarketHoursUpdate(new Date());
      }
    } catch (err) {
      console.error('Failed to load market hours:', err);
    } finally {
      setIsLoadingMarketHours(false);
    }
  };

  const loadMoversData = async (tab: MoverTab) => {
    setIsLoadingMovers(true);
    try {
      let result;
      switch (tab) {
        case 'most-active':
          result = await marketApi.getMostActive(10);
          setMoversData(result.most_active || []);
          break;
        case 'gainers':
          result = await marketApi.getTopGainers(10);
          setMoversData(result.gainers || []);
          break;
        case 'losers':
          result = await marketApi.getTopLosers(10);
          setMoversData(result.losers || []);
          break;
        case 'trending':
          result = await marketApi.getTrending(10);
          setMoversData(result.trending || []);
          break;
      }
    } catch (err) {
      console.error('Failed to load movers data:', err);
      setMoversData([]);
    } finally {
      setIsLoadingMovers(false);
    }
  };

  const loadChartData = async (symbol: string, period: string) => {
    setIsLoadingChart(true);
    setChartError(null);
    try {
      const data = await marketApi.getHistorical(symbol, period);
      if (data.data && Array.isArray(data.data)) {
        // Convert API response to CandlestickData format
        const candleData: CandlestickData[] = data.data.map((d: any) => ({
          time: d.date || d.timestamp || d.time,
          open: parseFloat(d.open),
          high: parseFloat(d.high),
          low: parseFloat(d.low),
          close: parseFloat(d.close),
          volume: d.volume ? parseFloat(d.volume) : undefined,
        }));
        setChartData(candleData);
      } else {
        setChartData([]);
        setChartError('No historical data available');
      }
    } catch (err) {
      console.error('Failed to load chart data:', err);
      setChartError('Failed to load chart data');
      setChartData([]);
    } finally {
      setIsLoadingChart(false);
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

  // Handle symbol click from movers list
  const handleSymbolClick = async (symbol: string) => {
    setSelectedSymbol(symbol);
    try {
      const q = await marketApi.getQuote(symbol);
      setSelectedQuote(q);
    } catch (err) {
      console.error('Failed to load quote:', err);
    }
  };

  const formatVolume = (vol: number) => {
    if (vol >= 1_000_000_000) return `${(vol / 1_000_000_000).toFixed(1)}B`;
    if (vol >= 1_000_000) return `${(vol / 1_000_000).toFixed(1)}M`;
    if (vol >= 1_000) return `${(vol / 1_000).toFixed(1)}K`;
    return vol.toString();
  };

  // Get currency symbol and format price based on stock ticker suffix
  const getCurrencyInfo = (symbol: string): { symbol: string; code: string; decimals: number } => {
    if (!symbol) return { symbol: '$', code: 'USD', decimals: 2 };
    
    const upperSymbol = symbol.toUpperCase();
    
    // London Stock Exchange - prices in GBX (pence)
    if (upperSymbol.endsWith('.L')) {
      return { symbol: 'GBX ', code: 'GBX', decimals: 2 };
    }
    // Hong Kong Stock Exchange
    if (upperSymbol.endsWith('.HK')) {
      return { symbol: 'HK$', code: 'HKD', decimals: 2 };
    }
    // Tokyo Stock Exchange
    if (upperSymbol.endsWith('.T')) {
      return { symbol: '¥', code: 'JPY', decimals: 0 };
    }
    // Euronext exchanges (Milan, Paris, Amsterdam, Brussels, etc.)
    if (upperSymbol.endsWith('.MI') || upperSymbol.endsWith('.PA') || 
        upperSymbol.endsWith('.AS') || upperSymbol.endsWith('.BR')) {
      return { symbol: '€', code: 'EUR', decimals: 2 };
    }
    // German exchanges (XETRA, Frankfurt)
    if (upperSymbol.endsWith('.DE') || upperSymbol.endsWith('.F')) {
      return { symbol: '€', code: 'EUR', decimals: 2 };
    }
    // Swiss Exchange
    if (upperSymbol.endsWith('.SW')) {
      return { symbol: 'CHF ', code: 'CHF', decimals: 2 };
    }
    // Toronto Stock Exchange
    if (upperSymbol.endsWith('.TO')) {
      return { symbol: 'C$', code: 'CAD', decimals: 2 };
    }
    // Australian Stock Exchange
    if (upperSymbol.endsWith('.AX')) {
      return { symbol: 'A$', code: 'AUD', decimals: 2 };
    }
    // Singapore Exchange
    if (upperSymbol.endsWith('.SI')) {
      return { symbol: 'S$', code: 'SGD', decimals: 2 };
    }
    // India NSE/BSE
    if (upperSymbol.endsWith('.NS') || upperSymbol.endsWith('.BO')) {
      return { symbol: '₹', code: 'INR', decimals: 2 };
    }
    // Default US market
    return { symbol: '$', code: 'USD', decimals: 2 };
  };

  const formatPrice = (price: number | undefined, symbol: string): string => {
    if (price === undefined || price === null) return '-';
    const currencyInfo = getCurrencyInfo(symbol);
    const formatted = price.toFixed(currencyInfo.decimals);
    return `${currencyInfo.symbol}${formatted}`;
  };

  const getMoversTabIcon = (tab: MoverTab) => {
    switch (tab) {
      case 'most-active': return <Activity className="w-4 h-4" />;
      case 'gainers': return <TrendingUp className="w-4 h-4" />;
      case 'losers': return <TrendingDown className="w-4 h-4" />;
      case 'trending': return <Flame className="w-4 h-4" />;
    }
  };

  const getMoversTabLabel = (tab: MoverTab) => {
    switch (tab) {
      case 'most-active': return 'Most Traded';
      case 'gainers': return 'Top Gainers';
      case 'losers': return 'Top Losers';
      case 'trending': return 'Trending';
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
                          <span className="text-2xl font-bold text-white">{formatPrice(selectedQuote.price, selectedQuote.symbol)}</span>
                          <p className={`text-sm font-medium ${selectedQuote.change >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                            {selectedQuote.change >= 0 ? '+' : ''}{selectedQuote.change?.toFixed(2)} ({selectedQuote.change_percent?.toFixed(2)}%)
                          </p>
                        </div>
                      </div>
                      <div className="grid grid-cols-4 gap-4 text-sm">
                        <div>
                          <p className="text-surface-400">Open</p>
                          <p className="text-white font-medium">{formatPrice(selectedQuote.open, selectedQuote.symbol)}</p>
                        </div>
                        <div>
                          <p className="text-surface-400">High</p>
                          <p className="text-white font-medium">{formatPrice(selectedQuote.high, selectedQuote.symbol)}</p>
                        </div>
                        <div>
                          <p className="text-surface-400">Low</p>
                          <p className="text-white font-medium">{formatPrice(selectedQuote.low, selectedQuote.symbol)}</p>
                        </div>
                        <div>
                          <p className="text-surface-400">Volume</p>
                          <p className="text-white font-medium">{formatVolume(selectedQuote.volume)}</p>
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

            {/* Price Chart */}
            {selectedSymbol && (
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <BarChart2 className="w-4 h-4 text-blue-400" />
                      <h2 className="font-semibold text-white">{selectedSymbol} Price Chart</h2>
                    </div>
                    <div className="flex gap-2">
                      {['1D', '1W', '1M', '3M', '1Y'].map((period) => (
                        <button
                          key={period}
                          onClick={() => setChartPeriod(period)}
                          className={`px-3 py-1 text-xs rounded-lg transition-colors ${
                            chartPeriod === period
                              ? 'bg-primary-600 text-white'
                              : 'bg-surface-700 text-surface-400 hover:bg-surface-600'
                          }`}
                        >
                          {period}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="bg-surface-800 rounded-lg p-2">
                    <CandlestickChart
                      data={chartData}
                      symbol={selectedSymbol}
                      showVolume={true}
                      showMA={true}
                      maLength={20}
                      height={350}
                      theme="dark"
                      loading={isLoadingChart}
                      error={chartError || undefined}
                    />
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Market Movers - Tabbed Section */}
            <Card>
              <CardContent className="p-4">
                {/* Tab Header */}
                <div className="flex items-center justify-between mb-4">
                  <div className="flex gap-1 bg-surface-800 p-1 rounded-lg">
                    {(['most-active', 'gainers', 'losers', 'trending'] as MoverTab[]).map((tab) => (
                      <button
                        key={tab}
                        onClick={() => setActiveMoversTab(tab)}
                        className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md transition-colors ${
                          activeMoversTab === tab
                            ? 'bg-primary-600 text-white'
                            : 'text-surface-400 hover:text-white hover:bg-surface-700'
                        }`}
                      >
                        {getMoversTabIcon(tab)}
                        <span className="hidden sm:inline">{getMoversTabLabel(tab)}</span>
                      </button>
                    ))}
                  </div>
                  <button
                    onClick={() => loadMoversData(activeMoversTab)}
                    className="text-xs text-primary-400 hover:text-primary-300 transition-colors"
                  >
                    Refresh
                  </button>
                </div>
                
                {/* Movers List */}
                {isLoadingMovers ? (
                  <div className="flex items-center justify-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
                  </div>
                ) : moversData.length === 0 ? (
                  <div className="text-center py-8 text-surface-400">
                    No data available. Market may be closed.
                  </div>
                ) : (
                  <div className="space-y-2">
                    {/* Table Header */}
                    <div className="grid grid-cols-12 gap-2 px-3 py-2 text-xs text-surface-400 border-b border-surface-700">
                      <div className="col-span-4">Symbol</div>
                      <div className="col-span-2 text-right">Price</div>
                      <div className="col-span-3 text-right">Change</div>
                      <div className="col-span-3 text-right">
                        {activeMoversTab === 'trending' ? 'Score' : 'Volume'}
                      </div>
                    </div>
                    
                    {/* Movers Items */}
                    {moversData.map((mover, index) => (
                      <button
                        key={mover.symbol}
                        onClick={() => handleSymbolClick(mover.symbol)}
                        className="w-full grid grid-cols-12 gap-2 px-3 py-2.5 bg-surface-800 rounded-lg hover:bg-surface-700 transition-colors text-left items-center"
                      >
                        <div className="col-span-4 flex items-center gap-2">
                          <span className="text-surface-500 text-xs w-4">{index + 1}</span>
                          <div>
                            <span className="font-medium text-white">{mover.symbol}</span>
                            <p className="text-xs text-surface-400 truncate max-w-[120px]">{mover.name}</p>
                          </div>
                        </div>
                        <div className="col-span-2 text-right">
                          <span className="text-white font-medium">{formatPrice(mover.price, mover.symbol)}</span>
                        </div>
                        <div className="col-span-3 text-right">
                          <div className={`flex items-center justify-end gap-1 ${mover.change_percent >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                            {mover.change_percent >= 0 ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />}
                            <span className="font-medium">{Math.abs(mover.change_percent || 0).toFixed(2)}%</span>
                          </div>
                        </div>
                        <div className="col-span-3 text-right">
                          {activeMoversTab === 'trending' ? (
                            <div className="flex flex-col items-end">
                              <span className="text-yellow-500 font-medium">{mover.trending_score}</span>
                              <span className="text-xs text-surface-400">{mover.volume_ratio}x vol</span>
                            </div>
                          ) : (
                            <span className="text-surface-300">{formatVolume(mover.volume)}</span>
                          )}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Market Hours Info */}
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4 text-blue-400" />
                    <h2 className="font-semibold text-white">Market Hours</h2>
                  </div>
                  <div className="flex items-center gap-2">
                    {lastMarketHoursUpdate && (
                      <span className="text-xs text-surface-500">
                        Updated: {lastMarketHoursUpdate.toLocaleTimeString()}
                      </span>
                    )}
                    <button 
                      onClick={loadMarketHours}
                      disabled={isLoadingMarketHours}
                      className="text-xs text-blue-400 hover:text-blue-300 disabled:opacity-50"
                    >
                      {isLoadingMarketHours ? '...' : '↻'}
                    </button>
                  </div>
                </div>
                
                {marketHours.length === 0 ? (
                  <div className="text-center py-4 text-surface-400">
                    {isLoadingMarketHours ? 'Loading market hours...' : 'No market data'}
                  </div>
                ) : (
                  <div className="space-y-4">
                    {/* Group markets by region */}
                    {['US', 'Europe', 'Asia', 'Global'].map(region => {
                      const regionMarkets = marketHours.filter(m => m.region === region);
                      if (regionMarkets.length === 0) return null;
                      
                      return (
                        <div key={region}>
                          <h3 className="text-xs font-medium text-surface-400 mb-2 uppercase tracking-wide">
                            {region}
                          </h3>
                          <div className="grid grid-cols-2 gap-2">
                            {regionMarkets.map(market => (
                              <div 
                                key={market.code}
                                className={`p-2 rounded-lg ${market.is_open ? 'bg-green-900/30 border border-green-700/50' : 'bg-surface-800'}`}
                              >
                                <div className="flex items-center justify-between mb-1">
                                  <span className="text-xs font-medium text-white truncate" title={market.name}>
                                    {market.code}
                                  </span>
                                  <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                                    market.is_open 
                                      ? 'bg-green-500/20 text-green-400' 
                                      : 'bg-surface-600 text-surface-400'
                                  }`}>
                                    {market.is_open ? 'OPEN' : 'CLOSED'}
                                  </span>
                                </div>
                                <p className="text-[10px] text-surface-400 truncate" title={market.name}>
                                  {market.name}
                                </p>
                                <div className="flex justify-between items-center mt-1">
                                  <span className="text-[10px] text-surface-500">
                                    {market.open_time && market.close_time 
                                      ? `${market.open_time} - ${market.close_time}` 
                                      : '24/7'}
                                  </span>
                                  <span className="text-[10px] text-blue-400">
                                    {market.local_time}
                                  </span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default Markets;
