// Exchange rate USD to INR (fallback rate when backend doesn't provide live rate)
// The backend fetches live exchange rates, this is used as fallback only
const USD_TO_INR_RATE = 83.5;

export type Currency = 'USD' | 'INR';

// Global exchange rate from backend
let currentExchangeRate: number | null = null;

export function setExchangeRate(rate: number): void {
  if (typeof rate === 'number' && !isNaN(rate) && isFinite(rate) && rate > 0) {
    currentExchangeRate = rate;
  }
}

export function getExchangeRate(): number {
  return currentExchangeRate || USD_TO_INR_RATE;
}

export function convertPrice(price: number | undefined | null, fromCurrency: Currency = 'USD', toCurrency: Currency = 'USD', exchangeRate?: number): number {
  // Handle null/undefined prices
  if (price == null || isNaN(price)) {
    return 0;
  }
  
  if (fromCurrency === toCurrency) {
    return price;
  }
  
  const rate = exchangeRate || getExchangeRate();
  
  if (fromCurrency === 'USD' && toCurrency === 'INR') {
    return price * rate;
  }
  
  if (fromCurrency === 'INR' && toCurrency === 'USD') {
    return price / rate;
  }
  
  return price;
}

export function formatPrice(price: number | undefined | null, currency: Currency = 'USD', exchangeRate?: number): string {
  // Handle null/undefined prices
  if (price == null || isNaN(price)) {
    return currency === 'INR' ? '₹0.00' : '$0.00';
  }
  
  const converted = convertPrice(price, 'USD', currency, exchangeRate);
  
  if (currency === 'INR') {
    // Use Indian number formatting with proper lakh/crore notation
    return `₹${converted.toLocaleString('en-IN', { 
      maximumFractionDigits: 2,
      minimumFractionDigits: 2
    })}`;
  }
  
  return `$${converted.toFixed(2)}`;
}

// Format price without conversion (for already converted prices)
export function formatPriceDirect(price: number | undefined | null, currency: Currency = 'USD'): string {
  // Handle null/undefined prices
  if (price == null || isNaN(price)) {
    return currency === 'INR' ? '₹0.00' : '$0.00';
  }
  
  if (currency === 'INR') {
    // Use Indian number formatting with proper lakh/crore notation
    return `₹${price.toLocaleString('en-IN', { 
      maximumFractionDigits: 2,
      minimumFractionDigits: 2
    })}`;
  }
  
  return `$${price.toFixed(2)}`;
}

export function getCurrencySymbol(currency: Currency): string {
  return currency === 'USD' ? '$' : '₹';
}
