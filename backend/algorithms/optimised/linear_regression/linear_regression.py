"""
Linear Regression for Stock Price Prediction

Optimized implementation using scikit-learn for stock price prediction
based on OHLCV data and technical indicators.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple
import sys
import os
import joblib
from sklearn.linear_model import LinearRegression, SGDRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler

# Add parent directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from ...model_interface import ModelInterface
from ...stock_indicators import StockIndicators


class LinearRegressionModel(ModelInterface):
    """
    Linear Regression model for stock price prediction.
    
    Uses technical indicators calculated from OHLC data to predict
    future stock prices. Volume is excluded from all calculations.
    """
    
    def __init__(self, use_sgd: bool = False, **kwargs):
        super().__init__('Linear Regression', **kwargs)
        self.model = None
        self.scaler = None
        self.feature_columns = None
        self.use_sgd = use_sgd  # Use SGD for efficient training on large datasets
        
    def _create_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators from OHLC data (no volume)."""
        return StockIndicators.calculate_all_indicators(df)
    
    def fit(self, X: np.ndarray, y: np.ndarray) -> 'ModelInterface':
        """
        Train the linear regression model on stock data.
        
        Args:
            X: Feature matrix (n_samples, n_features)
            y: Target vector (n_samples,) - stock prices (percentage change format)
            
        Returns:
            self: Returns self for method chaining
        """
        print(f"[DEBUG] LinearRegression.fit() called with X.shape={X.shape}, y.shape={y.shape}")
        print(f"[DEBUG] X min={X.min():.2f}, max={X.max():.2f}, mean={X.mean():.2f}")
        print(f"[DEBUG] y min={y.min():.2f}, max={y.max():.2f}, mean={y.mean():.2f}")
        
        self.validate_input(X, y)
        
        # Initialize model (SGD for incremental learning, LinearRegression for batch)
        if self.use_sgd:
            self.model = SGDRegressor(
                loss='squared_error',
                learning_rate='adaptive',
                eta0=0.01,
                max_iter=1000,
                random_state=42
            )
        else:
            self.model = LinearRegression()
        
        # Linear Regression NEEDS StandardScaler for numerical stability
        # Feature values range from -16000 to +16000 while target is -50 to +50
        # We save the scaler and use it during predictions
        self.scaler = StandardScaler()
        
        # Scale features for training
        X_scaled = self.scaler.fit_transform(X)
        
        # Log-transform target prices for linear growth
        y_log = np.log(y)
        
        # Train model on scaled features
        self.model.fit(X_scaled, y_log)
        
        # Calculate training metrics using inverse transformed predictions
        y_pred_log = self.model.predict(X_scaled)
        y_pred = np.exp(y_pred_log)
        mse = mean_squared_error(y, y_pred)
        rmse = np.sqrt(mse)
        r2 = r2_score(y, y_pred)
        
        self.set_training_metrics({
            'mse': mse,
            'rmse': rmse,
            'r2_score': r2
        })
        
        return self
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Make predictions on new stock data.
        
        Args:
            X: Features to predict on (n_samples, n_features)
            
        Returns:
            predictions: Predicted percentage changes (n_samples,)
        """
        if not self.is_trained:
            raise ValueError("Model not trained")
        
        self.validate_input(X)
        
        # Scale features using the SAME scaler from training
        X_scaled = self.scaler.transform(X)
        
        # Make predictions on scaled features
        predictions_log = self.model.predict(X_scaled)
        
        # Inverse log transform to get absolute prices
        return np.exp(predictions_log)
    
    def supports_incremental_learning(self) -> bool:
        """Check if model supports partial_fit."""
        return self.use_sgd and hasattr(self.model, 'partial_fit')
    
    def partial_fit(self, X: np.ndarray, y: np.ndarray) -> 'ModelInterface':
        """
        Incrementally train on a batch of data.
        
        Args:
            X: Feature matrix (n_samples, n_features)
            y: Target vector (n_samples,) - percentage changes
            
        Returns:
            self: Returns self for method chaining
        """
        if not self.supports_incremental_learning():
            raise ValueError("Model does not support incremental learning. Use SGDRegressor.")
        
        self.validate_input(X, y)
        
        # Scale features (fit scaler on first batch, transform on subsequent)
        if self.scaler is None or not hasattr(self.scaler, 'mean_'):
            self.scaler = StandardScaler()
            X_scaled = self.scaler.fit_transform(X)
        else:
            X_scaled = self.scaler.transform(X)
        
        # Log-transform target prices
        y_log = np.log(y)
        
        # Incrementally train model on scaled features
        self.model.partial_fit(X_scaled, y_log)
        
        # Update training status
        self.is_trained = True
        
        return self
    
    def save(self, path: str) -> None:
        """
        Save the trained model to disk.
        
        Args:
            path: File path to save the model
        """
        if not self.is_trained:
            raise ValueError("Model not trained")
        
        print(f"[DEBUG] LinearRegression.save() called with path={path}")
        print(f"[DEBUG] Training metrics: {self.training_metrics}")
        
        joblib.dump({
            'model': self.model,
            'scaler': self.scaler,
            'metrics': self.training_metrics,
            'params': self.model_params,
            'feature_columns': self.feature_columns
        }, path)
        
        print(f"[DEBUG] Model saved successfully")
    
    def load(self, path: str) -> 'ModelInterface':
        """
        Load a previously saved model from disk.
        
        Args:
            path: File path to load the model from
            
        Returns:
            self: Returns self for method chaining
        """
        data = joblib.load(path)
        self.model = data['model']
        self.scaler = data['scaler']
        self.training_metrics = data['metrics']
        self.model_params = data['params']
        self.feature_columns = data.get('feature_columns')
        self.is_trained = True
        return self
    
    def get_feature_importance(self) -> Dict[str, float]:
        """
        Get feature importance (coefficients) from the linear model.
        
        Returns:
            Dictionary of feature names and their coefficients
        """
        if not self.is_trained:
            raise ValueError("Model not trained")
        
        if self.feature_columns is None:
            return {}
        
        coefficients = self.model.coef_
        return dict(zip(self.feature_columns, coefficients))
    
    def predict_with_confidence(self, X: np.ndarray, confidence_level: float = 0.95) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Make predictions with confidence intervals.
        
        Args:
            X: Features to predict on
            confidence_level: Confidence level (0-1)
            
        Returns:
            Tuple of (predictions, lower_bounds, upper_bounds)
        """
        predictions = self.predict(X)
        
        # Simple confidence interval based on training RMSE
        rmse = self.training_metrics.get('rmse', 0)
        margin = rmse * 1.96  # Approximate 95% confidence
        
        lower_bounds = predictions - margin
        upper_bounds = predictions + margin
        
        return predictions, lower_bounds, upper_bounds


