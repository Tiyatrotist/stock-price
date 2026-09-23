import React from 'react';
import { DollarSign, IndianRupee } from 'lucide-react';
import { Button } from './ui/button';

interface CurrencyToggleProps {
  currency: 'USD' | 'INR';
  onCurrencyChange: (currency: 'USD' | 'INR') => void;
}

export function CurrencyToggle({ currency, onCurrencyChange }: CurrencyToggleProps) {
  return (
    <div className="flex bg-muted p-1 rounded-md">
      <Button
        variant={currency === 'USD' ? 'default' : 'ghost'}
        size="sm"
        onClick={() => onCurrencyChange('USD')}
        className="h-8 px-3 gap-1"
        aria-label="Switch display currency to USD"
        aria-pressed={currency === 'USD'}
        title="Switch display currency to USD"
      >
        <DollarSign className="h-4 w-4" />
        USD
      </Button>
      <Button
        variant={currency === 'INR' ? 'default' : 'ghost'}
        size="sm"
        onClick={() => onCurrencyChange('INR')}
        className="h-8 px-3 gap-1"
        aria-label="Switch display currency to INR"
        aria-pressed={currency === 'INR'}
        title="Switch display currency to INR"
      >
        <IndianRupee className="h-4 w-4" />
        INR
      </Button>
    </div>
  );
}
