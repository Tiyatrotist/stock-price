import React from 'react';
import { TrendingUp, TrendingDown, Calendar, BarChart3, Clock, Database, RefreshCw, Building2, Globe, MapPin, ArrowRightCircle, ArrowUpCircle, ArrowDownCircle, PieChart } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { Skeleton } from './ui/skeleton';
import { Alert, AlertDescription } from './ui/alert';
import { Button } from './ui/button';
import { StockData, LivePriceResponse, StockInfoResponse } from '../services/stockService';
import { formatPrice, formatPriceDirect, Currency, setExchangeRate, convertPrice, getExchangeRate } from '../utils/currency';
import { CurrencyToggle } from './CurrencyToggle';

interface StockInfoProps {
  data: StockData | null;
  loading: boolean;
  error: string;
  currency: Currency;
  onCurrencyChange: (currency: Currency) => void;
  livePriceData?: LivePriceResponse | null;
  stockInfoData?: StockInfoResponse | null;
  onRefresh: () => void;
}

export function StockInfo({ data, loading, error, currency, onCurrencyChange, livePriceData, stockInfoData, onRefresh }: StockInfoProps) {
  // Update exchange rate when live price data is available
  React.useEffect(() => {
    if (livePriceData?.exchange_rate) {
      setExchangeRate(livePriceData.exchange_rate);
    }
  }, [livePriceData?.exchange_rate]);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="card-title-scaled flex items-center justify-between">
            <div className='card-title-with-icon'>
              <PieChart className='card-icon-scaled' />
              Stock Information
              <Button
                variant="ghost"
                size="sm"
                onClick={onRefresh}
                className="h-8 w-8 p-0"
                disabled={loading}
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              </Button>
            </div>
            <CurrencyToggle currency={currency} onCurrencyChange={onCurrencyChange} />
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Skeleton className="h-8 w-32" />
          <Skeleton className="h-6 w-24" />
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="card-title-scaled flex items-center justify-between">
            <div className='card-title-with-icon'>
              <PieChart className='card-icon-scaled' />
              Stock Information
              <Button
                variant="ghost"
                size="sm"
                onClick={onRefresh}
                className="h-8 w-8 p-0"
                disabled={loading}
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              </Button>
            </div>
            <CurrencyToggle currency={currency} onCurrencyChange={onCurrencyChange} />
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Alert>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  if (!data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="card-title-scaled flex items-center justify-between">
            <div className='card-title-with-icon'>
              <PieChart className='card-icon-scaled' />
              Stock Information
              <Button
                variant="ghost"
                size="sm"
                onClick={onRefresh}
                className="h-8 w-8 p-0"
                disabled={loading}
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              </Button>
            </div>
            <CurrencyToggle currency={currency} onCurrencyChange={onCurrencyChange} />
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-sm">
            Select a stock to view detailed information
          </p>
        </CardContent>
      </Card>
    );
  }

  const isPositiveChange = (data.change || 0) >= 0;

  // Determine the actual price to display
  // IMPORTANT: data.price is ALWAYS in USD (normalized in stockService.ts)
  const getDisplayPrice = () => {
    // If displaying in USD, use price directly
    if (currency === 'USD') {
      return data.price;
    }
    
    // If displaying in INR, convert USD to INR
    const rate = livePriceData?.exchange_rate || getExchangeRate();
    return convertPrice(data.price, 'USD', 'INR', rate);
  };

  const displayPrice = getDisplayPrice();

  // Helper function to format price values consistently
  const formatFieldPrice = (value: number | undefined | null) => {
    if (value === undefined || value === null) return null;
    
    // IMPORTANT: data.price, data.open, etc. are ALWAYS in USD (normalized in stockService.ts)
    // regardless of the original backend currency
    const sourceCurrency: Currency = 'USD';
    
    // Check if conversion is needed
    if (sourceCurrency === currency) {
      // No conversion needed - already in USD and user wants USD
      return formatPriceDirect(value, currency);
    }
    
    // Convert USD to INR for display
    const rate = livePriceData?.exchange_rate || getExchangeRate();
    const converted = convertPrice(value, sourceCurrency, currency, rate);
    
    // Format the converted value
    return formatPriceDirect(converted, currency);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="card-title-scaled flex items-center justify-between">
          <div className="card-title-with-icon">
            <PieChart className="card-icon-scaled" />
            Stock Information
            <Button
              variant="ghost"
              size="sm"
              onClick={onRefresh}
              className="h-8 w-8 p-0"
              disabled={loading}
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
          <CurrencyToggle currency={currency} onCurrencyChange={onCurrencyChange} />
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <div className="stock-price-main">{formatPriceDirect(displayPrice, currency)}</div>
          <div className="flex items-center gap-2 mt-1">
            {isPositiveChange ? (
              <TrendingUp className="stock-change-icon text-green-600" />
            ) : (
              <TrendingDown className="stock-change-icon text-red-600" />
            )}
            <span className={`stock-change-info ${isPositiveChange ? 'text-green-600' : 'text-red-600'
              }`}>
              {formatFieldPrice(Math.abs(data.change || 0))} ({(data.changePercent || 0).toFixed(2)}%)
            </span>
          </div>

          {/* Data source indicator */}
          {livePriceData && (
            <>
              {/* Show warning for offline/stored data */}
              {!livePriceData.source_reliable && livePriceData.data_date && (
                <div className="mt-2 px-3 py-2 bg-amber-50 border border-amber-200 rounded-md">
                  <div className="flex items-center gap-2 text-sm text-amber-700">
                    <Database className="h-4 w-4" />
                    <span>Using offline data from {livePriceData.data_date}</span>
                  </div>
                </div>
              )}
              
              {/* Show live data indicator */}
              {livePriceData.source_reliable && (
                <div className="space-y-1 mt-2 stock-live-data text-muted-foreground">
                  <div className="flex items-center gap-2">
                    <Database className="stock-live-data-icon" />
                    <span>Live data from {livePriceData.source}</span>
                    <Clock className="stock-live-data-icon ml-2" />
                    <span>{new Date(livePriceData.timestamp).toLocaleTimeString()}</span>
                  </div>
                </div>
              )}
              
              {/* Exchange rate (show for both live and offline) */}
              {livePriceData.exchange_rate && (
                <div className="flex items-center gap-2 mt-1 text-sm text-muted-foreground">
                  <span>Exchange Rate: 1 USD = ₹{livePriceData.exchange_rate.toFixed(2)}</span>
                  <span className="opacity-75">({livePriceData.exchange_source})</span>
                </div>
              )}
            </>
          )}
        </div>

        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <span className="stock-metadata-label text-muted-foreground">Symbol</span>
            <Badge variant="secondary" className="stock-symbol-badge">{data.symbol}</Badge>
          </div>

          <div className="flex justify-between items-center">
            <span className="stock-metadata-label text-muted-foreground">Company</span>
            <span className="stock-metadata-value">{data.name}</span>
          </div>

          {data.open !== undefined && data.open !== null && (
            <div className="flex justify-between items-center">
              <span className="stock-metadata-label text-muted-foreground flex items-center gap-1">
                <ArrowRightCircle className="stock-metadata-icon" />
                Open
              </span>
              <span className="stock-metadata-value">{
                formatFieldPrice(data.open)
              }</span>
            </div>
          )}

          {data.high !== undefined && data.high !== null && (
            <div className="flex justify-between items-center">
              <span className="stock-metadata-label text-muted-foreground flex items-center gap-1">
                <ArrowUpCircle className="stock-metadata-icon text-green-600" />
                High
              </span>
              <span className="stock-metadata-value text-green-600">{
                formatFieldPrice(data.high)
              }</span>
            </div>
          )}

          {data.low !== undefined && data.low !== null && (
            <div className="flex justify-between items-center">
              <span className="stock-metadata-label text-muted-foreground flex items-center gap-1">
                <ArrowDownCircle className="stock-metadata-icon text-red-600" />
                Low
              </span>
              <span className="stock-metadata-value text-red-600">{
                formatFieldPrice(data.low)
              }</span>
            </div>
          )}

          {data.close !== undefined && data.close !== null && (
            <div className="flex justify-between items-center">
              <span className="stock-metadata-label text-muted-foreground flex items-center gap-1">
                <Calendar className="stock-metadata-icon" />
                Close
              </span>
              <span className="stock-metadata-value">{
                formatFieldPrice(data.close)
              }</span>
            </div>
          )}

          {data.marketCap && data.marketCap !== 'N/A' && (
            <div className="flex justify-between items-center">
              <span className="stock-metadata-label text-muted-foreground">Market Cap</span>
              <span className="stock-metadata-value">{data.marketCap}</span>
            </div>
          )}

          {stockInfoData && stockInfoData.indicators && stockInfoData.indicators.rsi !== undefined && (
            <div className="flex justify-between items-center">
              <span className="stock-metadata-label text-muted-foreground flex items-center gap-1">
                <BarChart3 className="stock-metadata-icon" />
                RSI (14)
              </span>
              <div className="flex items-center gap-2">
                <span className="stock-metadata-value text-sm">
                  {stockInfoData.indicators.rsi.toFixed(2)}
                </span>
                {stockInfoData.indicators.rsi_tag && (
                  <Badge 
                    variant={stockInfoData.indicators.rsi_tag === 'Overbought' ? 'destructive' : stockInfoData.indicators.rsi_tag === 'Oversold' ? 'default' : 'secondary'}
                    className="text-[10px] px-1.5 py-0"
                  >
                    {stockInfoData.indicators.rsi_tag}
                  </Badge>
                )}
              </div>
            </div>
          )}

          {stockInfoData && stockInfoData.indicators && stockInfoData.indicators.golden_cross && (
            <div className="flex justify-between items-center">
              <span className="stock-metadata-label text-muted-foreground flex items-center gap-1">
                <TrendingUp className="stock-metadata-icon text-green-500" />
                Golden Cross
              </span>
              <Badge variant="default" className="text-[10px] px-1.5 py-0 bg-green-500 hover:bg-green-600">
                Bullish Signal
              </Badge>
            </div>
          )}

          {/* Additional metadata from stock info data (fast) or live price data (fallback) */}
          {(stockInfoData?.sector || livePriceData?.sector) && (stockInfoData?.sector || livePriceData?.sector) !== 'N/A' && (
            <div className="flex justify-between items-center">
              <span className="stock-metadata-label text-muted-foreground flex items-center gap-1">
                <Building2 className="stock-metadata-icon" />
                Sector
              </span>
              <span className="stock-metadata-value">{stockInfoData?.sector || livePriceData?.sector}</span>
            </div>
          )}

          {(stockInfoData?.market_cap || livePriceData?.market_cap) && (stockInfoData?.market_cap || livePriceData?.market_cap) !== 'N/A' && (stockInfoData?.market_cap || livePriceData?.market_cap) !== data.marketCap && (
            <div className="flex justify-between items-center">
              <span className="stock-metadata-label text-muted-foreground flex items-center gap-1">
                <BarChart3 className="stock-metadata-icon" />
                Market Cap
              </span>
              <span className="stock-metadata-value">{stockInfoData?.market_cap || livePriceData?.market_cap}</span>
            </div>
          )}

          {(stockInfoData?.headquarters || livePriceData?.headquarters) && (stockInfoData?.headquarters || livePriceData?.headquarters) !== 'N/A' && (
            <div className="flex justify-between items-center">
              <span className="stock-metadata-label text-muted-foreground flex items-center gap-1">
                <MapPin className="stock-metadata-icon" />
                Headquarters
              </span>
              <span className="stock-metadata-value">{stockInfoData?.headquarters || livePriceData?.headquarters}</span>
            </div>
          )}

          {(stockInfoData?.exchange || livePriceData?.exchange) && (stockInfoData?.exchange || livePriceData?.exchange) !== 'N/A' && (
            <div className="flex justify-between items-center">
              <span className="stock-metadata-label text-muted-foreground flex items-center gap-1">
                <Globe className="stock-metadata-icon" />
                Exchange
              </span>
              <span className="stock-metadata-value">{stockInfoData?.exchange || livePriceData?.exchange}</span>
            </div>
          )}

          <div className="flex justify-between items-center">
            <span className="stock-metadata-label text-muted-foreground">Last Updated</span>
            <span className="stock-metadata-value">{new Date(data.lastUpdated).toLocaleString()}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}