# Example usage and testing
if __name__ == "__main__":
    # Create sample stock data for testing
    np.random.seed(42)
    dates = pd.date_range('2020-01-01', periods=100, freq='D')
    
    # Generate synthetic OHLC data
    base_price = 100
    returns = np.random.normal(0, 0.02, 100)
    prices = [base_price]
    
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    df = pd.DataFrame({
        'date': dates,
        'open': prices,
        'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
        'close': prices
    })
    
    # Ensure high >= low and high >= close >= low
    df['high'] = np.maximum(df['high'], df['close'])
    df['low'] = np.minimum(df['low'], df['close'])
    
    # Create model
    model = LinearRegressionModel()
    
    # Add technical indicators
    df_with_features = model._create_technical_indicators(df)
    
    # Prepare training data
    X, y = StockIndicators.prepare_training_data(df_with_features)
    
    if len(X) > 0:
        # Train model
        model.fit(X, y)
        
        # Make predictions
        predictions = model.predict(X[-10:])  # Predict last 10 days
        
        print(f"Linear Regression Model Results:")
        print(f"Training R²: {model.training_metrics['r2_score']:.4f}")
        print(f"Training RMSE: {model.training_metrics['rmse']:.4f}")
        print(f"Sample predictions: {predictions[:5]}")
        
        # Test save/load
        model.save('test_linear_model.pkl')
        loaded_model = LinearRegressionModel().load('test_linear_model.pkl')
        print(f"Model loaded successfully: {loaded_model.is_trained}")
        
        # Clean up
        os.remove('test_linear_model.pkl')
    else:
        print("Insufficient data for training")
