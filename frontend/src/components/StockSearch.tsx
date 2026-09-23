import { useState, useEffect } from 'react';
import { Search } from 'lucide-react';
import { Input } from './ui/input';
import { Button } from './ui/button';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { stockService } from '../services/stockService';

interface StockSearchProps {
  onStockSelect: (symbol: string) => void;
  selectedSymbol?: string;
}

export function StockSearch({ onStockSelect, selectedSymbol }: StockSearchProps) {
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState<{ symbol: string; name: string }[]>([]);
  const [popularStocks, setPopularStocks] = useState<{ symbol: string; name: string }[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isLoadingPopular, setIsLoadingPopular] = useState(true);

  // Load popular stocks on mount
  useEffect(() => {
    const loadPopularStocks = async () => {
      try {
        const stocks = await stockService.getPopularStocks();
        setPopularStocks(stocks);
      } catch (error) {
        console.error('Failed to load popular stocks:', error);
      } finally {
        setIsLoadingPopular(false);
      }
    };

    loadPopularStocks();
  }, []);

  useEffect(() => {
    const performSearch = async () => {
      if (query.trim().length > 0) {
        setIsSearching(true);
        try {
          const results = await stockService.searchStocks(query);
          setSearchResults(results);
        } catch (error) {
          console.error('Search error:', error);
          setSearchResults([]);
        } finally {
          setIsSearching(false);
        }
      } else {
        setSearchResults([]);
      }
    };

    const debounceTimer = setTimeout(performSearch, 300);
    return () => clearTimeout(debounceTimer);
  }, [query]);

  const handleStockClick = (symbol: string) => {
    onStockSelect(symbol);
    setQuery('');
    setSearchResults([]);
  };

  const displayStocks = query.trim().length > 0 ? searchResults : popularStocks;

  return (
    <Card>
      <CardContent className="p-4">
        <div className="relative mb-4">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground stock-search-icon" />
          <Input
            placeholder="Search stocks (e.g., AAPL, Apple)"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Escape') {
                setQuery('');
                setSearchResults([]);
              }
            }}
            className="pl-10 stock-search-input"
          />
        </div>

        {(isSearching || isLoadingPopular) && (
          <div className="text-center text-muted-foreground py-4 stock-search-loading">
            {isSearching ? 'Searching...' : 'Loading stocks...'}
          </div>
        )}

        {!isSearching && !isLoadingPopular && (
          <div>
            <div className="mb-3">
              <h3 className="stock-search-heading text-muted-foreground mb-2">
                {query.trim().length > 0 ? 'Search Results' : 'Popular Stocks'}
              </h3>
            </div>
            
            <div className="space-y-2 max-h-60 overflow-y-auto">
              {displayStocks.map((stock) => (
                <Button
                  key={stock.symbol}
                  variant={selectedSymbol === stock.symbol ? 'default' : 'ghost'}
                  className={`w-full justify-start p-3 h-auto ${selectedSymbol === stock.symbol ? 'stock-search-selected' : ''}`}
                  onClick={() => handleStockClick(stock.symbol)}
                >
                  <div className="flex items-center justify-between w-full">
                    <div className="text-left">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="stock-search-symbol">
                          {stock.symbol}
                        </Badge>
                        {/* Show Indian stock indicator */}
                        {stock.symbol.includes('.NS') || stock.symbol.includes('.BO') || 
                         ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 'WIPRO', 'MARUTI', 'BAJAJFINSV', 'TATACONSUM', 'LTF'].includes(stock.symbol) ? (
                          <Badge variant="secondary" className="stock-search-symbol">
                            NSE
                          </Badge>
                        ) : null}
                        {selectedSymbol === stock.symbol && (
                          <Badge variant="default" className="stock-search-symbol">
                            Selected
                          </Badge>
                        )}
                      </div>
                      <div className="stock-search-company text-muted-foreground mt-1 truncate">
                        {stock.name}
                      </div>
                    </div>
                  </div>
                </Button>
              ))}
              
              {displayStocks.length === 0 && query.trim().length > 0 && !isSearching && (
                <div className="text-center text-muted-foreground py-4 stock-search-no-results">
                  No stocks found for "{query}"
                </div>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}