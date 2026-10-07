import { describe, expect, test } from 'vitest';

import {
  convertPrice,
  formatCompactNumber,
  formatPrice,
  formatPriceDirect,
  getCurrencySymbol,
  getExchangeRate,
  setExchangeRate,
} from './currency';

describe('currency utilities', () => {
  test('convertPrice handles missing and invalid prices', () => {
    expect(convertPrice(null, 'USD', 'INR', 80)).toBe(0);
    expect(convertPrice(undefined, 'USD', 'INR', 80)).toBe(0);
    expect(convertPrice(Number.NaN, 'USD', 'INR', 80)).toBe(0);
  });

  test('convertPrice converts both directions with an explicit rate', () => {
    expect(convertPrice(10, 'USD', 'INR', 80)).toBe(800);
    expect(convertPrice(800, 'INR', 'USD', 80)).toBe(10);
    expect(convertPrice(-10, 'USD', 'INR', 80)).toBe(-800);
    expect(convertPrice(12.5, 'USD', 'USD', 80)).toBe(12.5);
  });

  test('setExchangeRate accepts only finite positive rates', () => {
    setExchangeRate(84.25);
    expect(getExchangeRate()).toBe(84.25);

    setExchangeRate(0);
    setExchangeRate(-1);
    setExchangeRate(Number.NaN);
    setExchangeRate(Number.POSITIVE_INFINITY);

    expect(getExchangeRate()).toBe(84.25);
  });

  test('formatPrice handles zero-like input and currencies', () => {
    expect(formatPrice(null, 'USD')).toBe('$0.00');
    expect(formatPrice(undefined, 'INR')).toBe('₹0.00');
    expect(formatPrice(Number.NaN, 'USD')).toBe('$0.00');
    expect(formatPrice(12.5, 'USD')).toBe('$12.50');
    expect(formatPrice(-12.5, 'USD')).toBe('$-12.50');
    expect(formatPrice(10, 'INR', 80)).toBe('₹800.00');
  });

  test('formatPriceDirect formats already-converted values without conversion', () => {
    expect(formatPriceDirect(1234.5, 'USD')).toBe('$1234.50');
    expect(formatPriceDirect(1234.5, 'INR')).toBe('₹1,234.50');
    expect(formatPriceDirect(null, 'INR')).toBe('₹0.00');
  });

  test('getCurrencySymbol returns the expected display symbol', () => {
    expect(getCurrencySymbol('USD')).toBe('$');
    expect(getCurrencySymbol('INR')).toBe('₹');
  });

  test('formatCompactNumber handles edge cases and compact notation', () => {
    expect(formatCompactNumber(null)).toBe('N/A');
    expect(formatCompactNumber(undefined)).toBe('N/A');
    expect(formatCompactNumber(Number.NaN)).toBe('N/A');
    expect(formatCompactNumber(1_200)).toBe('1.2K');
    expect(formatCompactNumber(-1_200)).toBe('-1.2K');
  });
});
