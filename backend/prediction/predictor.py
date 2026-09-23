"""
Stock Predictor

Main prediction orchestrator that uses all algorithms from the optimised directory
to generate predictions for multiple time horizons.
"""

import os
import sys
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
import logging
from datetime import datetime
import warnings

# Add algorithms directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'algorithms'))

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

from .config import config
from .data_loader import DataLoader
from .prediction_saver import PredictionSaver
from .confidence_calculator import confidence_calculator

# LAZY MODEL LOADING: Models are imported only when _load_model_class() is called
# This prevents loading TensorFlow and other heavy dependencies at module import time


class StockPredictor:
    """
    Main stock prediction orchestrator.
    
    Uses all available algorithms to generate ensemble predictions
    for multiple time horizons.
    """
    
    def __init__(self):
        self.config = config
        self.data_loader = DataLoader()
        self.prediction_saver = PredictionSaver()
        
        # Initialize all models
        self.models = self._initialize_models()
        
        # Track model performance
        self.model_performance = {}
        
    def _load_model_class(self, model_name: str):
        """Lazy load model class only when needed."""
        try:
            if model_name == 'linear_regression':
                from algorithms.optimised.linear_regression.linear_regression import LinearRegressionModel
                return LinearRegressionModel
            elif model_name == 'random_forest':
                from algorithms.optimised.random_forest.random_forest import RandomForestModel
                return RandomForestModel
            elif model_name == 'decision_tree':
                from algorithms.optimised.decision_tree.decision_tree import DecisionTreeModel
                return DecisionTreeModel
            elif model_name == 'svm':
                from algorithms.optimised.svm.svm import SVMModel
                return SVMModel
            elif model_name == 'knn':
                from algorithms.optimised.knn.knn import KNNModel
                return KNNModel
            elif model_name == 'arima':
                from algorithms.optimised.arima.arima import ARIMAModel
                return ARIMAModel
            elif model_name == 'autoencoder':
                from algorithms.optimised.autoencoders.autoencoder import AutoencoderModel
                return AutoencoderModel
            else:
                logger.warning(f"Unknown model: {model_name}")
                return None
        except ImportError as e:
            logger.warning(f"Could not import {model_name}: {e}")
            return None
    
    def _initialize_models(self) -> Dict[str, Any]:
        """Load pre-trained models from disk."""
        models = {}
        models_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
        
        # Model list (classes loaded lazily)
        model_names = [
            'linear_regression',
            'random_forest',
            'svm',
            'knn',
            'decision_tree',
            'arima',
            'autoencoder'
        ]
        
        for model_name in model_names:
            # Lazy load model class
            model_class = self._load_model_class(model_name)
            if model_class is None:
                logger.warning(f"Model class not available: {model_name}")
                continue
            
            # Special handling for ARIMA (per-stock specialist models)
            if model_name == 'arima':
                model_subdir = os.path.join(models_dir, model_name)
                if os.path.isdir(model_subdir):
                    models[model_name] = model_class  # Register class, not instance
                    logger.info(f"Registered {model_name} (per-stock specialist model)")
                else:
                    logger.warning(f"ARIMA model directory not found: {model_subdir}")
                continue  # Skip normal loading for ARIMA
            
            # Load from model-specific subdirectory
            model_subdir = os.path.join(models_dir, model_name)
            model_path = os.path.join(model_subdir, f"{model_name}_model.pkl")
            
            # Special handling for autoencoder (3-file structure)
            if model_name == 'autoencoder':
                # Check for metadata file instead of base .pkl file
                check_path = f"{model_path}_metadata.pkl"
            else:
                check_path = model_path
            
            if os.path.exists(check_path):
                try:
                    # Load pre-trained model
                    model = model_class().load(model_path)
                    models[model_name] = model
                    logger.info(f"Loaded pre-trained {model_name}")
                except Exception as e:
                    logger.error(f"Error loading {model_name}: {e}")
            else:
                logger.warning(f"Pre-trained model not found: {check_path}")
        
        logger.info(f"Loaded {len(models)} pre-trained models: {list(models.keys())}")
        return models
    
    
    def predict_single_stock_with_models(
        self, 
        symbol: str, 
        category: str,
        horizon: str,
        current_price: float,
        model_filter: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Generate prediction for a single stock using specific models.
        
        Args:
            symbol: Stock symbol
            category: Stock category ('us_stocks' or 'ind_stocks')
            horizon: Time horizon ('1d', '1w', '1m', '1y', '5y')
            current_price: Current stock price
            model_filter: List of model names to use (None = use all available)
            
        Returns:
            Dictionary with prediction results or None if failed
        """
        try:
            logger.info(f"Generating prediction for {symbol} ({category}) - horizon: {horizon}")
            
            # Load and prepare data
            logger.info(f"[PREDICT] Step 1: Loading stock data for {symbol}...")
            df = self.data_loader.load_stock_data(symbol, category)
            if df is None:
                logger.error(f"[PREDICT] FAILED at Step 1: No data available for {symbol}")
                return None
            logger.info(f"[PREDICT] Step 1 SUCCESS: Loaded {len(df)} rows for {symbol}")
            
            # Validate data quality
            logger.info(f"[PREDICT] Step 2: Validating data quality for {symbol}...")
            if not self.data_loader.validate_data_quality(df, symbol):
                logger.error(f"[PREDICT] FAILED at Step 2: Data quality issues for {symbol}")
                return None
            logger.info(f"[PREDICT] Step 2 SUCCESS: Data quality validated")
            
            # Create features
            logger.info(f"[PREDICT] Step 3: Creating features for {symbol}...")
            df_with_features = self.data_loader.create_features(df)
            if df_with_features is None or len(df_with_features) == 0:
                logger.error(f"[PREDICT] FAILED at Step 3: Could not create features for {symbol}")
                return None
            logger.info(f"[PREDICT] Step 3 SUCCESS: Created features, {len(df_with_features)} rows")
            
            # Prepare training data (for prediction with pre-trained models, we need less data)
            logger.info(f"[PREDICT] Step 4: Preparing training data for {symbol}...")
            X, y = self.data_loader.prepare_training_data(df_with_features, for_prediction=True)
            if len(X) == 0 or len(y) == 0:
                logger.error(f"[PREDICT] FAILED at Step 4: Insufficient training data for {symbol}")
                return None
            logger.info(f"[PREDICT] Step 4 SUCCESS: Prepared {len(X)} training samples")
            
            # Filter models if specified
            models_to_use = self.models
            if model_filter:
                models_to_use = {k: v for k, v in self.models.items() if k in model_filter}
                if not models_to_use:
                    logger.error(f"None of the requested models are available: {model_filter}")
                    return None
            
            # Generate prediction for the horizon
            horizon_days = self.config.TIME_HORIZONS.get(horizon, 1)
            
            # Collect predictions from each model
            model_predictions = []
            for model_name, model_or_class in models_to_use.items():
                try:
                    # Get model weight
                    weight = self.config.MODEL_WEIGHTS.get(model_name, 0.0)
                    
                    # Skip models with weight 0 ONLY in ensemble mode (no filter specified)
                    if weight == 0 and model_filter is None:
                        continue
                    
                    # For explicitly requested models with weight 0, use weight 1.0
                    if model_filter and weight == 0:
                        weight = 1.0
                    
                    # Special handling for ARIMA (per-stock specialist models)
                    if model_name == 'arima':
                        logger.info(f"--- Processing ARIMA specialist model for {symbol} ---")
                        models_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
                        model_path = os.path.join(models_dir, 'arima', f"{symbol}_model.pkl")
                        
                        if not os.path.exists(model_path):
                            logger.warning(f"ARIMA model for {symbol} not found at {model_path}. Skipping.")
                            continue
                        
                        # Load the specialist model for this stock
                        model = model_or_class().load(model_path)
                        logger.info(f"Loaded ARIMA specialist model for {symbol}")
                        
                        # Update models_to_use so confidence calculation can access training_metrics
                        models_to_use[model_name] = model
                        
                        # ARIMA predict_with_confidence() returns (predictions, lower_bounds, upper_bounds)
                        # Each is an array of forecasts for 'steps' days ahead
                        forecast_result = model.predict_with_confidence(X, steps=horizon_days)
                        
                        # Get the final prediction for the requested horizon (last day in forecast)
                        predicted_price = forecast_result[0][-1]
                        prediction_pct = (predicted_price - current_price) / current_price * 100
                        
                        logger.info(f"ARIMA prediction for {symbol}: ${predicted_price:.2f} ({prediction_pct:+.2f}%)")
                    
                    else:
                        # Original logic for all other models (they're already loaded instances)
                        model = model_or_class  # Use the pre-loaded model instance
                        
                        # Make prediction (returns percentage change)
                        if horizon_days == 1:
                            # Direct next-day prediction
                            prediction_pct = model.predict(X[-1:].reshape(1, -1))[0]
                        else:
                            # Extrapolate for longer horizons
                            prediction_pct = self._extrapolate_prediction(
                                model, X, y, horizon_days, current_price
                            )
                        
                        # Convert percentage to price
                        predicted_price = current_price * (1 + prediction_pct / 100)
                    
                    model_predictions.append({
                        'model': model_name,
                        'prediction': predicted_price,
                        'weight': weight,
                        'percentage_change': prediction_pct
                    })
                    
                    logger.info(f"  {model_name}: {predicted_price:.2f} ({prediction_pct:+.2f}%)")
                    
                except Exception as e:
                    logger.error(f"  {model_name} prediction failed: {e}", exc_info=True)
                    continue
            
            if not model_predictions:
                logger.warning(f"No models produced valid predictions for {symbol}")
                return None
            
            # Calculate weighted ensemble prediction
            total_weight = sum(p['weight'] for p in model_predictions)
            if total_weight == 0:
                # Equal weights
                total_weight = len(model_predictions)
                for p in model_predictions:
                    p['weight'] = 1.0
            
            ensemble_prediction = sum(
                p['prediction'] * (p['weight'] / total_weight)
                for p in model_predictions
            )
            
            # Calculate confidence
            if len(model_predictions) == 1:
                # Single model confidence
                model_pred = model_predictions[0]
                # Use the actual R² score from training metrics
                model_r2 = (getattr(models_to_use[model_pred['model']], 'training_metrics', {}) or {}).get('r2_score', 0.5)
                confidence = confidence_calculator.calculate_single_model_confidence(
                    model_accuracy=model_r2,
                    historical_prices=df['close'].values if 'close' in df.columns else np.array([current_price]),
                    time_horizon_days=horizon_days,
                    model_name=model_pred['model']
                )
            else:
                # Ensemble confidence
                # Use actual R² scores from each model's training metrics
                model_accuracies = {
                    p['model']: (getattr(models_to_use[p['model']], 'training_metrics', {}) or {}).get('r2_score', 0.5)
                    for p in model_predictions
                }
                model_price_predictions = {p['model']: p['prediction'] for p in model_predictions}
                confidence = confidence_calculator.calculate_ensemble_confidence(
                    model_accuracies=model_accuracies,
                    model_predictions=model_price_predictions,
                    historical_prices=df['close'].values if 'close' in df.columns else np.array([current_price]),
                    time_horizon_days=horizon_days
                )
            
            # Build result
            result = {
                'symbol': symbol,
                'predicted_price': ensemble_prediction,
                'current_price': current_price,
                'confidence': confidence,
                'time_frame_days': horizon_days,
                'model_info': {
                    'model': 'Ensemble' if len(model_predictions) > 1 else model_predictions[0]['model'],
                    'members': [p['model'] for p in model_predictions],
                    'weights': {p['model']: p['weight'] / total_weight for p in model_predictions}
                },
                'data_points_used': len(X),
                'last_updated': datetime.utcnow().isoformat() + 'Z'
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Prediction failed for {symbol}: {e}", exc_info=True)
            return None
    
    
    def predict_stock(self, symbol: str, category: str) -> bool:
        """
        Generate predictions for a single stock.
        
        Args:
            symbol: Stock symbol
            category: Stock category ('us_stocks' or 'ind_stocks')
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Starting prediction for {symbol} ({category})")
            
            # Load and prepare data (historical only)
            # TODO: For live predictions, use load_stock_data_with_current_price() 
            # and pass current_price parameter fetched from API
            df = self.data_loader.load_stock_data(symbol, category)
            if df is None:
                logger.warning(f"No data available for {symbol}")
                return False
            
            # Validate data quality
            if not self.data_loader.validate_data_quality(df, symbol):
                logger.warning(f"Data quality issues for {symbol}")
                return False
            
            # Create features
            df_with_features = self.data_loader.create_features(df)
            if df_with_features is None or len(df_with_features) == 0:
                logger.warning(f"Could not create features for {symbol}")
                return False
            
            # Prepare training data
            X, y = self.data_loader.prepare_training_data(df_with_features)
            if len(X) == 0 or len(y) == 0:
                logger.warning(f"Insufficient training data for {symbol}")
                return False
            
            # Generate predictions for all time horizons
            all_predictions = []
            
            for horizon in self.config.TIME_HORIZONS.keys():
                logger.debug(f"Generating {horizon} prediction for {symbol}")
                
                horizon_predictions = self._predict_horizon(
                    symbol, category, X, y, horizon, df_with_features
                )
                
                if horizon_predictions:
                    all_predictions.extend(horizon_predictions)
            
            # Save predictions
            if all_predictions:
                success = self.prediction_saver.save_predictions(
                    symbol, category, all_predictions
                )
                
                if success:
                    logger.info(f"Successfully generated {len(all_predictions)} predictions for {symbol}")
                    return True
                else:
                    logger.error(f"Failed to save predictions for {symbol}")
                    return False
            else:
                logger.warning(f"No predictions generated for {symbol}")
                return False
                
        except Exception as e:
            logger.error(f"Error predicting {symbol}: {str(e)}")
            return False
    
    def _predict_horizon(self, symbol: str, category: str, X: np.ndarray, y: np.ndarray, 
                        horizon: str, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Generate predictions for a specific time horizon.
        
        Args:
            symbol: Stock symbol
            category: Stock category
            X: Feature matrix
            y: Target vector
            horizon: Time horizon (1D, 1W, 1M, 1Y, 5Y)
            
        Returns:
            List of prediction dictionaries
        """
        predictions = []
        
        try:
            # Get number of days for this horizon
            horizon_days = self.config.get_time_horizon_days(horizon)
            
            # Get current price for reference
            current_price = df['close'].iloc[-1]
            
            # Get historical prices for confidence calculation
            historical_prices = df['close'].values
            
            # Get currency
            currency = 'USD' if category == 'us_stocks' else 'INR'
            
            # Train models and get predictions
            model_predictions = {}
            model_accuracies = {}
            
            for model_name, model in self.models.items():
                try:
                    logger.debug(f"Using pre-trained {model_name} for {symbol} {horizon}")
                    
                    if model_name == 'arima':
                        # Special handling for ARIMA (per-stock specialist models)
                        models_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
                        model_path = os.path.join(models_dir, 'arima', f"{symbol}_model.pkl")
                        if not os.path.exists(model_path):
                            logger.warning(f"ARIMA model for {symbol} not found at {model_path}. Skipping.")
                            continue
                        arima_instance = model().load(model_path)
                        forecast_result = arima_instance.predict_with_confidence(X, steps=horizon_days)
                        predicted_price = forecast_result[0][-1]
                        prediction_pct = (predicted_price - current_price) / current_price * 100
                        accuracy = (getattr(arima_instance, 'training_metrics', {}) or {}).get('r2_score', 0.5)
                    else:
                        # Get prediction (model predicts PERCENTAGE CHANGE, not raw price)
                        if horizon == '1D':
                            # Direct prediction for next day (percentage change)
                            prediction_pct = model.predict(X[-1:].reshape(1, -1))[0]
                        else:
                            # For longer horizons, use iterative prediction or trend extrapolation
                            prediction_pct = self._extrapolate_prediction(
                                model, X, y, horizon_days, current_price
                            )
                        
                        # Convert percentage change to actual price
                        # Formula: predicted_price = current_price * (1 + prediction_percentage/100)
                        predicted_price = current_price * (1 + prediction_pct / 100)
                        
                        # Debug logging
                        logger.info(f"[DEBUG] {model_name} for {symbol} {horizon}: current_price={current_price:.2f}, prediction_pct={prediction_pct:.4f}%, predicted_price={predicted_price:.2f}")
                        
                        # Use the R² score from training (already calculated and stored during model training)
                        # This is more efficient and accurate than recalculating on the fly
                        accuracy = (getattr(model, 'training_metrics', {}) or {}).get('r2_score', 0.5)
                    
                    model_predictions[model_name] = predicted_price
                    model_accuracies[model_name] = accuracy
                    
                    logger.debug(f"{model_name} prediction for {symbol} {horizon}: ${predicted_price:.2f} ({prediction_pct:+.2f}%, accuracy: {accuracy:.4f})")
                    
                except Exception as e:
                    logger.warning(f"Error with {model_name} for {symbol} {horizon}: {str(e)}")
                    continue
            
            if not model_predictions:
                logger.warning(f"No model predictions for {symbol} {horizon}")
                return []
            
            # Create ensemble prediction
            ensemble_prediction = self._create_ensemble_prediction(
                model_predictions, model_accuracies
            )
            
            # Calculate confidence interval
            confidence_low, confidence_high = self._calculate_confidence_interval(
                model_predictions, ensemble_prediction
            )
            
            # Calculate confidence score (0-100)
            ensemble_confidence = confidence_calculator.calculate_ensemble_confidence(
                model_accuracies=model_accuracies,
                model_predictions=model_predictions,
                historical_prices=historical_prices,
                time_horizon_days=horizon_days
            )
            
            # Create prediction dictionary
            prediction_dict = self.prediction_saver.create_prediction_dict(
                horizon=horizon,
                predicted_price=ensemble_prediction,
                current_price=current_price,
                confidence=ensemble_confidence,
                confidence_low=confidence_low,
                confidence_high=confidence_high,
                algorithm_used='|'.join(model_predictions.keys()),
                currency=currency,
                model_accuracy=np.mean(list(model_accuracies.values())),
                data_points_used=len(X)
            )
            
            predictions.append(prediction_dict)
            
            # Store individual model predictions for analysis
            for model_name, pred in model_predictions.items():
                # Calculate confidence for single model
                single_model_confidence = confidence_calculator.calculate_single_model_confidence(
                    model_accuracy=model_accuracies[model_name],
                    historical_prices=historical_prices,
                    time_horizon_days=horizon_days,
                    model_name=model_name
                )
                
                individual_pred = self.prediction_saver.create_prediction_dict(
                    horizon=horizon,
                    predicted_price=pred,
                    current_price=current_price,
                    confidence=single_model_confidence,
                    confidence_low=pred * 0.95,  # 5% range
                    confidence_high=pred * 1.05,
                    algorithm_used=model_name,
                    currency=currency,
                    model_accuracy=model_accuracies[model_name],
                    data_points_used=len(X)
                )
                predictions.append(individual_pred)
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error predicting {horizon} for {symbol}: {str(e)}")
            return []
    
    def _extrapolate_prediction(self, model: Any, X: np.ndarray, y: np.ndarray, 
                               horizon_days: int, current_price: float) -> float:
        """
        Extrapolate prediction for longer time horizons.
        
        NOTE: y contains PERCENTAGE CHANGES (not prices)
        
        Args:
            model: Trained model
            X: Feature matrix
            y: Target vector (PERCENTAGE CHANGES)
            horizon_days: Number of days to predict ahead
            current_price: Current stock price (not used - we return percentage)
            
        Returns:
            Extrapolated prediction as PERCENTAGE CHANGE
        """
        try:
            # y contains percentage changes, not prices
            recent_pct_changes = y[-30:]  # Last 30 days of percentage changes
            if len(recent_pct_changes) < 2:
                return 0.0  # Return 0% change
            
            # Calculate average daily percentage change
            avg_daily_pct_change = np.mean(recent_pct_changes)
            
            # Extrapolate: compound the average daily change over the horizon
            # For simplicity, we'll multiply by horizon_days (linear approximation)
            # This gives us the total expected percentage change
            trend_pct = avg_daily_pct_change * min(horizon_days, 30)  # Cap at 30 days for stability
            
            # Also get model's next-day prediction (percentage change)
            next_day_pct_pred = model.predict(X[-1:].reshape(1, -1))[0]
            
            # Combine trend and model prediction
            # For longer horizons, trust the trend more; for shorter, trust the model more
            trend_weight = min(0.7, horizon_days / 365)  # More weight to trend for longer horizons
            model_weight = 1 - trend_weight
            
            # Both are percentage changes, so we can combine them
            final_pct_prediction = (trend_weight * trend_pct + 
                                   model_weight * next_day_pct_pred)
            
            # Return percentage change (NOT price)
            return final_pct_prediction
            
        except Exception as e:
            logger.warning(f"Error in extrapolation: {str(e)}")
            # Fallback to 0% change
            return 0.0
    
    def _create_ensemble_prediction(self, model_predictions: Dict[str, float], 
                                   model_accuracies: Dict[str, float]) -> float:
        """
        Create ensemble prediction using weighted average.
        
        Args:
            model_predictions: Dictionary of model predictions
            model_accuracies: Dictionary of model accuracies
            
        Returns:
            Ensemble prediction
        """
        try:
            # Use model weights from config, adjusted by accuracy
            total_weight = 0
            weighted_sum = 0
            
            for model_name, prediction in model_predictions.items():
                base_weight = self.config.get_model_weight(model_name)
                accuracy = model_accuracies.get(model_name, 0.5)
                
                # Adjust weight by accuracy
                adjusted_weight = base_weight * (0.5 + accuracy)  # Boost by accuracy
                weighted_sum += prediction * adjusted_weight
                total_weight += adjusted_weight
            
            if total_weight > 0:
                return weighted_sum / total_weight
            else:
                # Fallback to simple average
                return np.mean(list(model_predictions.values()))
                
        except Exception as e:
            logger.warning(f"Error creating ensemble prediction: {str(e)}")
            return np.mean(list(model_predictions.values()))
    
    def _calculate_confidence_interval(self, model_predictions: Dict[str, float], 
                                     ensemble_prediction: float) -> Tuple[float, float]:
        """
        Calculate confidence interval for predictions.
        
        Args:
            model_predictions: Dictionary of model predictions
            ensemble_prediction: Ensemble prediction
            
        Returns:
            Tuple of (confidence_low, confidence_high)
        """
        try:
            predictions = list(model_predictions.values())
            
            if len(predictions) < 2:
                # Single prediction - use 10% range
                range_pct = 0.1
                return (ensemble_prediction * (1 - range_pct), 
                       ensemble_prediction * (1 + range_pct))
            
            # Calculate standard deviation
            std_dev = np.std(predictions)
            
            # Use multiplier from config
            multiplier = self.config.CONFIDENCE_MULTIPLIER
            
            confidence_low = ensemble_prediction - (multiplier * std_dev)
            confidence_high = ensemble_prediction + (multiplier * std_dev)
            
            # Ensure positive values
            confidence_low = max(confidence_low, ensemble_prediction * 0.5)
            confidence_high = max(confidence_high, ensemble_prediction * 1.5)
            
            return confidence_low, confidence_high
            
        except Exception as e:
            logger.warning(f"Error calculating confidence interval: {str(e)}")
            # Fallback to 20% range
            range_pct = 0.2
            return (ensemble_prediction * (1 - range_pct), 
                   ensemble_prediction * (1 + range_pct))
    
    def _calculate_accuracy(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """
        Calculate model accuracy (R² score).
        
        Args:
            y_true: True values
            y_pred: Predicted values
            
        Returns:
            Accuracy score (0-1)
        """
        try:
            from sklearn.metrics import r2_score
            return max(0, r2_score(y_true, y_pred))
        except:
            # Fallback to simple correlation
            try:
                correlation = np.corrcoef(y_true, y_pred)[0, 1]
                return max(0, correlation ** 2)
            except:
                return 0.5  # Default accuracy
    
    def predict_all_stocks(self, category: str = None, max_stocks: int = None) -> Dict[str, Any]:
        """
        Generate predictions for all stocks in a category.
        
        Args:
            category: Stock category ('us_stocks', 'ind_stocks', or None for both)
            max_stocks: Maximum number of stocks to process (for testing)
            
        Returns:
            Dictionary with prediction results summary
        """
        results = {
            'total_stocks': 0,
            'successful_predictions': 0,
            'failed_predictions': 0,
            'failed_symbols': [],
            'start_time': datetime.now().isoformat(),
            'end_time': None
        }
        
        try:
            categories = [category] if category else ['us_stocks', 'ind_stocks']
            
            for cat in categories:
                logger.info(f"Starting predictions for {cat}")
                
                # Get stock symbols
                symbols = self.data_loader.get_stock_symbols(cat)
                
                if max_stocks:
                    symbols = symbols[:max_stocks]
                    logger.info(f"Processing first {max_stocks} stocks for testing")
                
                results['total_stocks'] += len(symbols)
                
                # Process each stock
                for i, symbol in enumerate(symbols, 1):
                    logger.info(f"Processing {symbol} ({i}/{len(symbols)}) in {cat}")
                    
                    try:
                        success = self.predict_stock(symbol, cat)
                        
                        if success:
                            results['successful_predictions'] += 1
                        else:
                            results['failed_predictions'] += 1
                            results['failed_symbols'].append(f"{symbol} ({cat})")
                            
                    except Exception as e:
                        logger.error(f"Error processing {symbol}: {str(e)}")
                        results['failed_predictions'] += 1
                        results['failed_symbols'].append(f"{symbol} ({cat})")
            
            results['end_time'] = datetime.now().isoformat()
            
            logger.info(f"Prediction summary: {results['successful_predictions']}/{results['total_stocks']} successful")
            
            if results['failed_symbols']:
                logger.warning(f"Failed symbols: {results['failed_symbols']}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in predict_all_stocks: {str(e)}")
            results['end_time'] = datetime.now().isoformat()
            return results
    
    def get_prediction_summary(self) -> Dict[str, Any]:
        """Get summary of all predictions."""
        summary = {}
        
        for category in ['us_stocks', 'ind_stocks']:
            summary[category] = self.prediction_saver.get_prediction_summary(category)
        
        return summary
