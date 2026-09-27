"""
Support Vector Regression for Stock Price Prediction

Optimized implementation using scikit-learn for stock price prediction
based on OHLCV data and technical indicators.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, List
import sys
import os
import joblib
import logging

from sklearn.svm import SVR, LinearSVR
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.preprocessing import RobustScaler
from sklearn.pipeline import Pipeline

logger = logging.getLogger(__name__)

# Add parent directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from ...model_interface import ModelInterface
from ...stock_indicators import StockIndicators


class SVMModel(ModelInterface):
    """
    Support Vector Regression model for stock price prediction.

    Uses technical indicators calculated from OHLC data to predict
    future stock prices. Volume is excluded from all calculations.
    """

    def __init__(
        self,
        kernel: str = 'rbf',
        C: float = 1.0,
        gamma: str = 'scale',
        epsilon: float = 0.1,
        degree: int = 3,
        max_samples: int = 10000,
        max_iter: int = -1,
        cache_size: int = 200,
        verbose: bool = False,
        **kwargs
    ):
        super().__init__('Support Vector Regression', **kwargs)

        self.model = None
        self.scaler = None
        self.feature_columns = None

        # Model parameters
        self.kernel = kernel
        self.C = C
        self.gamma = gamma
        self.epsilon = epsilon
        self.degree = degree
        self.max_samples = max_samples
        self.max_iter = max_iter
        self.cache_size = cache_size
        self.verbose = verbose

    def _create_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators from OHLC data (no volume)."""
        return StockIndicators.calculate_all_indicators(df)

    def fit(self, X: np.ndarray, y: np.ndarray) -> 'ModelInterface':
        """
        Train the SVR model on stock data.

        Args:
            X: Feature matrix (n_samples, n_features)
            y: Target vector (n_samples,) - stock prices

        Returns:
            self: Returns self for method chaining
        """
        self.validate_input(X, y)

        # Get dataset size for model selection
        original_size = len(X)

        # Robust scaling is better suited for financial data
        # because it is less sensitive to extreme outliers.
        self.scaler = RobustScaler()
        X_scaled = self.scaler.fit_transform(X)

        # For large datasets, use LinearSVR because standard kernel
        # SVR can become extremely expensive as dataset size grows.
        if original_size > 10000:
            logger.info(
                f"Using LinearSVR for large dataset ({original_size:,} samples)"
            )

            self.model = LinearSVR(
                C=self.C,
                epsilon=self.epsilon,
                max_iter=5000 if self.max_iter == -1 else self.max_iter,
                random_state=42
            )

        else:
            # Initialize standard SVR model
            self.model = SVR(
                kernel=self.kernel,
                C=self.C,
                gamma=self.gamma,
                epsilon=self.epsilon,
                degree=self.degree,
                max_iter=self.max_iter,
                cache_size=self.cache_size,
                verbose=self.verbose
            )

        # Train model
        self.model.fit(X_scaled, y)

        # Calculate training metrics
        y_pred = self.model.predict(X_scaled)

        mse = mean_squared_error(y, y_pred)
        rmse = np.sqrt(mse)
        r2 = r2_score(y, y_pred)
        mae = mean_absolute_error(y, y_pred)

        # Get support vectors count
        # LinearSVR does not expose support_.
        n_support_vectors = (
            len(self.model.support_)
            if hasattr(self.model, 'support_')
            else 0
        )

        self.set_training_metrics({
            'mse': mse,
            'rmse': rmse,
            'r2_score': r2,
            'mae': mae,
            'n_support_vectors': n_support_vectors
        })

        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Make predictions on new stock data.

        Args:
            X: Features to predict on (n_samples, n_features)

        Returns:
            predictions: Predicted stock prices (n_samples,)
        """
        if not self.is_trained:
            raise ValueError("Model not trained")

        self.validate_input(X)

        # Scale features using scaler fitted during training
        X_scaled = self.scaler.transform(X)

        # Make predictions
        predictions = self.model.predict(X_scaled)

        return predictions

    def get_support_vectors(self) -> np.ndarray:
        """
        Get support vectors from the trained model.

        Returns:
            Array of support vectors (None if using LinearSVR)
        """
        if not self.is_trained:
            raise ValueError("Model not trained")

        if not hasattr(self.model, 'support_vectors_'):
            logger.warning("LinearSVR does not have support vectors attribute")
            return None

        return self.model.support_vectors_

    def get_dual_coefficients(self) -> np.ndarray:
        """
        Get dual coefficients from the trained model.

        Returns:
            Array of dual coefficients (None if using LinearSVR)
        """
        if not self.is_trained:
            raise ValueError("Model not trained")

        if not hasattr(self.model, 'dual_coef_'):
            logger.warning("LinearSVR does not have dual coefficients attribute")
            return None

        return self.model.dual_coef_

    def save(self, path: str) -> None:
        """
        Save the trained model to disk.

        Args:
            path: File path to save the model
        """
        if not self.is_trained:
            raise ValueError("Model not trained")

        joblib.dump({
            'model': self.model,
            'scaler': self.scaler,
            'metrics': self.training_metrics,
            'params': self.model_params,
            'feature_columns': self.feature_columns
        }, path)

    def load(self, path: str) -> 'ModelInterface':
        """
        Load the trained model from disk.

        Args:
            path: File path to load the model from.

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

    def hyperparameter_tuning(
        self,
        X: np.ndarray,
        y: np.ndarray,
        cv: int = 5
    ) -> 'ModelInterface':
        """
        Perform time-aware hyperparameter tuning using GridSearchCV.

        TimeSeriesSplit is used instead of standard K-Fold CV so that
        future observations are never used to predict earlier observations.

        RobustScaler is placed inside a Pipeline so that scaling is fitted
        independently inside each CV training fold, preventing preprocessing
        leakage.

        For datasets larger than 10,000 samples, LinearSVR is used to avoid
        the expensive training cost of kernel SVR.

        Args:
            X: Feature matrix
            y: Target vector
            cv: Number of time-series cross-validation folds

        Returns:
            self: Returns self for method chaining
        """
        self.validate_input(X, y)

        if cv < 2:
            raise ValueError("cv must be at least 2")

        # Time-aware cross-validation.
        # Each validation fold contains observations that occur after
        # the corresponding training fold.
        tscv = TimeSeriesSplit(n_splits=cv)

        original_size = len(X)

        # ---------------------------------------------------------
        # Select model and parameter grid
        # ---------------------------------------------------------

        if original_size > 10000:
            # Kernel SVR is too expensive for large datasets.
            # Use LinearSVR instead.
            logger.info(
                f"Using LinearSVR for hyperparameter tuning "
                f"({original_size:,} samples)"
            )

            base_model = LinearSVR(
                max_iter=5000 if self.max_iter == -1 else self.max_iter,
                random_state=42
            )

            # IMPORTANT:
            # LinearSVR does not support gamma or degree.
            param_grid = {
                'model__C': [0.1, 1, 10, 100, 1000],
                'model__epsilon': [0.01, 0.1, 0.2, 0.5]
            }

        else:
            # Standard kernel SVR for smaller datasets.
            base_model = SVR(
                kernel=self.kernel,
                cache_size=self.cache_size,
                verbose=self.verbose
            )

            if self.kernel == 'rbf':
                param_grid = {
                    'model__C': [0.1, 1, 10, 100, 1000],
                    'model__gamma': [
                        'scale',
                        'auto',
                        0.001,
                        0.01,
                        0.1,
                        1
                    ],
                    'model__epsilon': [
                        0.01,
                        0.1,
                        0.2,
                        0.5
                    ]
                }

            elif self.kernel == 'poly':
                param_grid = {
                    'model__C': [0.1, 1, 10, 100],
                    'model__degree': [2, 3, 4, 5],
                    'model__epsilon': [
                        0.01,
                        0.1,
                        0.2
                    ]
                }

            else:
                # Linear kernel SVR
                param_grid = {
                    'model__C': [0.1, 1, 10, 100, 1000],
                    'model__epsilon': [
                        0.01,
                        0.1,
                        0.2,
                        0.5
                    ]
                }

        # ---------------------------------------------------------
        # Pipeline
        # ---------------------------------------------------------
        #
        # IMPORTANT:
        # RobustScaler must be inside the pipeline.
        #
        # If we scale X before GridSearchCV, the scaler sees the
        # complete dataset, including future validation observations.
        #
        # Putting it inside the pipeline means every TimeSeriesSplit
        # fold performs:
        #
        #     scaler.fit(train)
        #     scaler.transform(train)
        #     scaler.transform(test)
        #
        # independently.
        # ---------------------------------------------------------

        pipeline = Pipeline([
            ('scaler', RobustScaler()),
            ('model', base_model)
        ])

        # ---------------------------------------------------------
        # Grid Search
        # ---------------------------------------------------------

        grid_search = GridSearchCV(
            estimator=pipeline,
            param_grid=param_grid,
            cv=tscv,
            scoring='neg_mean_squared_error',
            n_jobs=-1,
            verbose=0
        )

        # Fit without any preprocessing outside the pipeline.
        grid_search.fit(X, y)

        # ---------------------------------------------------------
        # Extract best model and scaler
        # ---------------------------------------------------------

        best_pipeline = grid_search.best_estimator_

        self.scaler = best_pipeline.named_steps['scaler']
        self.model = best_pipeline.named_steps['model']

        # ---------------------------------------------------------
        # Training metrics
        # ---------------------------------------------------------

        # Predict using the complete fitted pipeline so the same
        # scaler/model combination is used.
        y_pred = best_pipeline.predict(X)

        mse = mean_squared_error(y, y_pred)
        rmse = np.sqrt(mse)
        r2 = r2_score(y, y_pred)
        mae = mean_absolute_error(y, y_pred)

        # Support vectors are only available for SVR.
        n_support_vectors = (
            len(self.model.support_)
            if hasattr(self.model, 'support_')
            else 0
        )

        self.set_training_metrics({
            'mse': mse,
            'rmse': rmse,
            'r2_score': r2,
            'mae': mae,
            'best_params': grid_search.best_params_,
            'cv_score': -grid_search.best_score_,
            'n_support_vectors': n_support_vectors
        })

        logger.info(
            f"Best hyperparameters: {grid_search.best_params_}"
        )

        logger.info(
            f"Best CV MSE: {-grid_search.best_score_:.6f}"
        )

        return self


