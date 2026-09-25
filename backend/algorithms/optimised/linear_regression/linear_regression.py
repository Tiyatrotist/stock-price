"""
Linear Regression for Stock Price Prediction

Optimized implementation using scikit-learn for stock price prediction
based on OHLCV data and technical indicators.

Supports regularized variants (Ridge, Lasso, ElasticNet) to prevent
overfitting on noisy financial data, and SGD for incremental learning.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple
import sys
import os
import joblib
from sklearn.linear_model import LinearRegression, SGDRegressor, Ridge, Lasso, ElasticNet
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
import logging

logger = logging.getLogger(__name__)

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
    
    def __init__(self, use_sgd: bool = False, model_type: str = 'linear',
                 alpha: float = 1.0, **kwargs):
        """
        Initialize Linear Regression model.

        Args:
            use_sgd: If True, use SGDRegressor for incremental learning.
                     The `model_type` parameter controls the penalty when
                     use_sgd is True ('l1', 'l2', 'elasticnet', or None).
            model_type: Type of regression model for batch training.
                        Options: 'linear', 'ridge', 'lasso', 'elasticnet'.
                        For SGD mode, this maps to the corresponding penalty.
            alpha: Regularization strength. Higher values = stronger
                   regularization. Ignored when model_type='linear'.
        """
        super().__init__('Linear Regression', **kwargs)
        self.model = None
        self.scaler = None
        self.feature_columns = None
        self.use_sgd = use_sgd  # Use SGD for efficient training on large datasets
        self.model_type = model_type.lower()
        self.alpha = alpha
        self.use_log_transform = True  # Will be set to False if y contains non-positive values
        
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
        logger.info(f"LinearRegression.fit() called with X.shape={X.shape}, y.shape={y.shape}")
        logger.debug(f"X min={X.min():.2f}, max={X.max():.2f}, mean={X.mean():.2f}")
        logger.debug(f"y min={y.min():.2f}, max={y.max():.2f}, mean={y.mean():.2f}")
        
        self.validate_input(X, y)
        
        # Initialize model based on configuration
        self.model = self._create_model()
        
        # Linear Regression NEEDS StandardScaler for numerical stability
        # Feature values range from -16000 to +16000 while target is -50 to +50
        # We save the scaler and use it during predictions
        self.scaler = StandardScaler()
        
        # Scale features for training
        X_scaled = self.scaler.fit_transform(X)
        
        # Safe target transformation: only apply log if all values are positive
        y_train = self._safe_transform_target(y)
        
        # Train model on scaled features
        self.model.fit(X_scaled, y_train)
        
        # Calculate training metrics using inverse transformed predictions
        y_pred_raw = self.model.predict(X_scaled)
        y_pred = self._inverse_transform_target(y_pred_raw)
        mse = mean_squared_error(y, y_pred)
        rmse = np.sqrt(mse)
        r2 = r2_score(y, y_pred)
        
        self.set_training_metrics({
            'mse': mse,
            'rmse': rmse,
            'r2_score': r2,
            'model_type': self.model_type,
            'alpha': self.alpha if self.model_type != 'linear' else None,
            'log_transformed': self.use_log_transform
        })
        
        logger.info(
            f"Training completed. R²={r2:.4f}, RMSE={rmse:.4f}, "
            f"model_type={self.model_type}, log_transform={self.use_log_transform}"
        )
        
        return self
    
    def _create_model(self):
        """
        Create the appropriate regression model based on configuration.

        For SGD mode, maps model_type to the corresponding penalty parameter.
        For batch mode, instantiates the appropriate sklearn estimator.

        Returns:
            Configured sklearn regression estimator
        """
        if self.use_sgd:
            # Map model_type to SGD penalty parameter
            penalty_map = {
                'linear': None,
                'ridge': 'l2',
                'lasso': 'l1',
                'elasticnet': 'elasticnet'
            }
            penalty = penalty_map.get(self.model_type, None)
            return SGDRegressor(
                loss='squared_error',
                penalty=penalty,
                alpha=self.alpha if penalty else 0.0001,
                learning_rate='adaptive',
                eta0=0.01,
                max_iter=1000,
                random_state=42
            )
        else:
            if self.model_type == 'ridge':
                return Ridge(alpha=self.alpha)
            elif self.model_type == 'lasso':
                return Lasso(alpha=self.alpha)
            elif self.model_type == 'elasticnet':
                return ElasticNet(alpha=self.alpha)
            else:
                return LinearRegression()
    
    def _safe_transform_target(self, y: np.ndarray) -> np.ndarray:
        """
        Safely transform the target variable.

        Applies log transform only when all target values are strictly positive
        (i.e., absolute prices). If y contains zero or negative values (e.g.,
        percentage returns), the log transform is skipped to prevent crashes.

        Args:
            y: Target array

        Returns:
            Transformed target array
        """
        if np.any(y <= 0):
            logger.warning(
                "Target variable contains zero or negative values. "
                "Skipping log transform (y likely represents percentage returns)."
            )
            self.use_log_transform = False
            return y
        
        self.use_log_transform = True
        return np.log(y)
    
    def _inverse_transform_target(self, y_pred: np.ndarray) -> np.ndarray:
        """
        Inverse transform predictions back to the original target scale.

        Args:
            y_pred: Raw model predictions

        Returns:
            Predictions in original scale
        """
        if self.use_log_transform:
            return np.exp(y_pred)
        return y_pred
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Make predictions on new stock data.
        
        Args:
            X: Features to predict on (n_samples, n_features)
            
        Returns:
            predictions: Predicted stock prices or returns (n_samples,)
        """
        if not self.is_trained:
            raise ValueError("Model not trained")
        
        self.validate_input(X)
        
        # Scale features using the SAME scaler from training
        X_scaled = self.scaler.transform(X)
        
        # Make predictions on scaled features
        predictions_raw = self.model.predict(X_scaled)
        
        # Inverse transform to original scale
        return self._inverse_transform_target(predictions_raw)
    
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
        
        # Safe target transformation
        y_train = self._safe_transform_target(y)
        
        # Incrementally train model on scaled features
        self.model.partial_fit(X_scaled, y_train)
        
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
        
        logger.info(f"Saving LinearRegression model to {path}")
        
        joblib.dump({
            'model': self.model,
            'scaler': self.scaler,
            'metrics': self.training_metrics,
            'params': self.model_params,
            'feature_columns': self.feature_columns,
            'model_type': self.model_type,
            'alpha': self.alpha,
            'use_log_transform': self.use_log_transform
        }, path)
        
        logger.info(f"Model saved successfully")
    
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
        self.model_type = data.get('model_type', 'linear')
        self.alpha = data.get('alpha', 1.0)
        self.use_log_transform = data.get('use_log_transform', True)
        self.is_trained = True
        return self
    
    def get_feature_importance(self) -> Dict[str, float]:
        """
        Get normalized feature importance from the linear model.
        
        Coefficients are normalized by their absolute sum so that they
        are comparable across different model types (LinearRegression,
        Ridge, Lasso, SGDRegressor) regardless of scaling differences.
        
        Returns:
            Dictionary of feature names and their normalized importance scores
        """
        if not self.is_trained:
            raise ValueError("Model not trained")
        
        if self.feature_columns is None:
            return {}
        
        coefficients = self.model.coef_.copy()
        
        # Normalize coefficients by absolute sum for cross-model comparability
        # This ensures that importance values are interpretable regardless of
        # whether the model is vanilla LR, Ridge, Lasso, or SGD with different
        # penalty strengths
        abs_sum = np.sum(np.abs(coefficients))
        if abs_sum > 0:
            coefficients = coefficients / abs_sum
        
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
