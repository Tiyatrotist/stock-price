import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { stockService } from './stockService';

describe('stockService', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    vi.spyOn(console, 'log').mockImplementation(() => {});
    stockService.cancelActiveRequests();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    global.fetch = originalFetch;
    stockService.cancelActiveRequests();
  });

  describe('searchStocks', () => {
    it('returns default popular stocks for empty query without making a network request', async () => {
      const fetchMock = vi.fn();
      vi.stubGlobal('fetch', fetchMock);

      const results = await stockService.searchStocks('');
      expect(results).toHaveLength(8);
      expect(results[0]).toEqual({ symbol: 'AAPL', name: 'Apple Inc.' });
      expect(fetchMock).not.toHaveBeenCalled();
    });

    it('constructs correct URL and returns backend results on successful search', async () => {
      const mockBackendResults = [
        { symbol: 'AAPL', name: 'Apple Inc.' },
        { symbol: 'AA', name: 'Alcoa Corp.' }
      ];

      const fetchMock = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          success: true,
          data: mockBackendResults
        })
      });
      vi.stubGlobal('fetch', fetchMock);

      const results = await stockService.searchStocks('AA');

      expect(fetchMock).toHaveBeenCalledTimes(1);
      const calledUrl = fetchMock.mock.calls[0][0];
      expect(calledUrl).toContain('/search?q=AA');
      expect(results).toEqual(mockBackendResults);
    });

    it('uses cached results on subsequent searches with the same query', async () => {
      const mockBackendResults = [{ symbol: 'CACHED_Q', name: 'Cached Corp' }];
      const fetchMock = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          success: true,
          data: mockBackendResults
        })
      });
      vi.stubGlobal('fetch', fetchMock);

      const firstCall = await stockService.searchStocks('CACHED_QUERY');
      const secondCall = await stockService.searchStocks('CACHED_QUERY');

      expect(firstCall).toEqual(mockBackendResults);
      expect(secondCall).toEqual(mockBackendResults);
      expect(fetchMock).toHaveBeenCalledTimes(1);
    });

    it('falls back to filtered popular stocks when backend returns empty data', async () => {
      const fetchMock = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          success: true,
          data: []
        })
      });
      vi.stubGlobal('fetch', fetchMock);

      const results = await stockService.searchStocks('Tesla');
      expect(results).toHaveLength(1);
      expect(results[0].symbol).toBe('TSLA');
    });

    it('falls back to filtered popular stocks on network failure', async () => {
      const fetchMock = vi.fn().mockRejectedValue(new Error('Failed to fetch'));
      vi.stubGlobal('fetch', fetchMock);

      const results = await stockService.searchStocks('Apple');
      expect(results).toHaveLength(1);
      expect(results[0].symbol).toBe('AAPL');
    });

    it('falls back to filtered popular stocks when server returns HTTP 500 error', async () => {
      const fetchMock = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({ message: 'Server error' })
      });
      vi.stubGlobal('fetch', fetchMock);

      const results = await stockService.searchStocks('MSFT');
      expect(results).toHaveLength(1);
      expect(results[0].symbol).toBe('MSFT');
    });
  });

  describe('getLivePrice', () => {
    it('throws error when symbol is empty or whitespace', async () => {
      await expect(stockService.getLivePrice('')).rejects.toThrow('Stock symbol is required');
      await expect(stockService.getLivePrice('   ')).rejects.toThrow('Stock symbol is required');
    });

    it('constructs correct URL and returns live price data on success', async () => {
      const mockPriceData = {
        symbol: 'NVDA',
        price: 120.5,
        company_name: 'NVIDIA Corporation',
        currency: 'USD',
        timestamp: '2026-10-06T10:00:00Z',
        source: 'test'
      };

      const fetchMock = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          success: true,
          data: mockPriceData
        })
      });
      vi.stubGlobal('fetch', fetchMock);

      const data = await stockService.getLivePrice('nvda');
      expect(fetchMock).toHaveBeenCalledTimes(1);
      const url = fetchMock.mock.calls[0][0];
      expect(url).toContain('/live_price?symbol=NVDA');
      expect(data).toEqual(mockPriceData);
    });

    it('serves cached live price data unless forceRefresh is true', async () => {
      const mockPriceData = {
        symbol: 'CACHE_LIVE',
        price: 100,
        company_name: 'Cache Live Co',
        currency: 'USD',
        timestamp: '2026-10-06T10:00:00Z',
        source: 'test'
      };

      const fetchMock = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          success: true,
          data: mockPriceData
        })
      });
      vi.stubGlobal('fetch', fetchMock);

      await stockService.getLivePrice('CACHE_LIVE');
      await stockService.getLivePrice('CACHE_LIVE');
      expect(fetchMock).toHaveBeenCalledTimes(1);

      await stockService.getLivePrice('CACHE_LIVE', true);
      expect(fetchMock).toHaveBeenCalledTimes(2);
    });

    it('throws connection error when network fails with Failed to fetch', async () => {
      const fetchMock = vi.fn().mockRejectedValue(new Error('Failed to fetch'));
      vi.stubGlobal('fetch', fetchMock);

      await expect(stockService.getLivePrice('FAIL_CONN', true)).rejects.toThrow(
        'Unable to connect to server. Please ensure the backend is running.'
      );
    });

    it('throws timeout error when request times out', async () => {
      const fetchMock = vi.fn().mockRejectedValue(new Error('Request timed out.'));
      vi.stubGlobal('fetch', fetchMock);

      await expect(stockService.getLivePrice('TIMEOUT_TEST', true)).rejects.toThrow(
        'Request timed out. Please try again.'
      );
    });

    it('throws error when server responds with HTTP non-ok status', async () => {
      const fetchMock = vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: async () => ({ message: 'Stock not found' })
      });
      vi.stubGlobal('fetch', fetchMock);

      await expect(stockService.getLivePrice('UNKNOWN_SYM', true)).rejects.toThrow('Stock not found');
    });

    it('deduplicates concurrent in-flight requests for the same symbol', async () => {
      let resolveFetch: (value: any) => void;
      const delayedPromise = new Promise((resolve) => {
        resolveFetch = resolve;
      });

      const fetchMock = vi.fn().mockImplementation(() => delayedPromise);
      vi.stubGlobal('fetch', fetchMock);

      const p1 = stockService.getLivePrice('DEDUP_TEST', true);
      const p2 = stockService.getLivePrice('DEDUP_TEST', false);

      resolveFetch!({
        ok: true,
        status: 200,
        json: async () => ({
          success: true,
          data: {
            symbol: 'DEDUP_TEST',
            price: 50,
            company_name: 'Dedup Inc',
            currency: 'USD',
            timestamp: '2026-10-06T10:00:00Z',
            source: 'test'
          }
        })
      });

      const [res1, res2] = await Promise.all([p1, p2]);
      expect(fetchMock).toHaveBeenCalledTimes(1);
      expect(res1.symbol).toBe('DEDUP_TEST');
      expect(res2.symbol).toBe('DEDUP_TEST');
    });
  });

  describe('getStockInfo', () => {
    it('throws error when symbol is empty', async () => {
      await expect(stockService.getStockInfo('')).rejects.toThrow('Stock symbol is required');
    });

    it('constructs correct URL and returns metadata on success', async () => {
      const mockInfo = {
        symbol: 'GOOGL',
        company_name: 'Alphabet Inc.',
        sector: 'Technology',
        market_cap: '2T',
        headquarters: 'Mountain View, CA',
        exchange: 'NASDAQ',
        category: 'Tech'
      };

      const fetchMock = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          success: true,
          data: mockInfo
        })
      });
      vi.stubGlobal('fetch', fetchMock);

      const result = await stockService.getStockInfo('googl');
      expect(fetchMock).toHaveBeenCalledTimes(1);
      expect(fetchMock.mock.calls[0][0]).toContain('/stock_info?symbol=GOOGL');
      expect(result).toEqual(mockInfo);
    });

    it('handles server failure with custom message', async () => {
      const fetchMock = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Error',
        json: async () => ({ message: 'Database connection failed' })
      });
      vi.stubGlobal('fetch', fetchMock);

      await expect(stockService.getStockInfo('ERR_TEST')).rejects.toThrow('Database connection failed');
    });
  });

  describe('getStockData', () => {
    it('formats USD live price into StockData model and computes changes', async () => {
      const mockLivePrice = {
        symbol: 'AMZN',
        company_name: 'Amazon.com Inc.',
        price: 180,
        open: 175,
        high: 182,
        low: 174,
        volume: 1234567,
        market_cap: '1.8T',
        timestamp: '2026-10-06T10:00:00Z',
        currency: 'USD',
        source: 'test'
      };

      vi.spyOn(stockService, 'getLivePrice').mockResolvedValue(mockLivePrice);

      const data = await stockService.getStockData('AMZN');
      expect(data.symbol).toBe('AMZN');
      expect(data.price).toBe(180);
      expect(data.open).toBe(175);
      expect(data.change).toBe(5);
      expect(data.changePercent).toBeCloseTo((5 / 175) * 100);
      expect(data.volume).toBe(1234567);
      expect(data.marketCap).toBe('1.8T');
    });

    it('converts INR price and open/high/low to USD using exchange rate', async () => {
      const mockLivePrice = {
        symbol: 'TCS.NS',
        company_name: 'Tata Consultancy Services',
        price: 4000,
        price_usd: 48,
        open: 3900,
        high: 4100,
        low: 3850,
        exchange_rate: 83.33,
        volume: 500000,
        timestamp: '2026-10-06T10:00:00Z',
        currency: 'INR',
        source: 'test'
      };

      vi.spyOn(stockService, 'getLivePrice').mockResolvedValue(mockLivePrice);

      const data = await stockService.getStockData('TCS.NS');
      expect(data.price).toBe(48);
      expect(data.open).toBeCloseTo(3900 / 83.33);
      expect(data.high).toBeCloseTo(4100 / 83.33);
      expect(data.low).toBeCloseTo(3850 / 83.33);
    });
  });

  describe('getHistoricalData', () => {
    it('throws error when symbol is empty', async () => {
      await expect(stockService.getHistoricalData('', 'year')).rejects.toThrow('Stock symbol is required');
    });

    it('fetches historical price points and appends today live price if missing', async () => {
      const mockPoints = [
        {
          date: '2026-10-01',
          open: 100,
          high: 105,
          low: 99,
          close: 104,
          volume: 1000,
          currency: 'USD'
        }
      ];

      const fetchMock = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          success: true,
          data: mockPoints
        })
      });
      vi.stubGlobal('fetch', fetchMock);

      vi.spyOn(stockService, 'getLivePrice').mockResolvedValue({
        symbol: 'HIST_TEST',
        price: 110,
        company_name: 'Hist Inc',
        currency: 'USD',
        timestamp: '2026-10-06T10:00:00Z',
        source: 'test'
      });

      const result = await stockService.getHistoricalData('HIST_TEST', 'year');
      expect(fetchMock.mock.calls[0][0]).toContain('/historical?symbol=HIST_TEST&period=year');
      expect(result.length).toBeGreaterThanOrEqual(1);
      expect(result[0].price).toBe(104);
    });

    it('falls back to 1-year data when 5-year data returns empty array', async () => {
      let callCount = 0;
      const fetchMock = vi.fn().mockImplementation((url: string) => {
        callCount++;
        if (url.includes('period=5year')) {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: async () => ({ success: true, data: [] })
          });
        }
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            success: true,
            data: [
              {
                date: '2026-05-01',
                open: 50,
                high: 52,
                low: 49,
                close: 51,
                volume: 500,
                currency: 'USD'
              }
            ]
          })
        });
      });
      vi.stubGlobal('fetch', fetchMock);
      vi.spyOn(stockService, 'getLivePrice').mockRejectedValue(new Error('no live price'));

      const result = await stockService.getHistoricalData('FALLBACK_SYM', '5year');
      expect(callCount).toBe(2);
      expect(result).toHaveLength(1);
      expect(result[0].close).toBe(51);
    });
  });

  describe('checkHealth', () => {
    it('constructs /health URL and returns health status on success', async () => {
      const fetchMock = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          success: true,
          data: { status: 'healthy', timestamp: '2026-10-06T12:00:00Z' }
        })
      });
      vi.stubGlobal('fetch', fetchMock);

      const health = await stockService.checkHealth();
      expect(fetchMock.mock.calls[0][0]).toContain('/health');
      expect(health.status).toBe('healthy');
    });

    it('throws server unavailable error when health check fails', async () => {
      const fetchMock = vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
        statusText: 'Service Unavailable'
      });
      vi.stubGlobal('fetch', fetchMock);

      await expect(stockService.checkHealth()).rejects.toThrow('Backend server is unavailable');
    });
  });

  describe('getPrediction', () => {
    it('constructs correct query params including horizon, model, and current price', async () => {
      const mockPredictionResponse = {
        predicted_price: 155.0,
        current_price: 150.0,
        confidence: 0.88,
        model_info: { model: 'LinearRegression' },
        time_frame_days: 7,
        data_points_used: 120,
        last_updated: '2026-10-06T10:00:00Z',
        currency: 'USD',
        data_source: 'live_api',
        data_date: null
      };

      const fetchMock = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => mockPredictionResponse
      });
      vi.stubGlobal('fetch', fetchMock);

      const prediction = await stockService.getPrediction('AAPL', '7d', 'LinearRegression', 150.0);

      expect(fetchMock).toHaveBeenCalledTimes(1);
      const url = new URL(fetchMock.mock.calls[0][0]);
      expect(url.pathname).toBe('/api/predict');
      expect(url.searchParams.get('symbol')).toBe('AAPL');
      expect(url.searchParams.get('horizon')).toBe('7d');
      expect(url.searchParams.get('model')).toBe('LinearRegression');
      expect(url.searchParams.get('current_price')).toBe('150');

      expect(prediction.predictedPrice).toBe(155.0);
      expect(prediction.currentPrice).toBe(150.0);
      expect(prediction.confidence).toBe(0.88);
      expect(prediction.model).toBe('LinearRegression');
      expect(prediction.sourceReliable).toBe(true);
    });

    it('wraps network or backend error into meaningful prediction failure error', async () => {
      const fetchMock = vi.fn().mockResolvedValue({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        json: async () => ({ error: 'Insufficient historical data for symbol' })
      });
      vi.stubGlobal('fetch', fetchMock);

      await expect(stockService.getPrediction('BAD_SYM', '1d')).rejects.toThrow(
        'Prediction failed: Insufficient historical data for symbol'
      );
    });
  });

  describe('getPopularStocks', () => {
    it('returns the predefined list of popular stocks', async () => {
      const list = await stockService.getPopularStocks();
      expect(list.length).toBeGreaterThan(0);
      expect(list.map((s) => s.symbol)).toContain('AAPL');
      expect(list.map((s) => s.symbol)).toContain('TSLA');
    });
  });
});
