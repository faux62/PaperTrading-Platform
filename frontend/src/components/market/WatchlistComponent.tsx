/**
 * Watchlist Component
 * Displays user's watchlists with real-time quotes
 */
import { useState, useEffect, useCallback, MouseEvent } from 'react';
import { 
  Plus, 
  X, 
  Trash2, 
  Star,
  ChevronDown,
  ChevronRight
} from 'lucide-react';
import Card, { CardContent, CardHeader } from '../common/Card';
import Button from '../common/Button';
import RealTimeQuote from './RealTimeQuote';
import { useMarketWebSocket, MarketQuote } from '../../hooks/useWebSocket';

// Types
interface WatchlistSymbol {
  symbol: string;
  added_at: string;
}

interface Watchlist {
  id: number;
  user_id: number;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  symbols?: WatchlistSymbol[];
}

interface WatchlistProps {
  onSymbolClick?: (symbol: string) => void;
}

export function WatchlistComponent({ onSymbolClick }: WatchlistProps) {
  const [watchlists, setWatchlists] = useState<Watchlist[]>([]);
  const [expandedWatchlist, setExpandedWatchlist] = useState<number | null>(null);
  const [quotes, setQuotes] = useState<Map<string, MarketQuote>>(new Map());
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newWatchlistName, setNewWatchlistName] = useState('');
  const [searchSymbol, setSearchSymbol] = useState('');
  const [selectedWatchlistId, setSelectedWatchlistId] = useState<number | null>(null);

  // WebSocket for real-time quotes
  const { status, subscribe, unsubscribe, subscribedSymbols } = useMarketWebSocket((quote) => {
    setQuotes((prev) => new Map(prev).set(quote.symbol, quote));
  });

  // Fetch watchlists
  const fetchWatchlists = useCallback(async () => {
    try {
      const token = localStorage.getItem('accessToken');
      const response = await fetch('/api/v1/watchlists/', {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      if (response.ok) {
        const data = await response.json();
        setWatchlists(data.watchlists || []);
      }
    } catch (error) {
      console.error('Failed to fetch watchlists:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch watchlist with symbols
  const fetchWatchlistSymbols = useCallback(async (watchlistId: number) => {
    try {
      const token = localStorage.getItem('accessToken');
      const response = await fetch(`/api/v1/watchlists/${watchlistId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      if (response.ok) {
        const data = await response.json();
        setWatchlists((prev) =>
          prev.map((w) => (w.id === watchlistId ? { ...w, symbols: data.symbols } : w))
        );
        
        // Subscribe to symbols
        data.symbols?.forEach((s: WatchlistSymbol) => {
          if (!subscribedSymbols.includes(s.symbol)) {
            subscribe(s.symbol);
          }
        });
      }
    } catch (error) {
      console.error('Failed to fetch watchlist symbols:', error);
    }
  }, [subscribe, subscribedSymbols]);

  useEffect(() => {
    fetchWatchlists();
  }, [fetchWatchlists]);

  // Toggle watchlist expansion
  const toggleWatchlist = (watchlistId: number) => {
    if (expandedWatchlist === watchlistId) {
      setExpandedWatchlist(null);
    } else {
      setExpandedWatchlist(watchlistId);
      fetchWatchlistSymbols(watchlistId);
    }
  };

  // Create watchlist
  const createWatchlist = async () => {
    if (!newWatchlistName.trim()) return;

    try {
      const token = localStorage.getItem('accessToken');
      const response = await fetch('/api/v1/watchlists/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ name: newWatchlistName }),
      });

      if (response.ok) {
        const newWatchlist = await response.json();
        setWatchlists((prev) => [newWatchlist, ...prev]);
        setNewWatchlistName('');
        setShowCreateModal(false);
      }
    } catch (error) {
      console.error('Failed to create watchlist:', error);
    }
  };

  // Delete watchlist
  const deleteWatchlist = async (watchlistId: number) => {
    if (!confirm('Are you sure you want to delete this watchlist?')) return;

    try {
      const token = localStorage.getItem('accessToken');
      const response = await fetch(`/api/v1/watchlists/${watchlistId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        setWatchlists((prev) => prev.filter((w) => w.id !== watchlistId));
        if (expandedWatchlist === watchlistId) {
          setExpandedWatchlist(null);
        }
      }
    } catch (error) {
      console.error('Failed to delete watchlist:', error);
    }
  };

  // Add symbol to watchlist
  const addSymbol = async (watchlistId: number, symbol: string) => {
    try {
      const token = localStorage.getItem('accessToken');
      const response = await fetch(`/api/v1/watchlists/${watchlistId}/symbols`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ symbol: symbol.toUpperCase() }),
      });

      if (response.ok) {
        fetchWatchlistSymbols(watchlistId);
        subscribe(symbol.toUpperCase());
        setSearchSymbol('');
        setSelectedWatchlistId(null);
      }
    } catch (error) {
      console.error('Failed to add symbol:', error);
    }
  };

  // Remove symbol from watchlist
  const removeSymbol = async (watchlistId: number, symbol: string) => {
    try {
      const token = localStorage.getItem('accessToken');
      const response = await fetch(`/api/v1/watchlists/${watchlistId}/symbols/${symbol}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        setWatchlists((prev) =>
          prev.map((w) =>
            w.id === watchlistId
              ? { ...w, symbols: w.symbols?.filter((s) => s.symbol !== symbol) }
              : w
          )
        );
        unsubscribe(symbol);
      }
    } catch (error) {
      console.error('Failed to remove symbol:', error);
    }
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <Star className="h-5 w-5 text-yellow-500" />
              Watchlists
            </h3>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-12 bg-muted animate-pulse rounded-lg" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Star className="h-5 w-5 text-yellow-500" />
            Watchlists
            <span className="text-xs text-muted-foreground font-normal">
              ({status === 'connected' ? 'Live' : 'Offline'})
            </span>
          </h3>
          <Button size="sm" variant="outline" onClick={() => setShowCreateModal(true)}>
            <Plus className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        {/* Create Modal */}
        {showCreateModal && (
          <div className="p-3 border rounded-lg bg-accent/50 space-y-2">
            <input
              type="text"
              placeholder="Watchlist name..."
              value={newWatchlistName}
              onChange={(e) => setNewWatchlistName(e.target.value)}
              className="w-full px-3 py-2 bg-background border rounded-md text-sm"
              onKeyDown={(e) => e.key === 'Enter' && createWatchlist()}
              autoFocus
            />
            <div className="flex gap-2">
              <Button size="sm" onClick={createWatchlist}>
                Create
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setShowCreateModal(false)}>
                Cancel
              </Button>
            </div>
          </div>
        )}

        {/* Watchlists */}
        {watchlists.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            No watchlists yet. Create one to start tracking stocks.
          </p>
        ) : (
          watchlists.map((watchlist) => (
            <div key={watchlist.id} className="border rounded-lg overflow-hidden">
              {/* Watchlist Header */}
              <div
                className="flex items-center justify-between p-3 cursor-pointer hover:bg-accent/50 transition-colors"
                onClick={() => toggleWatchlist(watchlist.id)}
              >
                <div className="flex items-center gap-2">
                  {expandedWatchlist === watchlist.id ? (
                    <ChevronDown className="h-4 w-4" />
                  ) : (
                    <ChevronRight className="h-4 w-4" />
                  )}
                  <span className="font-medium">{watchlist.name}</span>
                  <span className="text-xs text-muted-foreground">
                    ({watchlist.symbols?.length || 0} symbols)
                  </span>
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-8 w-8 p-0"
                  onClick={(e: MouseEvent) => {
                    e.stopPropagation();
                    deleteWatchlist(watchlist.id);
                  }}
                >
                  <Trash2 className="h-4 w-4 text-destructive" />
                </Button>
              </div>

              {/* Expanded Content */}
              {expandedWatchlist === watchlist.id && (
                <div className="border-t p-2 space-y-1">
                  {/* Add Symbol */}
                  {selectedWatchlistId === watchlist.id ? (
                    <div className="flex gap-2 p-2">
                      <input
                        type="text"
                        placeholder="Enter symbol (e.g., AAPL)"
                        value={searchSymbol}
                        onChange={(e) => setSearchSymbol(e.target.value.toUpperCase())}
                        className="flex-1 px-2 py-1 bg-background border rounded text-sm"
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            addSymbol(watchlist.id, searchSymbol);
                          }
                        }}
                        autoFocus
                      />
                      <Button
                        size="sm"
                        onClick={() => addSymbol(watchlist.id, searchSymbol)}
                        disabled={!searchSymbol}
                      >
                        Add
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          setSelectedWatchlistId(null);
                          setSearchSymbol('');
                        }}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  ) : (
                    <Button
                      size="sm"
                      variant="ghost"
                      className="w-full justify-start text-muted-foreground"
                      onClick={() => setSelectedWatchlistId(watchlist.id)}
                    >
                      <Plus className="h-4 w-4 mr-2" />
                      Add symbol
                    </Button>
                  )}

                  {/* Symbols List */}
                  {watchlist.symbols?.map((s) => (
                    <div
                      key={s.symbol}
                      className="flex items-center gap-2 group"
                    >
                      <div className="flex-1">
                        <RealTimeQuote
                          symbol={s.symbol}
                          quote={quotes.get(s.symbol)}
                          compact
                          onClick={() => onSymbolClick?.(s.symbol)}
                        />
                      </div>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                        onClick={() => removeSymbol(watchlist.id, s.symbol)}
                      >
                        <X className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  ))}

                  {watchlist.symbols?.length === 0 && (
                    <p className="text-xs text-muted-foreground text-center py-2">
                      No symbols in this watchlist
                    </p>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}

export default WatchlistComponent;
