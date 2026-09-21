"""
One-time cleanup script to remove stock CSV files not in dynamic index
Run once after implementing the new index system
"""

import os
import pandas as pd
from pathlib import Path

def load_symbols_from_index(data_dir: Path, category: str) -> set:
    """Load symbols from dynamic index file with fallback to standard index file."""
    dynamic_file = data_dir / f'index_{category}_stocks_dynamic.csv'
    standard_file = data_dir / f'index_{category}_stocks.csv'
    
    target_file = None
    if dynamic_file.exists():
        target_file = dynamic_file
    elif standard_file.exists():
        target_file = standard_file
    else:
        print(f"⚠️ Index file not found for {category} stocks (checked {dynamic_file.name} and {standard_file.name})")
        return set()
    
    try:
        df = pd.read_csv(target_file)
        if 'symbol' in df.columns:
            symbols = set(df['symbol'].dropna().str.upper())
            print(f"✓ Loaded {len(symbols)} symbols from {target_file.name}")
            return symbols
        else:
            print(f"⚠️ 'symbol' column missing in {target_file.name}")
            return set()
    except Exception as e:
        print(f"❌ Error reading {target_file.name}: {e}")
        return set()

def cleanup_orphaned_files():
    data_dir = Path(__file__).parent.parent.parent / 'data'
    
    # Load indexes with fallback
    us_symbols = load_symbols_from_index(data_dir, 'us')
    ind_symbols = load_symbols_from_index(data_dir, 'ind')
    
    # Check US stocks
    if us_symbols:
        us_dirs = [
            data_dir / 'latest' / 'us_stocks' / 'individual_files',
            data_dir / 'past' / 'us_stocks' / 'individual_files'
        ]
        for dir_path in us_dirs:
            if dir_path.exists():
                for file in dir_path.glob('*.csv'):
                    symbol = file.stem.upper()
                    if symbol not in us_symbols:
                        print(f"Removing orphaned US stock: {file}")
                        file.unlink()
    
    # Check Indian stocks
    if ind_symbols:
        ind_dirs = [
            data_dir / 'latest' / 'ind_stocks' / 'individual_files',
            data_dir / 'past' / 'ind_stocks' / 'individual_files'
        ]
        for dir_path in ind_dirs:
            if dir_path.exists():
                for file in dir_path.glob('*.csv'):
                    symbol = file.stem.upper()
                    if symbol not in ind_symbols:
                        print(f"Removing orphaned Indian stock: {file}")
                        file.unlink()

if __name__ == '__main__':
    cleanup_orphaned_files()
    print("Cleanup complete!")