# Example usage and testing
if __name__ == "__main__":
    # Create sample stock data for testing
    np.random.seed(42)

    dates = pd.date_range(
        '2020-01-01',
        periods=200,
        freq='D'
    )

    # Generate synthetic OHLC data
    base_price = 100
    returns = np.random.normal(0, 0.02, 200)
    prices = [base_price]

    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))

    df = pd.DataFrame({
        'date': dates,
        'open': prices,
        'high': [
            p * (1 + abs(np.random.normal(0, 0.01)))
            for p in prices
        ],
        'low': [
            p * (1 - abs(np.random.normal(0, 0.01)))
            for p in prices
        ],
        'close': prices
    })

    # Ensure high >= low and high >= close >= low
    df['high'] = np.maximum(df['high'], df['close'])
    df['low'] = np.minimum(df['low'], df['close'])

    # Create model
    model = SVMModel(
        kernel='rbf',
        C=1.0,
        gamma='scale',
        epsilon=0.1
    )

    # Add technical indicators
    df_with_features = model._create_technical_indicators(df)

    # Prepare training data
    X, y = StockIndicators.prepare_training_data(
        df_with_features
    )

    if len(X) > 0:
        # Train model
        model.fit(X, y)

        # Make predictions
        predictions = model.predict(X[-10:])

        print("SVR Model Results:")
        print(
            f"Training R²: "
            f"{model.training_metrics['r2_score']:.4f}"
        )
        print(
            f"Training RMSE: "
            f"{model.training_metrics['rmse']:.4f}"
        )
        print(
            f"Support Vectors: "
            f"{model.training_metrics['n_support_vectors']}"
        )
        print(
            f"Sample predictions: "
            f"{predictions[:5]}"
        )

        # Test save/load
        model.save('test_svr_model.pkl')

        loaded_model = SVMModel().load(
            'test_svr_model.pkl'
        )

        print(
            f"Model loaded successfully: "
            f"{loaded_model.is_trained}"
        )

        # Clean up
        os.remove('test_svr_model.pkl')

    else:
        print("Insufficient data for training")
