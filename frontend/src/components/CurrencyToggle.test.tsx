import '@testing-library/jest-dom/vitest';

import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, test, vi } from 'vitest';

import { CurrencyToggle } from './CurrencyToggle';

afterEach(() => {
  cleanup();
});

describe('CurrencyToggle', () => {
  test('shows the current currency as selected', () => {
    render(
      <CurrencyToggle
        currency="USD"
        onCurrencyChange={vi.fn()}
      />
    );

    expect(
      screen.getByRole('button', { name: 'Switch display currency to USD' })
    ).toHaveAttribute('aria-pressed', 'true');

    expect(
      screen.getByRole('button', { name: 'Switch display currency to INR' })
    ).toHaveAttribute('aria-pressed', 'false');
  });

  test('calls onCurrencyChange when a currency button is clicked', () => {
    const onCurrencyChange = vi.fn();

    render(
      <CurrencyToggle
        currency="USD"
        onCurrencyChange={onCurrencyChange}
      />
    );

    fireEvent.click(
      screen.getByRole('button', { name: 'Switch display currency to INR' })
    );

    expect(onCurrencyChange).toHaveBeenCalledTimes(1);
    expect(onCurrencyChange).toHaveBeenCalledWith('INR');
  });
});
