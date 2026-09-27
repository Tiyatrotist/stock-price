import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import { fileURLToPath, pathToFileURL } from 'node:url';

import { transformWithEsbuild } from 'vite';

const sourceUrl = new URL('../src/utils/currency.ts', import.meta.url);
const sourcePath = fileURLToPath(sourceUrl);
const source = await readFile(sourcePath, 'utf8');
const { code } = await transformWithEsbuild(source, sourcePath, {
  loader: 'ts',
  format: 'esm',
});
const moduleUrl = `data:text/javascript;base64,${Buffer.from(code).toString('base64')}`;
const currency = await import(moduleUrl);

test('convertPrice handles missing and invalid prices', () => {
  assert.equal(currency.convertPrice(null, 'USD', 'INR', 80), 0);
  assert.equal(currency.convertPrice(undefined, 'USD', 'INR', 80), 0);
  assert.equal(currency.convertPrice(Number.NaN, 'USD', 'INR', 80), 0);
});

test('convertPrice converts both directions with an explicit rate', () => {
  assert.equal(currency.convertPrice(10, 'USD', 'INR', 80), 800);
  assert.equal(currency.convertPrice(800, 'INR', 'USD', 80), 10);
  assert.equal(currency.convertPrice(-10, 'USD', 'INR', 80), -800);
  assert.equal(currency.convertPrice(12.5, 'USD', 'USD', 80), 12.5);
});

test('setExchangeRate accepts only finite positive rates', () => {
  currency.setExchangeRate(84.25);
  assert.equal(currency.getExchangeRate(), 84.25);

  currency.setExchangeRate(0);
  currency.setExchangeRate(-1);
  currency.setExchangeRate(Number.NaN);
  currency.setExchangeRate(Number.POSITIVE_INFINITY);

  assert.equal(currency.getExchangeRate(), 84.25);
});

test('formatPrice handles zero-like input and currencies', () => {
  assert.equal(currency.formatPrice(null, 'USD'), '$0.00');
  assert.equal(currency.formatPrice(undefined, 'INR'), '₹0.00');
  assert.equal(currency.formatPrice(Number.NaN, 'USD'), '$0.00');
  assert.equal(currency.formatPrice(12.5, 'USD'), '$12.50');
  assert.equal(currency.formatPrice(-12.5, 'USD'), '$-12.50');
  assert.equal(currency.formatPrice(10, 'INR', 80), '₹800.00');
});

test('formatPriceDirect formats already-converted values without conversion', () => {
  assert.equal(currency.formatPriceDirect(1234.5, 'USD'), '$1234.50');
  assert.equal(currency.formatPriceDirect(1234.5, 'INR'), '₹1,234.50');
  assert.equal(currency.formatPriceDirect(null, 'INR'), '₹0.00');
});

test('getCurrencySymbol returns the expected display symbol', () => {
  assert.equal(currency.getCurrencySymbol('USD'), '$');
  assert.equal(currency.getCurrencySymbol('INR'), '₹');
});

test('formatCompactNumber handles edge cases and compact notation', () => {
  assert.equal(currency.formatCompactNumber(null), 'N/A');
  assert.equal(currency.formatCompactNumber(undefined), 'N/A');
  assert.equal(currency.formatCompactNumber(Number.NaN), 'N/A');
  assert.equal(currency.formatCompactNumber(1_200), '1.2K');
  assert.equal(currency.formatCompactNumber(-1_200), '-1.2K');
});
