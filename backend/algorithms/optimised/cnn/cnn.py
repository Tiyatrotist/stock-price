"""
Optimized 1D Convolutional Neural Network (CNN) for Stock Price Prediction

Production-ready Conv1D implementation using TensorFlow/Keras for time-series
stock price prediction. Reshapes 2D tabular feature matrices into 3D time-windowed
tensors so convolutional filters can extract temporal patterns across the time axis.

Architecture:
    Conv1D(64, kernel_size=3) -> MaxPooling1D -> Dropout ->
    Conv1D(32, kernel_size=2) -> Flatten -> Dense(32) -> Dense(1)

Key Design Decisions:
    - Uses Conv1D instead of Conv2D: financial data is sequential, not spatial
    - Sliding window creates overlapping time windows from tabular data
    - shuffle=False preserves chronological order during training
    - RobustScaler handles outliers common in financial data
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from ...model_interface import ModelInterface
from ...stock_indicators import StockIndicators
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import Conv1D, MaxPooling1D, Flatten, Dense, Dropout
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from sklearn.preprocessing import RobustScaler
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import joblib
import logging

logger = logging.getLogger(__name__)


def create_time_windows(X, y=None, window_size=10):
    """
    Reshape 2D tabular data into 3D sequential data for Conv1D.

    Converts a standard (n_samples, n_features) matrix into overlapping
    time windows of shape (n_samples - window_size, window_size, n_features).
    Each window captures `window_size` consecutive time steps, allowing
    Conv1D filters to detect temporal patterns.

    Args:
        X: 2D array of shape (n_samples, n_features)
        y: Optional 1D target array of shape (n_samples,).
           When provided, targets are aligned to the end of each window.
        window_size: Number of consecutive time steps per window

    Returns:
        X_3d: 3D array of shape (n_samples - window_size, window_size, n_features)
        y_target: (only if y is provided) 1D array of aligned targets
    """
    X_3d = []
    y_target = [] if y is not None else None

    for i in range(len(X) - window_size):
        X_3d.append(X[i:(i + window_size)])
        if y is not None:
            y_target.append(y[i + window_size])

    if y is not None:
        return np.array(X_3d), np.array(y_target)
    return np.array(X_3d)


class CNNModel(ModelInterface):
    """
    1D Convolutional Neural Network model for stock price prediction.

    Uses sliding time windows and Conv1D layers to extract temporal features
    from tabular financial data (OHLCV + technical indicators), then applies
    dense layers for regression.
    """

    def __init__(self, window_size: int = 10, filters: int = 64,
                 kernel_size: int = 3, dropout_rate: float = 0.2,
                 learning_rate: float = 0.001, epochs: int = 100,
                 batch_size: int = 32, **kwargs):
        """
        Initialize CNN model.

        Args:
            window_size: Number of time steps per sliding window
            filters: Number of filters in the first Conv1D layer
            kernel_size: Kernel size for the first Conv1D layer
            dropout_rate: Dropout rate for regularization
            learning_rate: Adam optimizer learning rate
            epochs: Maximum training epochs (early stopping may cut short)
            batch_size: Training batch size
        """
        super().__init__('CNN', **kwargs)
        self.window_size = window_size
        self.filters = filters
        self.kernel_size = kernel_size
        self.dropout_rate = dropout_rate
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.batch_size = batch_size

        # Models and preprocessing
        self.model = None
        self.scaler = None
        self.n_features = None
        self.feature_columns = None

    def _create_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators from OHLC data (no volume)."""
        return StockIndicators.calculate_all_indicators(df)

    def _build_model(self, n_features: int) -> Sequential:
        """
        Build the Conv1D Keras model.

        Architecture:
            Conv1D(64, 3) -> MaxPooling1D(2) -> Dropout(0.2) ->
            Conv1D(32, 2) -> Flatten -> Dense(32, relu) -> Dense(1, linear)

        Args:
            n_features: Number of input features per time step

        Returns:
            Compiled Keras Sequential model
        """
        model = Sequential([
            Conv1D(
                filters=self.filters,
                kernel_size=self.kernel_size,
                activation='relu',
                input_shape=(self.window_size, n_features)
            ),
            MaxPooling1D(pool_size=2),
            Dropout(self.dropout_rate),
            Conv1D(
                filters=32,
                kernel_size=2,
                activation='relu'
            ),
            Flatten(),
            Dense(32, activation='relu'),
            Dense(1, activation='linear')
        ])

        model.compile(
            optimizer=Adam(learning_rate=self.learning_rate),
            loss='mse',
            metrics=['mae']
        )

        return model

    def fit(self, X: np.ndarray, y: np.ndarray) -> 'ModelInterface':
        """
        Train the CNN model on time-series data.

        Scales features with RobustScaler, creates sliding time windows,
        builds and trains a Conv1D model with shuffle=False to prevent
        time-series data leakage.

        Args:
            X: Input features of shape (n_samples, n_features)
            y: Target values of shape (n_samples,)

        Returns:
            self: Returns self for method chaining
        """
        self.validate_input(X, y)

        try:
            self.n_features = X.shape[1]

            # Validate that we have enough samples for the window size
            if X.shape[0] <= self.window_size:
                raise ValueError(
                    f"Not enough samples ({X.shape[0]}) for window_size "
                    f"({self.window_size}). Need at least {self.window_size + 1} samples."
                )

            # Scale features using RobustScaler (handles outliers in financial data)
            self.scaler = RobustScaler()
            X_scaled = self.scaler.fit_transform(X)

            # Create time windows: reshape (n_samples, n_features) -> (n_windows, window_size, n_features)
            X_3d, y_target = create_time_windows(X_scaled, y, window_size=self.window_size)
            logger.info(
                f"Created time windows: {X.shape} -> {X_3d.shape}, "
                f"targets: {y.shape} -> {y_target.shape}"
            )

            # Build Conv1D model
            self.model = self._build_model(self.n_features)
            logger.info(f"Built CNN model with {self.model.count_params()} parameters")

            # Callbacks for training optimization
            callbacks = [
                EarlyStopping(patience=10, restore_best_weights=True),
                ReduceLROnPlateau(factor=0.5, patience=5, min_lr=1e-6)
            ]

            # Train model — shuffle=False is CRITICAL for time-series integrity
            logger.info("Training CNN model...")
            history = self.model.fit(
                X_3d, y_target,
                epochs=self.epochs,
                batch_size=self.batch_size,
                validation_split=0.2,
                callbacks=callbacks,
                shuffle=False,  # CRITICAL: Prevent time-series data leakage
                verbose=0
            )

            # Set trained flag before calculating metrics
            self.is_trained = True

            # Calculate training metrics
            y_pred = self.model.predict(X_3d, verbose=0).flatten()
            self.training_metrics = {
                'mse': float(mean_squared_error(y_target, y_pred)),
                'rmse': float(np.sqrt(mean_squared_error(y_target, y_pred))),
                'r2_score': float(r2_score(y_target, y_pred)),
                'mae': float(mean_absolute_error(y_target, y_pred)),
                'training_loss': float(history.history['loss'][-1]),
                'val_loss': float(history.history['val_loss'][-1]),
                'epochs_trained': len(history.history['loss']),
                'window_size': self.window_size,
                'n_features': self.n_features
            }
            logger.info(
                f"CNN training completed. R² Score: {self.training_metrics['r2_score']:.4f}, "
                f"RMSE: {self.training_metrics['rmse']:.4f}"
            )

        except Exception as e:
            logger.error(f"Error training CNN: {str(e)}")
            raise

        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Make predictions using the trained CNN model.

        Scales features, creates time windows, and runs inference.
        Returns predictions aligned to the last (n_samples - window_size) rows.

        Args:
            X: Input features of shape (n_samples, n_features)

        Returns:
            Predictions of shape (n_samples - window_size,)
        """
        if not self.is_trained:
            raise ValueError("Model not trained")

        self.validate_input(X)

        try:
            # Scale features
            X_scaled = self.scaler.transform(X)

            # Create time windows
            X_3d = create_time_windows(X_scaled, window_size=self.window_size)

            # Make predictions
            predictions = self.model.predict(X_3d, verbose=0).flatten()

            # Convert to float for JSON serialization
            return predictions.astype(float)

        except Exception as e:
            logger.error(f"Error making predictions: {str(e)}")
            raise

    def save(self, path: str) -> None:
        """Save the trained model to disk."""
        if not self.is_trained:
            raise ValueError("Model not trained")

        try:
            # Save Keras model in modern .keras format
            self.model.save(f"{path}_cnn.keras")

            # Save preprocessing and metadata
            joblib.dump({
                'scaler': self.scaler,
                'window_size': self.window_size,
                'filters': self.filters,
                'kernel_size': self.kernel_size,
                'dropout_rate': self.dropout_rate,
                'learning_rate': self.learning_rate,
                'n_features': self.n_features,
                'feature_columns': self.feature_columns,
                'training_metrics': self.training_metrics,
                'model_params': self.model_params
            }, f"{path}_cnn_metadata.pkl")

            logger.info(f"CNN model saved to {path}")

        except Exception as e:
            logger.error(f"Error saving CNN model: {str(e)}")
            raise

    def load(self, path: str) -> 'ModelInterface':
        """Load a previously saved model from disk."""
        try:
            # Load Keras model
            self.model = load_model(f"{path}_cnn.keras", compile=False)

            # Re-compile after loading
            self.model.compile(
                optimizer=Adam(learning_rate=self.learning_rate),
                loss='mse',
                metrics=['mae']
            )

            # Load metadata
            metadata = joblib.load(f"{path}_cnn_metadata.pkl")
            self.scaler = metadata['scaler']
            self.window_size = metadata['window_size']
            self.filters = metadata['filters']
            self.kernel_size = metadata['kernel_size']
            self.dropout_rate = metadata['dropout_rate']
            self.learning_rate = metadata['learning_rate']
            self.n_features = metadata['n_features']
            self.feature_columns = metadata['feature_columns']
            self.training_metrics = metadata['training_metrics']
            self.model_params = metadata['model_params']

            self.is_trained = True
            logger.info(f"CNN model loaded from {path}")

        except Exception as e:
            logger.error(f"Error loading CNN model: {str(e)}")
            raise

        return self
