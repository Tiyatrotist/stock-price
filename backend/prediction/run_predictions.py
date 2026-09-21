#!/usr/bin/env python3
"""
Stock Prediction Runner

Standalone script to run stock predictions for all stocks or specific categories.
This script can be executed directly to generate predictions.

Usage:
    python backend/prediction/run_predictions.py
    python backend/prediction/run_predictions.py --category us_stocks
    python backend/prediction/run_predictions.py --symbol AAPL --category us_stocks
    python backend/prediction/run_predictions.py --max-stocks 10 --test
"""

import os
import sys
import argparse
import logging
from datetime import datetime
import json

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from prediction.predictor import StockPredictor
from prediction.config import config
from shared.utilities import categorize_stock

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('prediction.log')
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main function to run stock predictions."""
    parser = argparse.ArgumentParser(description='Run stock price predictions')
    
    parser.add_argument('--category', 
                       choices=['us_stocks', 'ind_stocks'], 
                       help='Stock category to process')
    
    parser.add_argument('--symbol', 
                       help='Specific stock symbol to predict')
    
    parser.add_argument('--max-stocks', 
                       type=int, 
                       help='Maximum number of stocks to process (for testing)')
    
    parser.add_argument('--test', 
                       action='store_true', 
                       help='Run in test mode (limited stocks)')
    
    parser.add_argument('--summary', 
                       action='store_true', 
                       help='Show prediction summary only')
    
    parser.add_argument('--config-check', 
                       action='store_true', 
                       help='Check configuration and exit')
    
    args = parser.parse_args()
    
    try:
        # Check configuration
        if args.config_check:
            check_configuration()
            return
        
        # Show summary only
        if args.summary:
            show_prediction_summary()
            return
        
        # Initialize predictor
        logger.info("Initializing Stock Predictor...")
        predictor = StockPredictor()
        
        # Set test mode defaults
        if args.test and not args.max_stocks:
            args.max_stocks = 5
        
        start_time = datetime.now()
        logger.info(f"Starting predictions at {start_time}")
        
        # Run predictions
        if args.symbol:
            category = args.category
            if not category:
                category = categorize_stock(args.symbol)
                logger.info(f"Auto-categorized {args.symbol} as {category}")
            
            # Single stock prediction
            logger.info(f"Predicting single stock: {args.symbol} ({category})")
            success = predictor.predict_stock(args.symbol, category)
            
            if success:
                logger.info(f"✅ Successfully predicted {args.symbol}")
            else:
                logger.error(f"❌ Failed to predict {args.symbol}")
                sys.exit(1)
                
        else:
            # Multiple stocks prediction
            logger.info("Starting predictions for multiple stocks...")
            results = predictor.predict_all_stocks(
                category=args.category,
                max_stocks=args.max_stocks
            )
            
            # Print results
            print_prediction_results(results)
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        logger.info(f"Predictions completed at {end_time}")
        logger.info(f"Total duration: {duration}")
        
    except KeyboardInterrupt:
        logger.info("Prediction interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error running predictions: {str(e)}")
        sys.exit(1)


def check_configuration():
    """Check configuration and display status."""
    logger.info("Checking configuration...")
    
    try:
        # Validate config
        config.validate_config()
        logger.info("✅ Configuration is valid")
        
        # Check directories
        directories = [
            config.DATA_DIR,
            config.PAST_DATA_DIR,
            config.LATEST_DATA_DIR,
            config.FUTURE_DATA_DIR
        ]
        
        for directory in directories:
            if os.path.exists(directory):
                logger.info(f"✅ Directory exists: {directory}")
            else:
                logger.warning(f"❌ Directory missing: {directory}")
        
        # Check index files
        index_files = [config.US_INDEX_FILE, config.IND_INDEX_FILE]
        for index_file in index_files:
            if os.path.exists(index_file):
                logger.info(f"✅ Index file exists: {index_file}")
            else:
                logger.warning(f"❌ Index file missing: {index_file}")
        
        # Display config summary
        config_dict = config.to_dict()
        logger.info("Configuration summary:")
        for key, value in config_dict.items():
            logger.info(f"  {key}: {value}")
        
    except Exception as e:
        logger.error(f"Configuration check failed: {str(e)}")
        sys.exit(1)


def show_prediction_summary():
    """Show summary of existing predictions."""
    logger.info("Loading prediction summary...")
    
    try:
        predictor = StockPredictor()
        summary = predictor.get_prediction_summary()
        
        print("\n" + "="*60)
        print("PREDICTION SUMMARY")
        print("="*60)
        
        if not summary:
            print("No prediction summaries found.")
            print("="*60 + "\n")
            return
            
        for category, data in summary.items():
            print(f"\n{category.upper()}:")
            if not isinstance(data, dict):
                print("  No data available.")
                continue
            total_stocks = data.get('total_stocks', 0)
            total_predictions = data.get('total_predictions', 0)
            latest_update = data.get('latest_update', 'N/A')
            horizons_available = data.get('horizons_available', []) or []
            horizons_str = ', '.join(horizons_available) if horizons_available else 'None'
            
            print(f"  Total stocks: {total_stocks}")
            print(f"  Total predictions: {total_predictions}")
            print(f"  Latest update: {latest_update}")
            print(f"  Horizons available: {horizons_str}")
        
        print("\n" + "="*60)
        
    except Exception as e:
        logger.error(f"Error loading summary: {str(e)}")
        sys.exit(1)


def print_prediction_results(results: dict):
    """Print prediction results in a formatted way."""
    print("\n" + "="*60)
    print("PREDICTION RESULTS")
    print("="*60)
    
    print(f"Total stocks processed: {results.get('total_stocks', 0)}")
    print(f"Successful predictions: {results.get('successful_predictions', 0)}")
    print(f"Failed predictions: {results.get('failed_predictions', 0)}")
    
    total_stocks = results.get('total_stocks', 0)
    successful_predictions = results.get('successful_predictions', 0)
    success_rate = (successful_predictions / total_stocks * 100) if total_stocks > 0 else 0
    print(f"Success rate: {success_rate:.1f}%")
    
    print(f"Start time: {results.get('start_time', 'N/A')}")
    print(f"End time: {results.get('end_time', 'N/A')}")
    
    failed_symbols = results.get('failed_symbols', [])
    if failed_symbols:
        print(f"\nFailed symbols ({len(failed_symbols)}):")
        for symbol in failed_symbols[:10]:  # Show first 10
            print(f"  - {symbol}")
        if len(failed_symbols) > 10:
            print(f"  ... and {len(failed_symbols) - 10} more")
    
    print("\n" + "="*60)
    
    # Save results to file
    results_dir = config.DATA_DIR if hasattr(config, 'DATA_DIR') and config.DATA_DIR else os.getcwd()
    os.makedirs(results_dir, exist_ok=True)
    results_file = os.path.join(results_dir, f"prediction_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    try:
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {results_file}")
    except Exception as e:
        logger.warning(f"Could not save results file: {str(e)}")


def run_quick_test():
    """Run a quick test with a few stocks."""
    logger.info("Running quick test...")
    
    try:
        predictor = StockPredictor()
        
        # Test with a few US stocks
        test_symbols = ['AAPL', 'MSFT', 'GOOGL']
        
        for symbol in test_symbols:
            logger.info(f"Testing {symbol}...")
            success = predictor.predict_stock(symbol, 'us_stocks')
            
            if success:
                logger.info(f"✅ {symbol} test passed")
            else:
                logger.warning(f"⚠️ {symbol} test failed")
        
        logger.info("Quick test completed")
        
    except Exception as e:
        logger.error(f"Quick test failed: {str(e)}")


if __name__ == "__main__":
    # If no arguments provided, show help
    if len(sys.argv) == 1:
        print("Stock Prediction System")
        print("=" * 50)
        print("Usage examples:")
        print("  python run_predictions.py --help")
        print("  python run_predictions.py --config-check")
        print("  python run_predictions.py --summary")
        print("  python run_predictions.py --test")
        print("  python run_predictions.py --category us_stocks --max-stocks 10")
        print("  python run_predictions.py --symbol AAPL --category us_stocks")
        print("")
        
        # Run quick test by default
        run_quick_test()
    else:
        main()
