"""
Indian Stocks Latest Data Fetcher

Fetches latest stock data for Indian stocks from 2025-01-01 to current date.
Uses yfinance as primary source.
Automatically adds .NS suffix for NSE stocks.
"""

import os
import sys
import yfinance as yf
import pandas as pd
import time
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, date

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from shared.utilities import (
    Config, Constants, standardize_csv_columns, 
    ensure_alphabetical_order, get_currency_for_category
)

class IndianLatestFetcher:
    """
    Fetches latest Indian stock data using yfinance.
    Period: 2025-01-01 to current date
    Automatically adds .NS suffix for NSE stocks.
    """
    
    def __init__(self):
        self.config = Config()
        self.data_dir = self.config.data_dir
        self.latest_dir = os.path.join(self.data_dir, 'latest', 'ind_stocks')
        self.individual_dir = os.path.join(self.latest_dir, 'individual_files')
        self.index_file = os.path.join(self.latest_dir, 'index_ind_stocks_latest.csv')
        
        # Ensure directories exist
        os.makedirs(self.individual_dir, exist_ok=True)
        
        # Date range for latest data
        self.start_date = Constants.LATEST_START
        self.end_date = date.today().strftime('%Y-%m-%d')
        self.currency = get_currency_for_category('ind_stocks')
        
        # API configurations
        
        # Rate limiting
        self.rate_limit_delay = 1.5  # seconds between requests
        self.max_retries = 3
    
        
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
        
    def load_symbols_from_index(self) -> Optional[List[str]]:
        """
        Load symbols from the Indian stocks index file.
        
        Returns:
            List of symbols or None if error
        """
        # Try latest index first, then fall back to past index
        past_index = os.path.join(self.data_dir, 'past', 'ind_stocks', 'index_ind_stocks.csv')
        
        index_file = self.index_file if os.path.exists(self.index_file) else past_index
        
        if not os.path.exists(index_file):
            print(f"Index file not found: {index_file}")
            return None
        
        try:
            df = pd.read_csv(index_file)
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
        Check if a stock data file already exists and is recent.
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Dict with file status information
        """
        file_path = os.path.join(self.individual_dir, f"{symbol}.csv")
        
        result = {
            'exists': False,
            'recent': False,
            'rows': 0,
            'needs_download': True
        }
        
        if not os.path.exists(file_path):
            return result
        
        result['exists'] = True
        
        try:
            df = pd.read_csv(file_path)
            if len(df) > 0:
                result['rows'] = len(df)
                
                # Check if the last date is recent (within last 7 days)
                last_date = pd.to_datetime(df['date'].iloc[-1])
                days_old = (datetime.now() - last_date).days
                
                if days_old <= 7:  # Data is recent
                    result['recent'] = True
                    result['needs_download'] = False
                    print(f"{symbol}: Existing file is recent ({days_old} days old)")
                else:
                    print(f"{symbol}: Existing file is outdated ({days_old} days old)")
            else:
                print(f"{symbol}: Existing file is empty")
        except Exception as e:
            print(f"Could not read existing file for {symbol}: {e}")
        
        return result
    
    def download_from_yfinance(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        Download latest stock data from yfinance.
        
        Args:
            symbol: Stock symbol
        
        Returns:
            DataFrame with stock data or None if error
        """
        for attempt in range(self.max_retries):
            try:
                print(f"Downloading {symbol} from yfinance (attempt {attempt + 1}/{self.max_retries})")
                
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
                
                print(f"{symbol}: Successfully downloaded {len(data)} rows from yfinance")
                return data
                
            except Exception as e:
                print(f"{symbol}: yfinance attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.rate_limit_delay * 2)
                else:
                    print(f"{symbol}: All yfinance attempts failed")
                    return None
    
    
    
    
    def download_stock_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        Download latest stock data with fallback strategy.
        
        Args:
            symbol: Stock symbol
        
        Returns:
            DataFrame with stock data or None if error
        """
        # Try yfinance
        data = self.download_from_yfinance(symbol)
        if data is not None:
            return data
        
        print(f"{symbol}: yfinance download failed")
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
        Update the latest index file with all symbols in alphabetical order.
        
        Args:
            symbols: List of symbols to include in index
        
        Returns:
            Boolean indicating success
        """
        try:
            # Load existing index to get company info
            past_index = os.path.join(self.data_dir, 'past', 'ind_stocks', 'index_ind_stocks.csv')
            
            if os.path.exists(past_index):
                existing_df = pd.read_csv(past_index)
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
            print(f"Updated latest index with {len(existing_df)} symbols")
            return True
            
        except Exception as e:
            print(f"Error updating latest index file: {e}")
            return False
    
    def fetch_latest_data(self, force_redownload: bool = False, 
                         symbols_to_download: List[str] = None) -> Dict[str, Any]:
        """
        Fetch latest data for all symbols or specified symbols.
        
        Args:
            force_redownload: If True, download even if file exists and is recent
            symbols_to_download: List of specific symbols to download (None for all)
        
        Returns:
            Dict with download statistics
        """
        print("Starting Indian stocks latest data download...")
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
            'skipped_recent': 0,
            'downloaded': 0,
            'failed': 0,
            'errors': []
        }
        
        # Download each symbol
        for i, symbol in enumerate(symbols, 1):
            print(f"\n[{i}/{len(symbols)}] Processing {symbol}...")
            
            # Check if file already exists and is recent
            if not force_redownload:
                file_status = self.check_existing_file(symbol)
                if file_status['recent']:
                    stats['skipped_recent'] += 1
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

    def fetch_recent_data_on_demand(self, symbol: str, period: str, existing_data: List[Dict]) -> List[Dict]:
        """
        Fetch recent data on-demand if existing data is insufficient for the period.
        
        Args:
            symbol: Stock symbol
            period: Requested period ('week', 'month', 'year', '5year')
            existing_data: List of existing price points
        
        Returns:
            List of additional price points or empty list if no fetch needed
        """
        try:
            # For 'year' period, use existing historical data to show last 12 months
            if period == 'year':
                print(f"Year period requested for {symbol}: using existing historical data for last 12 months")
                
                # Use fallback data strategy to get last year of historical data
                return self._get_fallback_data(symbol, period, existing_data)
            
            # For other periods, use the original logic
            # Determine minimum data points needed for meaningful charts
            min_points = {
                'week': 5,    # At least 5 trading days
                'month': 20,  # At least 20 trading days
                '5year': 100  # At least 100 trading days
            }
            
            # Check if we have enough data
            min_required = min_points.get(period, 1)
            print(f"Data check for {symbol} {period}: {len(existing_data)} points, need {min_required}")
            
            if len(existing_data) >= min_required:
                print(f"Sufficient data for {symbol} {period}: {len(existing_data)} points")
                return []
            
            print(f"Insufficient data for {symbol} {period}: {len(existing_data)} points, fetching recent data")
            
            # Prepare symbol for yfinance
            yfinance_symbol = self.prepare_yfinance_symbol(symbol)
            
            # Calculate date range for recent data
            from datetime import datetime, timedelta
            today = datetime.now().date()
            if period == 'week':
                start_date = today - timedelta(days=14)  # 2 weeks to ensure enough data
            elif period == 'month':
                start_date = today - timedelta(days=60)  # 2 months to ensure enough data
            else:  # 5year
                start_date = today - timedelta(days=2000)  # ~5.5 years
            
            # Try to fetch data from yfinance
            try:
                ticker = yf.Ticker(yfinance_symbol)
                data = ticker.history(
                    start=start_date.strftime('%Y-%m-%d'),
                    end=today.strftime('%Y-%m-%d'),
                    auto_adjust=False,
                    timeout=5
                )
                
                if data.empty:
                    print(f"No recent data found for {yfinance_symbol} from yfinance")
                    # Fallback: Use existing historical data with smart filtering
                    return self._get_fallback_data(symbol, period, existing_data)
            except Exception as e:
                print(f"yfinance error for {yfinance_symbol}: {e}")
                # Fallback: Use existing historical data with smart filtering
                return self._get_fallback_data(symbol, period, existing_data)
            
            # Convert to our format
            additional_points = []
            for date, row in data.iterrows():
                additional_points.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'open': float(row['Open']) if pd.notna(row['Open']) else None,
                    'high': float(row['High']) if pd.notna(row['High']) else None,
                    'low': float(row['Low']) if pd.notna(row['Low']) else None,
                    'close': float(row['Close']) if pd.notna(row['Close']) else None,
                    'volume': int(row['Volume']) if pd.notna(row['Volume']) else 0,
                    'currency': 'INR'
                })
            
            print(f"Fetched {len(additional_points)} additional data points for {symbol}")
            
            # Save to CSV file for future use
            try:
                latest_file = os.path.join(self.individual_dir, f'{symbol}.csv')
                
                # Read existing data
                if os.path.exists(latest_file):
                    existing_df = pd.read_csv(latest_file)
                else:
                    existing_df = pd.DataFrame()
                
                # Convert new data to DataFrame
                new_df = pd.DataFrame(additional_points)
                new_df['date'] = pd.to_datetime(new_df['date'])
                
                # Combine and remove duplicates
                if not existing_df.empty:
                    existing_df['date'] = pd.to_datetime(existing_df['date'])
                    combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                    combined_df = combined_df.drop_duplicates(subset=['date']).sort_values('date')
                else:
                    combined_df = new_df
                
                # Save back to file
                combined_df['date'] = combined_df['date'].dt.strftime('%Y-%m-%d')
                combined_df.to_csv(latest_file, index=False)
                print(f"Saved updated data to {latest_file}")
                
            except Exception as e:
                print(f"Could not save fetched data to CSV: {e}")
            
            return additional_points
            
        except Exception as e:
            print(f"Error fetching recent data for {symbol}: {e}")
            return []

    def _get_fallback_data(self, symbol: str, period: str, existing_data: List[Dict]) -> List[Dict]:
        """
        Fallback method to provide meaningful data when yfinance fails.
        Uses existing historical data with smart filtering.
        """
        try:
            print(f"Using fallback data strategy for {symbol} {period}")
            
            # Load historical data from past files
            # Get the project root directory (go up from backend/data_fetching/ind_stocks/latest_fetching)
            project_root = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')
            past_file = os.path.join(project_root, 'data', 'past', 'ind_stocks', 'individual_files', f'{symbol}.csv')
            
            if not os.path.exists(past_file):
                print(f"No historical data found for {symbol}")
                return []
            
            # Read historical data
            import pandas as pd
            df = pd.read_csv(past_file)
            df['date'] = pd.to_datetime(df['date'])
            
            # Filter to get recent data based on period
            from datetime import datetime, timedelta
            today = datetime.now().date()
            if period == 'week':
                # Get last 2 weeks of historical data, or last 10 trading days if no recent data
                start_date = today - timedelta(days=14)
                filtered_df = df[df['date'].dt.date >= start_date]
                if filtered_df.empty:
                    # Fallback: get last 10 trading days
                    filtered_df = df.tail(10)
            elif period == 'month':
                # Get last 2 months of historical data, or last 30 trading days if no recent data
                start_date = today - timedelta(days=60)
                filtered_df = df[df['date'].dt.date >= start_date]
                if filtered_df.empty:
                    # Fallback: get last 30 trading days
                    filtered_df = df.tail(30)
            elif period == 'year':
                # Get the most recent 1 year of historical data (last 250 trading days)
                print("Year filter: getting last 1 year of historical data")
                filtered_df = df.tail(250)  # Last 250 trading days = ~1 year
            else:  # 5year
                # Get all historical data
                filtered_df = df
            
            if filtered_df.empty:
                print(f"No fallback data found for {symbol} {period}")
                return []
            
            # Convert to our format
            fallback_points = []
            for _, row in filtered_df.iterrows():
                fallback_points.append({
                    'date': row['date'].strftime('%Y-%m-%d'),
                    'open': float(row['open']) if pd.notna(row['open']) else None,
                    'high': float(row['high']) if pd.notna(row['high']) else None,
                    'low': float(row['low']) if pd.notna(row['low']) else None,
                    'close': float(row['close']) if pd.notna(row['close']) else None,
                    'volume': int(row['volume']) if pd.notna(row['volume']) else 0,
                    'currency': 'INR'
                })
            
            print(f"Fallback: Found {len(fallback_points)} data points for {symbol} {period}")
            return fallback_points
            
        except Exception as e:
            print(f"Error in fallback data for {symbol}: {e}")
            return []

