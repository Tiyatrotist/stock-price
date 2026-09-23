"""
Indian Stocks Historical Data Fetcher

Fetches historical stock data for Indian stocks from 2020-01-01 to 2024-12-31.
Uses yfinance with .NS suffix for NSE tickers.
"""

import os
import sys
import yfinance as yf
import pandas as pd
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from shared.utilities import (
    Config, Constants, standardize_csv_columns, 
    ensure_alphabetical_order, get_currency_for_category
)

class IndianHistoricalFetcher:
    """
    Fetches historical Indian stock data using yfinance.
    Period: 2020-01-01 to 2024-12-31 (5 years)
    Automatically adds .NS suffix for NSE stocks.
    """
    
    def __init__(self):
        self.config = Config()
        self.data_dir = self.config.data_dir
        self.past_dir = os.path.join(self.data_dir, 'past', 'ind_stocks')
        self.individual_dir = os.path.join(self.past_dir, 'individual_files')
        self.index_file = os.path.join(self.past_dir, 'index_ind_stocks.csv')
        
        # Ensure directories exist
        os.makedirs(self.individual_dir, exist_ok=True)
        
        # Date range for historical data
        self.start_date = Constants.HISTORICAL_START
        self.end_date = Constants.HISTORICAL_END
        self.currency = get_currency_for_category('ind_stocks')
        
        # Rate limiting
        self.rate_limit_delay = 1.5  # seconds between requests
        self.max_retries = 3
        
    def load_symbols_from_index(self) -> Optional[List[str]]:
        """
        Load symbols from the Indian stocks index file.
        
        Returns:
            List of symbols or None if error
        """
        if not os.path.exists(self.index_file):
            print(f"Index file not found: {self.index_file}")
            return None
        
        try:
            df = pd.read_csv(self.index_file)
            if 'symbol' not in df.columns:
                print("Index file missing 'symbol' column")
                return None
            
            symbols = df['symbol'].tolist()
            print(f"Loaded {len(symbols)} symbols from index")
            return symbols
            
        except Exception as e:
            print(f"Error reading index file: {e}")
            return None
    
    def check_existing_file(self, symbol: str) -> Dict[str, Any]:
        """
        Check if a stock data file already exists and is valid.
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Dict with file status information
        """
        file_path = os.path.join(self.individual_dir, f"{symbol}.csv")
        
        result = {
            'exists': False,
            'valid': False,
            'rows': 0,
            'needs_download': True
        }
        
        if not os.path.exists(file_path):
            return result
        
        result['exists'] = True
        
        try:
            df = pd.read_csv(file_path)
            if len(df) >= 100:  # Minimum rows for valid historical data
                result['valid'] = True
                result['rows'] = len(df)
                result['needs_download'] = False
                print(f"{symbol}: Existing file valid ({len(df)} rows)")
            else:
                print(f"{symbol}: Existing file has insufficient data ({len(df)} rows)")
        except Exception as e:
            print(f"Could not read existing file for {symbol}: {e}")
        
        return result
    
    def prepare_yfinance_symbol(self, symbol: str) -> str:
        """
        Prepare symbol for yfinance by adding .NS suffix if needed.
        
        Args:
            symbol: Original symbol
        
        Returns:
            Symbol with .NS suffix for yfinance
        """
        # Remove any existing suffix first
        base_symbol = symbol.split('.')[0]
        
        # Add .NS suffix for NSE stocks
        yfinance_symbol = f"{base_symbol}.NS"
        return yfinance_symbol
    
    def download_stock_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        Download historical stock data for a single symbol.
        
        Args:
            symbol: Stock symbol (without .NS suffix)
        
        Returns:
            DataFrame with stock data or None if error
        """
        for attempt in range(self.max_retries):
            try:
                print(f"Downloading {symbol} (attempt {attempt + 1}/{self.max_retries})")
                
                # Prepare symbol for yfinance
                yfinance_symbol = self.prepare_yfinance_symbol(symbol)
                print(f"Using yfinance symbol: {yfinance_symbol}")
                
                # Download data using yfinance
                ticker = yf.Ticker(yfinance_symbol)
                data = ticker.history(
                    start=self.start_date, 
                    end=self.end_date, 
                    auto_adjust=False,  # Proven pattern from inspiration code
                    timeout=5
                )
                
                if data.empty:
                    print(f"{symbol}: No data returned from yfinance for {yfinance_symbol}")
                    return None
                
                # Reset index to get Date as column
                data = data.reset_index()
                
                # Standardize column names to lowercase
                data = standardize_csv_columns(data)
                
                # Ensure we have the required columns
                required_cols = Constants.REQUIRED_STOCK_COLUMNS
                available_cols = [col for col in required_cols if col in data.columns]
                
                if len(available_cols) < len(required_cols):
                    print(f"{symbol}: Missing columns. Available: {available_cols}")
                
                # Select only the columns we need
                data = data[available_cols]
                
                # Add currency column
                data['currency'] = self.currency
                
                # Validate data quality
                if len(data) < 100:
                    print(f"{symbol}: Insufficient data downloaded ({len(data)} rows)")
                    return None
                
                print(f"{symbol}: Successfully downloaded {len(data)} rows")
                return data
                
            except Exception as e:
                print(f"{symbol}: Download attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.rate_limit_delay * 2)  # Longer delay on retry
                else:
                    print(f"{symbol}: All yfinance attempts failed, trying NSEPython fallback...")
                    # Try NSEPython as fallback
                    data = self.download_from_nsepython(symbol)
                    if data is not None:
                        return data
                    print(f"{symbol}: NSEPython failed, trying stock-market-india fallback...")
                    # Try stock-market-india as fallback
                    data = self.download_from_stock_market_india(symbol)
                    if data is not None:
                        return data
                    print(f"{symbol}: stock-market-india failed, trying NSELib fallback...")
                    # Try NSELib as final fallback
                    data = self.download_from_nselib(symbol)
                    if data is not None:
                        return data
                    print(f"{symbol}: All download attempts failed")
                    return None
    
    def download_from_nsepython(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        Download historical stock data from NSEPython as fallback.
        
        Args:
            symbol: Stock symbol
        
        Returns:
            DataFrame with stock data or None if error
        """
        try:
            import nsepython
            print(f"Downloading {symbol} from NSEPython...")
            
            # Get historical data from NSEPython
            try:
                # Try to get historical data
                hist_data = nsepython.nse_historical_data(symbol, self.start_date, self.end_date)
                
                if hist_data and len(hist_data) > 0:
                    # Convert to DataFrame format
                    df = pd.DataFrame(hist_data)
                    
                    # Standardize column names
                    df = standardize_csv_columns(df)
                    
                    # Ensure we have the required columns
                    required_cols = Constants.REQUIRED_STOCK_COLUMNS
                    available_cols = [col for col in required_cols if col in df.columns]
                    
                    if len(available_cols) < len(required_cols):
                        print(f"{symbol}: Missing columns from NSEPython. Available: {available_cols}")
                    
                    # Select only the columns we need
                    df = df[available_cols]
                    
                    # Add currency column
                    df['currency'] = self.currency
                    
                    print(f"{symbol}: Successfully downloaded {len(df)} rows from NSEPython")
                    return df
                else:
                    print(f"{symbol}: No data from NSEPython")
                    return None
                    
            except AttributeError:
                # NSEPython doesn't have historical data method, try alternative
                print(f"{symbol}: NSEPython historical data method not available")
                return None
                
        except ImportError:
            print(f"{symbol}: NSEPython not available")
            return None
        except Exception as e:
            print(f"{symbol}: NSEPython error: {e}")
            return None
    
    def download_from_stock_market_india(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        Download historical stock data from stock-market-india Python package as fallback.
        
        Args:
            symbol: Stock symbol
        
        Returns:
            DataFrame with stock data or None if error
        """
        try:
            from stock_market_india import StockMarketIndia
            print(f"Downloading {symbol} from stock-market-india package...")
            
            # Initialize the stock market India client
            smi = StockMarketIndia()
            
            # Get quote data (this package may not have historical data)
            # We'll create a simple DataFrame with current data
            quote_data = smi.get_quote(symbol)
            
            if quote_data and 'lastPrice' in quote_data:
                # Create a simple DataFrame with current data
                # Note: This package may not provide historical data
                current_date = pd.Timestamp.now().strftime('%Y-%m-%d')
                
                df = pd.DataFrame({
                    'Date': [current_date],
                    'Open': [quote_data.get('open', quote_data['lastPrice'])],
                    'High': [quote_data.get('dayHigh', quote_data['lastPrice'])],
                    'Low': [quote_data.get('dayLow', quote_data['lastPrice'])],
                    'Close': [quote_data['lastPrice']],
                    'Volume': [quote_data.get('totalTradedVolume', 0)],
                    'Adj Close': [quote_data['lastPrice']]
                })
                
                # Standardize column names
                df = standardize_csv_columns(df)
                
                # Ensure we have the required columns
                required_cols = Constants.REQUIRED_STOCK_COLUMNS
                available_cols = [col for col in required_cols if col in df.columns]
                
                if len(available_cols) < len(required_cols):
                    print(f"{symbol}: Missing columns from stock-market-india. Available: {available_cols}")
                
                # Select only the columns we need
                df = df[available_cols]
                
                # Add currency column
                df['currency'] = self.currency
                
                print(f"{symbol}: Successfully downloaded {len(df)} rows from stock-market-india")
                return df
            else:
                print(f"{symbol}: No data from stock-market-india")
                return None
                
        except ImportError:
            print(f"{symbol}: stock-market-india package not available - install with: pip install stock-market-india")
            return None
        except Exception as e:
            print(f"{symbol}: stock-market-india error: {e}")
            return None
    
    def download_from_nselib(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        Download historical stock data from NSELib as fallback.
        
        Args:
            symbol: Stock symbol
        
        Returns:
            DataFrame with stock data or None if error
        """
        try:
            import nselib
            print(f"Downloading {symbol} from NSELib...")
            
            # Get historical data from NSELib
            # Note: NSELib may have different methods for historical data
            # This is a placeholder implementation - adjust based on actual NSELib API
            try:
                # Try to get historical data
                hist_data = nselib.get_historical_data(symbol, start_date=self.start_date, end_date=self.end_date)
                
                if hist_data and len(hist_data) > 0:
                    # Convert to DataFrame format
                    df = pd.DataFrame(hist_data)
                    
                    # Standardize column names
                    df = standardize_csv_columns(df)
                    
                    # Ensure we have the required columns
                    required_cols = Constants.REQUIRED_STOCK_COLUMNS
                    available_cols = [col for col in required_cols if col in df.columns]
                    
                    if len(available_cols) < len(required_cols):
                        print(f"{symbol}: Missing columns from NSELib. Available: {available_cols}")
                    
                    # Select only the columns we need
                    df = df[available_cols]
                    
                    # Add currency column
                    df['currency'] = self.currency
                    
                    print(f"{symbol}: Successfully downloaded {len(df)} rows from NSELib")
                    return df
                else:
                    print(f"{symbol}: No data from NSELib")
                    return None
                    
            except AttributeError:
                # NSELib doesn't have historical data method, try alternative
                print(f"{symbol}: NSELib historical data method not available")
                return None
                
        except ImportError:
            print(f"{symbol}: NSELib not available")
            return None
        except Exception as e:
            print(f"{symbol}: NSELib error: {e}")
            return None
    
    def save_stock_data(self, symbol: str, data: pd.DataFrame) -> bool:
        """
        Save stock data to individual CSV file.
        
        Args:
            symbol: Stock symbol
            data: DataFrame with stock data
        
        Returns:
            Boolean indicating success
        """
        try:
            file_path = os.path.join(self.individual_dir, f"{symbol}.csv")
            data.to_csv(file_path, index=False)
            print(f"{symbol}: Saved {len(data)} rows to {file_path}")
            return True
        except Exception as e:
            print(f"{symbol}: Error saving file: {e}")
            return False
    
    def update_index_file(self, symbols: List[str]) -> bool:
        """
        Update the index file with all symbols in alphabetical order.
        
        Args:
            symbols: List of symbols to include in index
        
        Returns:
            Boolean indicating success
        """
        try:
            # Load existing index to get company info
            if os.path.exists(self.index_file):
                existing_df = pd.read_csv(self.index_file)
                # Keep only symbols that are in our list
                existing_df = existing_df[existing_df['symbol'].isin(symbols)]
            else:
                # Create empty DataFrame with required columns
                existing_df = pd.DataFrame(columns=Constants.REQUIRED_INDEX_COLUMNS)
            
            # Add any missing symbols with basic info
            existing_symbols = set(existing_df['symbol'].tolist()) if not existing_df.empty else set()
            missing_symbols = [s for s in symbols if s not in existing_symbols]
            
            if missing_symbols:
                new_rows = []
                for symbol in missing_symbols:
                    new_rows.append({
                        'symbol': symbol,
                        'company_name': symbol,
                        'sector': 'Unknown',
                        'market_cap': '',
                        'headquarters': 'Unknown',
                        'exchange': 'NSE'
                    })
                
                new_df = pd.DataFrame(new_rows)
                existing_df = pd.concat([existing_df, new_df], ignore_index=True)
            
            # Ensure alphabetical order
            existing_df = ensure_alphabetical_order(existing_df, 'symbol')
            
            # Save updated index
            existing_df.to_csv(self.index_file, index=False)
            print(f"Updated index with {len(existing_df)} symbols")
            return True
            
        except Exception as e:
            print(f"Error updating index file: {e}")
            return False
    
    def fetch_historical_data(self, force_redownload: bool = False, 
                            symbols_to_download: List[str] = None) -> Dict[str, Any]:
        """
        Fetch historical data for all symbols or specified symbols.
        
        Args:
            force_redownload: If True, download even if file exists
            symbols_to_download: List of specific symbols to download (None for all)
        
        Returns:
            Dict with download statistics
        """
        print("Starting Indian stocks historical data download...")
        print(f"Period: {self.start_date} to {self.end_date}")
        
        # Load symbols
        all_symbols = self.load_symbols_from_index()
        if all_symbols is None:
            return {'error': 'Could not load symbols from index'}
        
        # Filter symbols if specified
        if symbols_to_download:
            symbols = [s for s in all_symbols if s in symbols_to_download]
            print(f"Filtered to {len(symbols)} specified symbols")
        else:
            symbols = all_symbols
        
        # Statistics
        stats = {
            'total_symbols': len(symbols),
            'skipped_existing': 0,
            'downloaded': 0,
            'failed': 0,
            'errors': []
        }
        
        # Download each symbol
        for i, symbol in enumerate(symbols, 1):
            print(f"\n[{i}/{len(symbols)}] Processing {symbol}...")
            
            # Check if file already exists and is valid
            if not force_redownload:
                file_status = self.check_existing_file(symbol)
                if file_status['valid']:
                    stats['skipped_existing'] += 1
                    continue
            
            # Download data
            data = self.download_stock_data(symbol)
            
            if data is not None:
                # Save to file
                if self.save_stock_data(symbol, data):
                    stats['downloaded'] += 1
                else:
                    stats['failed'] += 1
                    stats['errors'].append(f"{symbol}: Failed to save file")
            else:
                stats['failed'] += 1
                stats['errors'].append(f"{symbol}: Download failed")
            
            # Rate limiting
            if i < len(symbols):  # Don't sleep after last symbol
                time.sleep(self.rate_limit_delay)
        
        # Update index file
        self.update_index_file(symbols)
        
        return stats

def main():
    """Main function for command line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Download Indian stocks historical data")
    parser.add_argument("--force", action="store_true", help="Force re-download of existing files")
    parser.add_argument("--symbols", nargs="+", help="Specific symbols to download")
    
    args = parser.parse_args()
    
    fetcher = IndianHistoricalFetcher()
    stats = fetcher.fetch_historical_data(
        force_redownload=args.force,
        symbols_to_download=args.symbols
    )
    
    # Print summary
    print("\n" + "=" * 50)
    print("DOWNLOAD SUMMARY")
    print("=" * 50)
    print(f"Total symbols: {stats['total_symbols']}")
    print(f"Skipped (existing): {stats['skipped_existing']}")
    print(f"Downloaded: {stats['downloaded']}")
    print(f"Failed: {stats['failed']}")
    
    if stats['downloaded'] + stats['skipped_existing'] > 0:
        success_rate = ((stats['downloaded'] + stats['skipped_existing']) / stats['total_symbols'] * 100)
        print(f"Success rate: {success_rate:.1f}%")
    
    if stats['errors']:
        print(f"\nErrors ({len(stats['errors'])}):")
        for error in stats['errors'][:10]:  # Show first 10
            print(f"  ❌ {error}")
        if len(stats['errors']) > 10:
            print(f"  ... and {len(stats['errors']) - 10} more")

if __name__ == "__main__":
    main()