def main():
    """Main function for command line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Download Indian stocks latest data")
    parser.add_argument("--force", action="store_true", help="Force re-download of existing files")
    parser.add_argument("--symbols", nargs="+", help="Specific symbols to download")
    
    args = parser.parse_args()
    
    fetcher = IndianLatestFetcher()
    stats = fetcher.fetch_latest_data(
        force_redownload=args.force,
        symbols_to_download=args.symbols
    )
    
    # Print summary
    print("\n" + "=" * 50)
    print("DOWNLOAD SUMMARY")
    print("=" * 50)
    print(f"Total symbols: {stats['total_symbols']}")
    print(f"Skipped (recent): {stats['skipped_recent']}")
    print(f"Downloaded: {stats['downloaded']}")
    print(f"Failed: {stats['failed']}")
    
    if stats['downloaded'] + stats['skipped_recent'] > 0:
        success_rate = ((stats['downloaded'] + stats['skipped_recent']) / stats['total_symbols'] * 100)
        print(f"Success rate: {success_rate:.1f}%")
    
    if stats['errors']:
        print(f"\nErrors ({len(stats['errors'])}):")
        for error in stats['errors'][:10]:  # Show first 10
            print(f"  ❌ {error}")
        if len(stats['errors']) > 10:
            print(f"  ... and {len(stats['errors']) - 10} more")

if __name__ == "__main__":
    main()
